# Domain-oriented CPU lab

Helmfile declares 30 releases, with 27 enabled by the sample definition. Each model has a dedicated chart, release, namespace
and S3 prefix. The shared pair-training workstation uses one Dex account named
`cluster-admin`, one computer, one workspace PVC and Kubernetes `cluster-admin` rights.

## Domains and ownership

| Domain | Namespace | Owner |
| --- | --- | --- |
| Chat | qwen3-0-6b | charts/qwen3-0-6b |
| Embeddings | qwen3-embedding-0-6b | charts/qwen3-embedding-0-6b |
| Reranker | qwen3-reranker-0-6b | charts/qwen3-reranker-0-6b |
| Shared terminal/editor | bastion | charts/bastion |
| HTTPS, routes, CA and API key | gateway | charts/gateway |
| Identity | dex | Official Dex chart + charts/dex-config |
| Browser session | oauth2-proxy | Official chart + native extraObjects |
| S3 and shared bucket IAM | rustfs | Official chart + native extraManifests |
| Administration dashboard | headlamp | Official Headlamp chart |

Infrastructure controllers retain their own namespaces: `kserve`, `cert-manager`,
`envoy-gateway`, `agent-router` and `local-path-provisioner`. The Envoy Gateway
controller configures the proxy in `gateway`; user traffic reaches the proxy,
not the controller. Controller CRDs can have a separate upstream release.

Each authored template declares one resource in block-style YAML. A model chart
owns its import hooks and inference resources. RustFS publishes one shared
bucket account; Kyverno distributes it under the compatibility names model-reader
and model-writer. Both now have bucket-wide read/write permissions. Serving Pods
do not mount a Kubernetes API token.

The centralized `lab-bootstrap` release is removed. Domain Jobs generate stable
credentials locally. Cross-domain contracts are deliberately narrow:

- Dex publishes `oidc-client` for oauth2-proxy, separately from the admin password.
- Gateway publishes the API key and a public CA ConfigMap for the bastion.
- RustFS publishes one shared credential Secret for the models bucket.
- Dex/oauth2-proxy own their cross-namespace Gateway ReferenceGrants.

Helmfile orchestrates official charts, their native extension points and local
charts directly. There is no custom plugin or post-renderer. See
[infrastructure definitions](infrastructure-definition.md) for configuration,
ordering and the existing-installation migration boundary.

## Application images

The CPU and GPU samples select separate public GHCR images for bastion and
provision by tested manifest digest. The VM pulls them before Helmfile starts.
See [GPU setup](gpu.md). Domain hooks
use provision, including its locked huggingface_hub, boto3, bcrypt and RustFS rc.

For an offline installation using `localhost/` overrides, build with
`bash oci/prepare.sh` or reuse a qualified OCI archive, then import it:

```sh
VM="$(id -un)@$(cat .devenv/.uuid).local"
for name in bastion provision; do
  (cd dist && sha256sum -c "$name.SHA256SUMS")
  ssh "$VM" 'sudo k0s ctr images import --digests -' < "dist/$name.oci.tar"
  ssh "$VM" "sudo k0s ctr images tag --force localhost/ai-inference-basics-$name:dev $(cat "dist/$name.ref")"
done
```

When using different qualified images, update the `images` map in the local
infrastructure JSON. `infra/helmfile/lab.yaml.gotmpl` translates these references.
`IfNotPresent` reuses the imported image; it does not make an unpublished localhost
image remotely available.

Ignition copies chart sources, Helmfile inputs, checks and the private definition
to `/etc/ai-inference-basics`. Local config.k uses file globs so template splits
are included automatically. Updating sources does not update an existing guest:
synchronize those directories, remove obsolete templates, and update the unit
before restarting `platform-k0s-bootstrap.service`.

## Model import and activation

