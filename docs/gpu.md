# GPU preparation

## Images and workspace

The environment samples pull the public images by digest. Both use Fedora Minimal
45 (glibc). For local builds, build and export them
with `oci/prepare.sh all`, or select `bastion` or `provision`. Import the resulting OCI archives into the VM’s
native k0s containerd and align the digest references before Helmfile sync.

- Bastion: bash, curl, jq, git, kubectl, k9s, ttyd, Zellij, code-server,
  Starship, Helix and vLLM bench. Python/PyTorch remain necessary for vLLM bench.
- Provision: Python, huggingface_hub, boto3, bcrypt, PyYAML and RustFS rc.
  Credential and model-import Jobs use this image; it contains no PyTorch.

The terminal and editor use Nord and bundled Geist fonts. code-server serves
fonts from same-origin static assets to respect its Content Security Policy.
`EDITOR`, `VISUAL` and `KUBE_EDITOR` select Helix, including for k9s.
The workspace ConfigMap mounts the copied Starship configuration.

## Environment selection

The environment infrastructure JSON selects model releases explicitly. Suggested selections:

| Environment | Chat | Embeddings | Reranker |
| --- | --- | --- | --- |
| default / devenv | qwen3-0-6b | qwen3-embedding-0-6b | qwen3-reranker-0-6b |
| scaleway | qwen3-8b-fp8 | qwen3-embedding-4b | qwen3-reranker-4b |

Select Scaleway with `helmfile -e scaleway -f platform/helmfile/helmfile.yaml.gotmpl`,
after creating the ignored `infra/infra-definition.scaleway.json`.
Start from `infra/infra-definition.scaleway.sample.json`, replace placeholder
access/network settings, and adapt machine sizing to the actual GPU instance.
This selects manifests; it does not create a cloud instance. Each model retains
its own namespace, chart, runtime, InferenceService and S3 prefix. Revisions and
downloaded file hashes are locked.

GPU Operator installs Container Toolkit and Node Feature Discovery, using the
driver already supplied by the Scaleway image. Its device plugin, MIG manager
and DCGM deployment are disabled. HAMi owns GPU allocation; standalone DCGM
Exporter provides GPU metrics. GPU-only DaemonSets select
`nvidia.com/gpu.present: "true"` and schedule zero Pods on the CPU VM.

Toolkit targets `/etc/k0s/containerd.d/nvidia.toml`, reads
`/etc/k0s/containerd.toml` and uses `/run/k0s/containerd.sock`.
Provisional HAMi budgets are 24576 MiB / 50% cores for chat and 20480 MiB / 20%
each for embeddings and reranking. H100 runtime behavior and these budgets
require qualification on real hardware.

The 4B pooling models also reserve KV cache in vLLM. Their 40,960-token native
windows require about 5.625 GiB of BF16 KV data in addition to weights, so the
former 16-GiB HAMi shares with 80% vLLM utilization were insufficient even before
runtime overhead. The revised shares total 64 GiB on the intended 80-GB H100;
they are configuration estimates, not hardware qualification.

## Metrics and public access

k0s `telemetry.enabled: false` disables periodic usage reporting to the k0s
development team. It does not disable metrics-server or local observability.
metrics-server provides the resource metrics API used by `kubectl top` and
resource-based autoscaling. Prometheus Adapter can provide a resource metrics
API backed by collected metrics, but adds configuration and dependencies;
DCGM Exporter complements rather than replaces it.

Scaleway documents an instance DNS name
`<instance-uuid>.pub.instances.scw.cloud` pointing to its main public IP.
Flexible public IPs can be attached independently. A reachable DNS name permits
ACME HTTP-01 validation when port 80 and the challenge route are configured.
A controlled domain is preferable for a stable service name. Let's Encrypt
also offers short-lived IP certificates; that cert-manager integration remains
unqualified here. No cloud instance or public certificate has been provisioned.
