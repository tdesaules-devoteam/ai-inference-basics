# Versions and compatibility

Pins are researched independently from runtime qualification. A resolved artifact
is not proof that the selected controllers interoperate.

| Component | Selected baseline | Evidence/status |
| --- | --- | --- |
| qemu-dev-env | c60632ccee08750adc5c6531efccfbaee9a06eae | Upstream HEAD inspected |
| Fedora CoreOS | 45.20261030.2.1 testing | Official stream metadata, 2026-11-11 |
| Stable FCOS alternative | 44.20261023.3.1 | Stable is not yet Fedora 45 |
| KCL host | 0.13.3 | Installed CLI inspected |
| Butane host | 0.29.0 | Installed CLI inspected |
| k0s / Kubernetes | v1.37.2+k0s.1 | Native local node Ready; active images pinned |
| Helm operator | 4.3.1 | Download checksum verified |
| Envoy Gateway | 1.10.0 | HTTPS, Bearer policy and tracing tested |
| Agent Router | 1.2.1 | Official repository redirects to theagentrouter/agent-router |
| cert-manager | 1.21.3 | Webhooks and serving-controller certificates Ready |
| KServe | 0.21.0 | LLMInferenceService without scheduler; pooling InferenceServices Ready |
| vLLM CPU | 0.32.0 | Three official Qwen checkpoints tested |
| Dex | 2.46.1 / chart 0.26.0 | Two real browser login flows tested |
| oauth2-proxy | 7.15.6 | Redirects, cookies, invalid accounts/passwords and WebSockets |
| Headlamp | 0.46.0 | Read-oriented SA behind proxy |
| Zellij | 0.46.0 | Native web, token rejection, scoped cookies and shell output tested |
| Caddy | 2.10.2-alpine | Local terminal proxy and fixed-port preview tested |
| otel-lgtm | 0.40.0 | Metrics, logs, traces and correlated model request tested |
| HAMi | 2.11.0 | Chart/image pins and GPU render only |
| DCGM Exporter | 4.9.0 | Chart/image pins and OTel scrape config only |
| NVIDIA Toolkit | 1.20.1 | Selected official release; hardware qualification pending |
| Terraform / Scaleway | 1.17.2 / 2.91.0 | Native and Docker fmt/init/validate; no apply |

FCOS compressed QEMU SHA-256:

- x86_64: `420f428010ba880200e5b83c116cdc4a804652efc4bbcd4846c8d3e860928f88`
- aarch64: `d0e1786961d08f801e1af24eb87616cd7aabbda372d30b5d9e8dc6e19537011b`

Source: <https://builds.coreos.fedoraproject.org/streams/testing.json>.
Only Linux/x86_64 boot will be qualified on this workstation.

The exact Helm dependency contract is `Chart.yaml` + `Chart.lock` +
`dependencies.sha256`, with upstream archives vendored unchanged. `Chart.lock`
alone does not pin archive contents. Values pin workload images; the live Pod audit
also checks injected containers. `infra/k0s/images.lock.json` records native addon
images. `reports/archive/pre-rename/local-cpu/G0/dependencies.json` records the collected baseline.

KServe's official v0.21.0 CPU no-scheduler example and controller source confirm
that LLMInferenceService can run without EPP. This implementation uses an explicit
minimal single-node preset, omits spec.router and lets Agent Router own the public
route. KServe owns the workload and internal Service. No GIE/LWS controller is
needed for this qualified single-node path; no InferencePool or EPP was installed.
The inherited `llm-d.ai/role` Pod label is not a running llm-d dependency.

The vLLM 0.32 CPU backend applies `--gpu-memory-utilization` to CPU memory despite
the flag's name. The default reservation failed under cgroup limits; 0.5 plus
bounded concurrency passed. KServe's 1-GiB storage initializer also OOMed; 3 GiB
passed. Preserve these measured adjustments instead of interpreting them as GPU
emulation. Reranking uses the tested Cohere-compatible `/cohere/v2/rerank` route.

The user approved official upstream image bases outside the container skill's
allowlist, with digest/provenance recorded. Project builds retain approved bases:
Fedora Minimal for administration and Fedora/Minimal for dedicated CI operations.
otel-lgtm's official recipe uses UBI9 and is covered by that explicit exception.
GPU profile versions are pinned candidates, not a compatibility claim.

Official references: [k0s](https://docs.k0sproject.io/),
[KServe](https://kserve.github.io/website/),
[Envoy Gateway](https://gateway.envoyproxy.io/),
[Envoy AI Gateway](https://aigateway.envoyproxy.io/),
[vLLM](https://docs.vllm.ai/), [Dex](https://dexidp.io/docs/),
[oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/),
[OpenTelemetry](https://opentelemetry.io/docs/collector/).
