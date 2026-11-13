# Domain-oriented CPU lab

Helmfile owns 16 releases. Each model has a dedicated chart, release, namespace
and S3 prefix. The shared pair-training workstation uses one Dex account named
`admin`, one computer, one workspace PVC and Kubernetes `cluster-admin` rights.

## Domains and ownership

| Domain | Namespace | Owner |
| --- | --- | --- |
| Chat | qwen3-0-6b | charts/qwen3-0-6b |
| Embeddings | qwen3-embedding-0-6b | charts/qwen3-embedding-0-6b |
| Reranker | qwen3-reranker-0-6b | charts/qwen3-reranker-0-6b |
| Shared terminal/editor | bastion | charts/bastion |
| HTTPS, routes, CA and API key | gateway | charts/gateway |
| Identity | dex | Official Dex chart + domain post-renderer |
| Browser session | oauth2-proxy | Official oauth2-proxy chart + domain post-renderer |
| S3 and prefix-scoped IAM | rustfs | Official RustFS chart + domain post-renderer |
| Administration dashboard | headlamp | Official Headlamp chart |

Infrastructure controllers retain their own namespaces: `kserve`, `cert-manager`,
`envoy-gateway`, `agent-router` and `local-path-provisioner`. The Envoy Gateway
controller configures the proxy in `gateway`; user traffic reaches the proxy,
not the controller. Controller CRDs can have a separate upstream release.

Each authored template declares one resource in block-style YAML. A model chart
owns its local Secrets and credential/import hooks. RustFS owns IAM users and
publishes credentials in model-specific Secrets; its RBAC grants each model's
credential Job access only to its own Secret. Serving Pods receive read-only S3
credentials and do not mount a Kubernetes API token.
The list policy uses `StringLikeIfExists` for the prefix because KServe first
calls HeadBucket without a prefix. Explicit listings of another model's prefix
and reads of its objects remain denied; this is not a promise to hide bucket
metadata from requests without a prefix.

The centralized `lab-bootstrap` release is removed. Domain Jobs generate stable
credentials locally. Cross-domain contracts are deliberately narrow:

- Dex publishes `oidc-client` for oauth2-proxy, separately from the admin password.
- Gateway publishes the API key and a public CA ConfigMap for the bastion.
- RustFS publishes one reader/writer credential Secret per model.
- Dex/oauth2-proxy own their cross-namespace Gateway ReferenceGrants.

`platform/helm/plugins/domain-render` is a repository-local Helm 4 subprocess
post-renderer. It appends declarative resources and hook scripts from
`platform/helm/domains` to the official upstream release. It makes no Kubernetes
calls and generates no secrets during rendering. This keeps upstream downloads
direct and pinned while keeping domain additions under the same release owner.
Helm 4.3.1's combined post-render strategy includes the appended Helm hooks.

## Local image prerequisite

GHCR publication remains unavailable with the previously supplied token. The
qualified bastion image is also the current hook tooling image: it already
contains the locked `huggingface_hub`, boto3, bcrypt and RustFS rc dependencies.
No additional image build is required for the Python import implementation.

Build with `bash oci/prepare.sh` or reuse a qualified OCI archive. A fresh VM must
receive the image before these domain hooks can run:

```sh
VM="$(id -un)@$(cat .devenv/.uuid).local"
(cd dist && sha256sum -c SHA256SUMS)
ssh "$VM" 'sudo k0s ctr images import --digests -' < dist/bastion.oci.tar
ssh "$VM" "sudo k0s ctr images tag --force localhost/ai-inference-basics-bastion:dev $(cat dist/bastion.ref)"
```

When using a different qualified image, set `LAB_TOOLS_IMAGE` consistently for
Helmfile and its post-renderer (including the bootstrap service environment).
The default reference is pinned in `values/lab.yaml.gotmpl` and `render-domain.sh`.
`IfNotPresent` reuses the imported image; it does not make an unpublished localhost
image remotely available.

Ignition copies chart sources, Helm inputs, the renderer and plugin descriptor
to `/etc/ai-inference-basics`. Local config.k uses file globs so template splits
are included automatically. Updating sources does not update an existing guest:
synchronize those directories, remove obsolete templates, and update the unit
before restarting `platform-k0s-bootstrap.service`.

## Model import and activation

Each model's `files/model.lock.json` pins the Hugging Face repository revision
and each file's size/SHA-256. The import Job uses the Python `huggingface_hub`
package, verifies the downloaded bytes, and uploads them through boto3:

```text
s3://models/qwen3-0-6b/<revision>/...
s3://models/qwen3-embedding-0-6b/<revision>/...
s3://models/qwen3-reranker-0-6b/<revision>/...
```

Existing objects are reused when size and SHA metadata agree; their contents are
not downloaded again for hashing. A mismatch fails the immutable import.

Models default to `serving.replicas: 1` in each chart and start automatically.
Helmfile inherits that value unless `LAB_MODEL_REPLICAS` is explicitly set.
Setting zero uses KServe's supported `serving.kserve.io/stop: "true"` annotation;
the readiness check then expects `Stopped=True` and zero inference Pods.
Imports still run by default even when serving is stopped.

Inside the VM, explicitly start or restart the chat model:

```sh
export LAB_HOSTNAME="$(hostname)"
export HELM_PLUGINS=/etc/ai-inference-basics/platform/helm/plugins
LAB_MODEL_REPLICAS=1 helmfile \
  -f /etc/ai-inference-basics/platform/helm/helmfile.yaml.gotmpl \
  -l name=qwen3-0-6b sync
```

Set `LAB_MODEL_REPLICAS=0` to stop it. Select all three names to activate all APIs.
The lab accepts 0 or 1 replica per model. There is no automatic wake-up on an API
request. A normal full bootstrap without the environment override starts all three models.
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
| `/v1/chat/completions` | Bearer API, model `qwen3-0-6b` |
| `/v1/embeddings` | Bearer API, model `qwen3-embedding-0-6b` |
| `/cohere/v2/rerank` | Bearer API, model `qwen3-reranker-0-6b` |

Dex has one account named `admin`; its login email is `admin@example.test`.
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

## Validation

Offline commands require Helm 4.3.1, Helmfile and `requirements-dev.txt`:

```sh
export HELM_PLUGINS="$PWD/platform/helm/plugins"
python tests/validate_storage.py
python tests/validate_lab.py
python tests/test_platform_units.py
python tests/test_rustfs_credentials.py
```

Runtime checks require the deployed lab and explicit authorization:

- `tests/qualify_admin.sh`: actual bastion and Headlamp cluster-admin permissions
  and the shared terminal/editor volume.
- `tests/browser/qualify.mjs`: one Dex login, real terminal command, editor,
  Headlamp, anonymous-header spoof rejection and API-cookie rejection.
- `tests/qualify_model_apis.py`: CA-verified HTTPS, Bearer rejection, real chat/SSE,
  embeddings and reranking; models must be Ready.
- `tests/qualify_model_storage.py`: run inside the bastion with a JSON map of model
  locks on stdin; verify own-prefix reads and rejection of writes/other prefixes.
- `tests/qualify_benchmark.py`: run inside the bastion with the chat lock on stdin;
  download only the verified tokenizer and submit three requests through HTTPS.

Browser/API tests consume `LAB_ORIGIN`, `LAB_CREDENTIALS_FILE` (a private JSON
object with username/email/password/api_key) and `LAB_CA_FILE` for the API test.
Chromium accepts the lab certificate for interaction tests; API TLS verification
is performed separately with the CA. Reports and credentials stay untracked.

The domain reorganization qualification passed the admin browser journey, both
cluster-admin identities, prefix-scoped S3 checks, all three real APIs and the
bastion benchmark. Reexecuting the complete bootstrap preserved nine credential
Secrets and the workspace PVC, deployed all 16 releases, and returned all three
models to Stopped=True with zero inference Pods. That validated the stopped mode;
the current default is now one active replica per model.
The automatic-start default was qualified without `LAB_MODEL_REPLICAS`: all three
InferenceServices reached Ready=True, and TLS/Bearer, chat/SSE, embeddings and
reranking checks passed.

## Existing installations of the previous layout

This layout changes Helm ownership and model namespaces. Do not overlay it and
blindly uninstall `lab-bootstrap` or `lab-gateway`: their release records still
own certificates and routes. A migration must first preserve/adopt those resources
under the new owners, retain old bastion PVCs, and validate the new identity and
routes before retiring the old releases. S3 prefixes are new; old model objects
can remain until their replacement is qualified. No automatic legacy-data deletion
is part of this configuration. The current qualification began with foundation
releases only, so it does not prove that legacy Helm ownership migration.
