# GPU preparation and multimodal runtime

## Images and workspace

Own images use digest-pinned Fedora Minimal 45 (glibc). Build and export them
with `oci/prepare.sh all`, or select `bastion`, `provision` or
`lfm3-omni-2b-transformers`. Build the CUDA variant separately with
`oci/prepare.sh lfm3-omni-2b-transformers-cuda`. Import the resulting OCI archives into the VM's
native k0s containerd and align the digest references before Helmfile sync.

- Bastion: bash, curl, jq, git, kubectl, k9s, ttyd, Zellij, code-server,
  Starship, Helix and vLLM bench. Python/PyTorch remain necessary for vLLM bench.
- Provision: Python, huggingface_hub, boto3, bcrypt, PyYAML and RustFS rc.
  Credential and model-import Jobs use this image; it contains no PyTorch.
- LFM3: dedicated Transformers/PyTorch runtime, with separate CPU and CUDA 12.8
  hash-locked dependencies, plus image, audio and video decoding libraries.

The terminal and editor use Nord and bundled Geist fonts. code-server serves
fonts from same-origin static assets to respect its Content Security Policy.
`EDITOR`, `VISUAL` and `KUBE_EDITOR` select Helix, including for k9s.
The workspace ConfigMap mounts the copied Starship configuration.

## Environment selection

The environment infrastructure JSON selects model releases explicitly. Suggested selections:

| Environment | Chat | Embeddings | Reranker | Multimodal |
| --- | --- | --- | --- | --- |
| default / devenv | qwen3-0-6b | qwen3-embedding-0-6b | qwen3-reranker-0-6b | lfm3-omni-2b |
| scaleway | qwen3-8b-fp8 | qwen3-embedding-4b | qwen3-reranker-4b | lfm3-omni-2b |

Select Scaleway with `helmfile -e scaleway -f platform/helmfile/helmfile.yaml.gotmpl`,
after creating the ignored `infra/infra-definition.scaleway.json`.
Start from `infra/infra-definition.scaleway.sample.json`, replace placeholder
access/network settings, and adapt machine sizing to the actual GPU instance.
This selects manifests; it does not create a cloud instance. Each model retains
its own namespace, chart, runtime, InferenceService and S3 prefix. Revisions and
downloaded file hashes, including LFM3 custom Python code, are locked.

GPU Operator installs Container Toolkit and Node Feature Discovery, using the
driver already supplied by the Scaleway image. Its device plugin, MIG manager
and DCGM deployment are disabled. HAMi owns GPU allocation; standalone DCGM
Exporter provides GPU metrics. GPU-only DaemonSets select
`nvidia.com/gpu.present: "true"` and schedule zero Pods on the CPU VM.

Toolkit targets `/etc/k0s/containerd.d/nvidia.toml`, reads
`/etc/k0s/containerd.toml` and uses `/run/k0s/containerd.sock`.
Provisional HAMi budgets are 24576 MiB / 50% cores for chat and 16384 MiB / 20%
each for embeddings and reranking, plus 12288 MiB / 10% for Omni. H100 runtime behavior and these budgets
require qualification on real hardware.

## LFM3 interface and qualification boundary

The dedicated adapter uses `AutoModelForImageTextToText` with the pinned local
custom code, `trust_remote_code=True` and `local_files_only=True`. Devenv selects
`MODEL_DEVICE=cpu`; Scaleway selects `MODEL_DEVICE=cuda` and HAMi GPU limits.
Set `images.omni` to the matching built variant's immutable reference. CUDA mode
requires an NVIDIA driver compatible with CUDA 12.8 and fails startup if CUDA is
unavailable, rather than silently falling back to CPU. Model weights use float32
on CPU and bfloat16 on CUDA. Video/audio decoding remains on CPU.

`POST /v1/chat/completions` accepts model `lfm3-omni-2b`. The adapter implements
complete responses, inline images, WAV input/output and inline video; each
modality must be qualified against the loaded model before being considered
operational. Streaming is currently rejected. The configured native context is
128000 tokens for input plus requested output; output remains bounded to 128
tokens per request. See [context windows](token-budgets.md). Other limits are
32 messages, a context-scaled character guard, four media items and 16 MiB of combined decoded
media. The HTTP body is limited to 24 MiB before JSON parsing, including chunked
requests. Images are limited to 16 megapixels before decoding and resized to
512×512. WAV input is limited to 30 seconds, two channels and 48 kHz. Video is
checked with a bounded ffprobe call: at most 30 seconds and 1920×1080 pixels,
then at most 16 sampled frames with a bounded processing pixel budget.
One request is processed at a time; Uvicorn bounds concurrent connections/tasks.
Malformed request structures return 422 without echoing prompts or media;
invalid media returns 400 and oversized requests return 413. Unsupported fields
and streaming are rejected rather than silently ignored.

Gateway connection buffer watermarks are 32 MiB for multimodal payloads; this
is not a universal HTTP file-size limit. Envoy JSON logs include request IDs,
model/backend, status, timing, byte counts and token usage. Client request IDs
are preserved; missing IDs are generated. Query strings and prompt bodies are
not logged. Token usage depends on the backend response and may be absent on
errors or unsupported endpoints.

After an authorized deployment and model readiness, qualify actual modalities:

```sh
python tests/qualify_omni.py --image fixture.png --audio fixture.wav --video fixture.mp4
```

This uses `LAB_ORIGIN`, `LAB_CREDENTIALS_FILE` and `LAB_CA_FILE`, like the other
model API checks. Fixture files must fit the limits above. A successful import
smoke test of an image is not this end-to-end inference qualification. Run the
same check on Scaleway during the later GPU qualification phase.

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