For an existing installation that served `lfm3-omni-2b`, remove its `images.omni`
and `models.lfm3-omni-2b` entries from the private environment JSON. Apply the
updated gateway routes, then run `helm uninstall lfm3-omni-2b -n lfm3-omni-2b`
on that cluster. Removing a release from Helmfile does not uninstall it. This
leaves the shared `models` bucket and its stored snapshots intact.

Each model's `files/model.lock.json` pins the Hugging Face repository revision
and each file's size/SHA-256. The import Job uses the Python `huggingface_hub`
package, verifies the downloaded bytes, and uploads them through boto3:

```text
s3://models/qwen3-0-6b/<revision>/...
s3://models/qwen3-embedding-0-6b/<revision>/...
s3://models/qwen3-reranker-0-6b/<revision>/...
```

Existing objects are reused when size and SHA metadata agree; their contents are
not downloaded again for hashing. A mismatch fails the snapshot consistency check.
The shared account can overwrite objects; this check is not an S3 immutability policy.

Models default to `serving.replicas: 1` in each chart and start automatically.
Helmfile overrides it with each model's `replicas` field from the environment JSON.
Setting zero uses KServe's supported `serving.kserve.io/stop: "true"` annotation;
the readiness check then expects `Stopped=True` and zero inference Pods.
The independent `import` field controls imports, including when serving is stopped.

Inside the VM, explicitly start or restart the chat model:

```sh
export INFRA_DEFINITION=/etc/ai-inference-basics/infra/infra-definition.devenv.json
# Set this model's replicas to 1 in the definition, then:
helmfile \
  -f /etc/ai-inference-basics/platform/helmfile/helmfile.yaml.gotmpl \
  -l name=qwen3-0-6b sync
```

Set the model's `replicas` to 0 to stop it.
The lab accepts 0 or 1 replica per model. There is no automatic wake-up on an API
request. A full bootstrap applies the definition's explicit selection.
For active models, the readiness hook checks the desired Deployment and KServe
Ready/UpToDate via JSONPath, accommodating stale observedGeneration in v0.21.0.

## Admin access

Use `https://<native-VM-hostname>:30443` over the native bridge/mDNS connection.
Trust the public lab CA. The server certificate terminates TLS at the Gateway;
Dex and oauth2-proxy's internal Services still use HTTP.

| Path | Purpose |
| --- | --- |
| `/terminal/` | Shared ttyd/Zellij CLI session |
| `/code/` | Shared code-server and workspace files |
| `/headlamp/` | Full Kubernetes administration |
| `/grafana/` | Authenticated metrics, logs and traces in Explore |
| `/v1/chat/completions` | Bearer API, selected chat model |
| `/v1/embeddings` | Bearer API, model `qwen3-embedding-0-6b` |
| `/cohere/v2/rerank` | Bearer API, model `qwen3-reranker-0-6b` |

Dex has one account named `cluster-admin`. The environment JSON supplies its email
and password. The dex-config Job preserves its identity and OIDC client secret,
and recomputes bcrypt only when required. Kyverno distributes the published OIDC
client. After credential changes, synchronize the releases and verify the
Kyverno-triggered consumer rollouts described in [security and access](security-and-access.md).
Retrieve the qualification file privately inside the VM:

```sh
umask 077
kubectl -n dex get secret admin-access -o jsonpath='{.data.credentials\.json}' |
  base64 -d > "$HOME/admin-identity.json"
kubectl -n gateway get secret lab-api-key -o json |
  jq --slurpfile admin "$HOME/admin-identity.json" \
    '(.data.lab | @base64d) as $key | $admin[0] | {username,email,password,api_key:$key}' \
    > "$HOME/lab-credentials.json"
rm "$HOME/admin-identity.json"
kubectl -n gateway get configmap lab-ca -o jsonpath='{.data.ca\.crt}' > "$HOME/lab-ca.crt"
```

