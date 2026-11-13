# CPU inference lab (stages 8–13)

The lab extends the six foundation releases with KServe CRDs/controller, identity
bootstrap, models, Dex, Headlamp, two bastions, oauth2-proxy and the HTTPS Gateway.
Helmfile owns all 15 releases. Project-authored charts live under `charts/`.

## Local image prerequisite

GHCR rejected publication with the available token; the operator selected local
image import. A new VM needs this explicit import before lab-bootstrap can run.
Build on the host with `bash oci/prepare.sh` or reuse the previously qualified archive.
With the native VM SSH destination in `VM`:

```sh
VM="$(id -un)@$(cat .devenv/.uuid).local"
(cd dist && sha256sum -c SHA256SUMS)
ssh "$VM" 'sudo k0s ctr images import --digests -' < dist/bastion.oci.tar
ssh "$VM" "sudo k0s ctr images tag --force localhost/ai-inference-basics-bastion:dev $(cat dist/bastion.ref)"
```

Set `toolsImage` in `platform/helm/values/lab.yaml.gotmpl` to `dist/bastion.ref`.
Copy updated charts and Helmfile inputs to `/etc/ai-inference-basics/` in an existing
guest, then run `sudo systemctl restart platform-k0s-bootstrap.service` there.
Ignition's custom copies populate these paths only on first boot. Keep the ignored
`.devenv/config.k` aligned with all authored-chart files and component values.

## Browser and API access

The native VM hostname exposes HTTPS on port 30443. Trust the public lab CA from
`gateway/lab-root-ca` (key `tls.crt`) in your browser or use it with `curl --cacert`.
The CA private key must stay in Kubernetes.

Retrieve credentials privately from inside the VM:

```sh
umask 077
kubectl -n gateway get secret lab-access -o jsonpath='{.data.credentials\.json}' |
  base64 -d > "$HOME/lab-credentials.json"
kubectl -n gateway get secret lab-root-ca -o jsonpath='{.data.tls\.crt}' |
  base64 -d > "$HOME/lab-ca.crt"
```

The JSON contains `accounts.a` (alice@example.test), `accounts.b` (bob@example.test)
and `api_key`, along with internal credentials. Keep it out of logs and version
control; give participants only their own login and the shared model API key.

| Path | Access |
| --- | --- |
| `/terminal-a/`, `/code-a/` | Alice's ttyd/Zellij and code-server |
| `/terminal-b/`, `/code-b/` | Bob's ttyd/Zellij and code-server |
| `/headlamp/` | Shared read-only Kubernetes browser |
| `/v1/chat/completions` | Bearer key; model `ai-inference-basics-chat` |
| `/v1/embeddings` | Bearer key; model `ai-inference-basics-embeddings` |
| `/cohere/v2/rerank` | Bearer key; model `ai-inference-basics-rerank` |

Browser access uses one oauth2-proxy/Dex session. The localhost-only Caddy sidecar
authorizes participant paths using the authenticated email. NetworkPolicies restrict
direct access to bastions, Headlamp and model backends. Browser cookies do not
authorize APIs. Bastions have `OPENAI_BASE_URL`, `OPENAI_API_KEY` and lab CA trust
configured for the internal HTTPS Gateway.
Zellij may display first-use tips or a keybinding dialog; this is a local UI
preference rather than another authentication step.

## Model storage and readiness

Three standard `InferenceService` resources serve pinned Qwen3 chat, embedding and
reranker snapshots on CPU. `models.lock.json` pins revisions and file SHA-256 hashes.
The import hook verifies downloads before S3 upload and reuses objects matching
the recorded size/hash metadata. KServe's initializer reads RustFS using a
models-bucket-only, read-only IAM identity; imports use a separate writer.

KServe v0.21.0 can leave `status.observedGeneration` stale during otherwise-ready
upgrades. The models release disables generic Helm waiting, but still waits for
its import hook. Its explicit postsync hook compares desired image, arguments,
resources and storage URI with the generated Deployments, verifies rollout, then
checks JSONPath `Ready=True` and model transition `UpToDate`.

## Qualification

Offline: `python tests/validate_storage.py`, `python tests/validate_lab.py`, the
platform-unit and RustFS-credential tests, and strict lint of the four authored
charts. Helm, Helmfile and the dependencies in `requirements-dev.txt` are required.

Runtime checks require explicit authorization and a deployed lab:

```sh
export LAB_ORIGIN="https://$(cat .devenv/.uuid).local:30443"
export LAB_CREDENTIALS_FILE=/private/path/lab-credentials.json
export LAB_CA_FILE=/private/path/lab-ca.crt
python tests/qualify_model_apis.py
npm ci --prefix tests/browser
node tests/browser/qualify.mjs
# Run with the lab administrator kubeconfig, for example inside the VM:
bash tests/qualify_participants.sh
```

For a short `vllm bench serve` run, copy `tests/qualify_benchmark.py` into a
participant terminal container and pipe `models.lock.json` to its stdin. It checks
the pinned tokenizer files and submits three requests through the internal HTTPS
Gateway, printing only aggregate metrics. The qualification run completed all
three requests (about 3.84 seconds and 12.51 output tokens/s); this tiny CPU sample
is a functional check, not a capacity estimate.

The API check verifies TLS with the CA. Chromium accepts the lab certificate for
browser interaction testing; this is separate from the API TLS verification.
Browser test failures report only the phase to avoid leaking login/OIDC values.
Reports and credentials remain development-local and untracked.

## Observed deployment

All 15 releases and the complete bootstrap service succeeded in the existing VM.
The three model services are Ready; browser/API and isolation checks passed.
The guest uses about 30 GiB of its 64-GiB disk and has about 30 GiB of memory
available with the models loaded. No VM destruction or recreation was performed
for these stages. A clean-VM bootstrap of the extended lab remains conditional on
the explicit local-image import described above. Beszel cleanup authentication
is the separately deferred issue.
