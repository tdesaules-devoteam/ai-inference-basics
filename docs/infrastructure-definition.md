# Infrastructure definitions and Helmfile orchestration

The desired environment is a JSON document validated against
`infra/infra-definition.schema.json`. Start from `infra/infra-definition.sample.json`.
For CUDA-backed Scaleway inference, use `infra/infra-definition.scaleway.sample.json`.
Real `infra/infra-definition.<environment>.json` files are ignored by Git because
they contain the administrator password and API Bearer key. Create them with
mode 0600. The sample contains placeholders, not deployment credentials.

The definition owns machine sizing, network hostname/HTTPS NodePort, image pins,
initial user access, storage capacity and model selection. Terraform may consume
the same document in a future implementation; no Terraform provisioning is
implemented by this change. Local devenv supports one machine only.

The current ignored `.devenv/config.k` reads the local JSON using KCL's
`json.decode(file.read("../infra/infra-definition.devenv.json"))` and maps
`machines[0].cpu`, `memoryGiB` and `diskGiB` into the native hardware schema.
Keep the existing VM UUID and other local settings when reproducing that mapping.
The JSON does not introduce a second VM lifecycle or override the native Taskfile.

Before Helmfile starts, `platform-images-ready.service` waits for configured
localhost application images to be explicitly imported into k0s, or pulls
digest-pinned registry images. This prevents initialization Jobs from failing
their short deadlines while application images are still unavailable. The native
devenv lifecycle remains unchanged. The gate has a bounded 30-minute timeout.
For context settings, see
[native context windows](token-budgets.md).

## Commands

Install `requirements-dev.txt` into your Python environment, then:

```sh
task infra:validate
export INFRA_DEFINITION="$PWD/infra/infra-definition.devenv.json"
helmfile -f platform/helmfile/helmfile.yaml.gotmpl template
# With explicit authorization to modify the target cluster:
helmfile -f platform/helmfile/helmfile.yaml.gotmpl sync
```

Helmfile validates the JSON before rendering its releases. Without an explicit
`INFRA_DEFINITION`, it selects `infra-definition.devenv.json` for the default or
devenv environment, and `infra-definition.scaleway.json` with `-e scaleway`.
An explicit path is authoritative. There is no implicit fallback to the sample.
Rendered output and Helm release records can include initialization credentials;
keep rendered files and reports private and untracked.

`infra/helmfile/lab.yaml.gotmpl` maps the validated document to shared chart values.
Passwords are passed only to the Dex configuration release, and the Bearer key
only to Gateway. Upstream dependency versions remain in Helmfile and its values;
they are software pins, not a second set of environment defaults.

## Model lifecycle

Every known model is explicitly present in the definition, including disabled
models. This avoids forgetting previously installed releases when editing a list.

| Fields | Desired state |
| --- | --- |
| `enabled: true`, `replicas: 1` | Install release and run inference |
| `enabled: true`, `replicas: 0` | Keep release and stop inference through KServe |
| `enabled: false`, `replicas: 0`, `import: false` | Helmfile `installed: false`; uninstall the release on sync |
| `import: true` on an enabled model | Run the verified S3 snapshot import hook |

Stopping does not remove the model's S3 data. Disabling uninstalls Kubernetes
resources but does not delete objects in the shared models bucket. Gateway routes
include enabled models; stopped models do not automatically wake on a request.
Changing local JSON does not change the guest's existing copy automatically.

## Resource ownership and ordering

- Project-authored charts live in `charts/`, including `dex-config`.
- `dex-config` owns the initialization/bcrypt Job and its namespaced RBAC; Dex's
  official release depends on its completion and consumes the resulting config.
- RustFS uses upstream `extraManifests` for root/shared-account initialization,
  bucket initialization, the `rc` IAM Job and model Secret distribution policy.
- oauth2-proxy uses upstream `extraObjects` for session initialization, Kyverno
  policies, ReferenceGrant and the Caddy router. Its application configuration is
  rendered through the upstream chart's native `configFile` setting.
- Kyverno synchronizes the OIDC client, Gateway API key, public CA and model
  credentials. It is installed before releases that declare GeneratingPolicies.
- cert-manager owns private TLS keys and certificates. Kyverno publishes only
  the public CA certificate.

There is no custom Helm plugin or post-renderer. Helmfile `needs`, Helm Jobs/hooks
and readiness waits order the work. `platform/helmfile/scripts/check-model.sh`
checks KServe convergence, including the explicit stopped state.

## Existing installation migration

The source refactor has offline validation only. Before applying to the existing
VM, import the new provision image (now containing kubectl), install the host
Python JSON-schema dependency, and synchronize the new source directories and
bootstrap unit. Preserve the current credential Secrets and PVCs. The native
devenv lifecycle and identity are unchanged; Ignition is first-boot provisioning.

The previous `dex-domain` ServiceAccount/Role/RoleBinding were Helm hook resources;
inspect their ownership before moving them to the `dex-config` release. Old hook
objects are not automatically removed when templates disappear. Retire only the
obsolete hook resources after the new release and authentication are validated.

The shared `rustfs/s3-models` account replaces per-model reader/writer accounts.
Existing old IAM users/Secrets are retained until the shared account is qualified
and consumers use it; no automatic account or data deletion is performed.
The compatibility names `model-reader` and `model-writer` now carry the same
bucket-scoped credential, with write access to `models` and no access to Loki.

Data-changing credential updates trigger scoped Kyverno MutatingPolicies to roll
out bastion, Dex and oauth2-proxy. Public CA and generated configuration policies
watch their source resources; cloned Secrets use source synchronization. Verify
source/consumer equality and Deployment rollout after rotation. Single-instance
applications can briefly disconnect; hardware/cluster qualification is separate
from offline policy validation.