Both bastion and Headlamp use ServiceAccounts bound to `cluster-admin`. The
bastion's Linux user remains UID 1000; Kubernetes administration is authorized
by its ServiceAccount. Browser cookies do not authorize model API calls.
The bastion provides `OPENAI_BASE_URL`, `OPENAI_API_KEY` and CA trust for clients.
code-server opens `/workspace/ai-inference-basics` by default and initializes new
user settings with Nord and Geist fonts. Its init container clones the
configured repository only when no checkout exists, and preserves existing files
and editor preferences. The workspace is a persistent Git copy, not a bind mount
of the workstation checkout. For this deployment it was seeded from local Git
history because the remote does not yet contain the latest lab commits.

## Validation

Offline commands require Helm 4.3.1, Helmfile and `requirements-dev.txt`:

```sh
python platform/helmfile/scripts/validate-infra.py infra/infra-definition.sample.json
python tests/validate_storage.py
python tests/validate_lab.py
python tests/test_platform_units.py
python tests/test_rustfs_credentials.py
python -m unittest discover -s tests -p 'test_*.py'
```

Runtime checks require the deployed lab and explicit authorization:

- `tests/qualify_admin.sh`: actual bastion and Headlamp cluster-admin permissions
  and the shared terminal/editor volume.
- `tests/browser/qualify.mjs`: one Dex login, real terminal command, editor,
  Headlamp, anonymous-header spoof rejection and API-cookie rejection.
  Set `LAB_SKIP_TERMINAL_COMMAND=1` when the shared terminal is already running
  an application; it then checks terminal rendering without typing into it.
- `tests/qualify_model_apis.py`: CA-verified HTTPS, Bearer rejection, real chat/SSE,
  embeddings and reranking; models must be Ready.
- `tests/qualify_model_storage.py`: run in a temporary provision-image Pod using
  the bastion ServiceAccount, with a JSON map of model
   locks on stdin; verify shared-bucket reads/writes and rejection of other buckets.
- `tests/qualify_benchmark.py`: run inside the bastion with the chat lock on stdin;
  download only the verified tokenizer and submit three requests through HTTPS.

Browser/API tests consume `LAB_ORIGIN`, `LAB_CREDENTIALS_FILE` (a private JSON
object with username/email/password/api_key) and `LAB_CA_FILE` for the API test.
Chromium accepts the lab certificate for interaction tests; API TLS verification
is performed separately with the CA. Reports and credentials stay untracked.

The previous domain reorganization qualification passed the admin browser journey, both
cluster-admin identities, prefix-scoped S3 checks, all three real APIs and the
bastion benchmark. Reexecuting the complete bootstrap preserved nine credential
Secrets and the workspace PVC, deployed all 16 releases, and returned all three
models to Stopped=True with zero inference Pods. That validated the stopped mode;
the current JSON definition now controls activation per model.
The automatic-start default was qualified without `LAB_MODEL_REPLICAS`: all three
InferenceServices reached Ready=True, and TLS/Bearer, chat/SSE, embeddings and
reranking checks passed.

Those earlier results predate the JSON/Kyverno/native-extension migration. The
three-Qwen configuration was separately qualified on the retained 48-GiB VM
disk: a native stop/start, successful platform bootstrap, three ready services,
actual model requests, workspace/PVC and credential preservation, S3 isolation
and authenticated Grafana telemetry. For the FCOS 45 first-boot policy correction,
see [local setup](devenv.md) and the [tracker](implementation-tracker.md).

## Existing installations of the previous layout

This layout changes Helm ownership and model namespaces. Do not overlay it and
blindly uninstall `lab-bootstrap` or `lab-gateway`: their release records still
own certificates and routes. A migration must first preserve/adopt those resources
under the new owners, retain old bastion PVCs, and validate the new identity and
routes before retiring the old releases. S3 prefixes are new; old model objects
can remain until their replacement is qualified. No automatic legacy-data deletion
is part of this configuration. The current qualification began with foundation
releases only, so it does not prove that legacy Helm ownership migration.
