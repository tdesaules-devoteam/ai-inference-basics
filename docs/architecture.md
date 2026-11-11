# Local lab architecture

`task up` prepares the bastion OCI archive and umbrella package on the workstation,
then invokes the original `.devenv/taskfile.qemu.yaml`. Its KCL/Butane/Ignition flow
uses the local `config.k` to provision the guest and append a bootstrap systemd unit.
Normal devenv package/tool installation remains intact.

The appended unit waits for normal provisioning and the shared workspace, verifies
artifact checksums, installs pinned native k0s, creates guest-local lab credentials,
injects `infra/k0s/k0s.yaml` and starts the single controller+worker.

## One umbrella, ordered k0s-owned releases

All four entries reference `/var/lib/k0s/charts/ai-inference-basics.tgz`:

1. `ai-inference-basics-foundation`: Envoy Gateway and cert-manager.
2. `ai-inference-basics-crds`: KServe and Agent Router CRDs.
3. `ai-inference-basics-controllers`: KServe and Agent Router controllers.
4. `ai-inference-basics`: access, models, bastions and observability.

`concurrencyLevel: 1`, explicit order, timeouts and `forceUpgrade: false` express
the intended bootstrap order. Each release enables a disjoint subset of the same umbrella;
offline tests reject cross-release resource ownership conflicts. These stages are
necessary for CRDs/webhooks, not four independently maintained platform charts.

k0s owns reconciliation. Guest bootstrap waits for its Chart resources to become
deployed; it does not execute `helm install` or `helm upgrade`.

The selected k0s implementation hardcodes concurrent Chart reconciliation and does
not copy the configured order into the generated Chart spec. Do not treat those
configuration fields as a proven dependency barrier. Native retries must converge
as CRDs/controllers appear; this must be qualified on a fresh VM. Bootstrap checks
the actual release/revision/error status fields and model readiness before success.

## Access

Browser → VM's native mDNS hostname, HTTPS 30443 → Envoy → oauth2-proxy/Dex →
Zellij bastions, Headlamp, Grafana and previews. No workstation tunnel is needed.

API clients → Envoy static Bearer-key policy → Agent Router → KServe-managed vLLM.
Chat is an LLMInferenceService without a scheduler; pooling models are
InferenceServices. The aliases are ai-inference-basics-chat,
ai-inference-basics-embeddings and ai-inference-basics-rerank.

The local VM defaults to 12 vCPUs, 32 GiB RAM and 64 GiB disk. Cloud provisioning
has been removed from this version. The empty cloud directories are reserved only.
