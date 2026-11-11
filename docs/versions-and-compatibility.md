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

FCOS compressed QEMU SHA-256:

- x86_64: `420f428010ba880200e5b83c116cdc4a804652efc4bbcd4846c8d3e860928f88`
- aarch64: `d0e1786961d08f801e1af24eb87616cd7aabbda372d30b5d9e8dc6e19537011b`

Source: <https://builds.coreos.fedoraproject.org/streams/testing.json>.
Only Linux/x86_64 boot will be qualified on this workstation.

Before chart implementation, resolve k0s/Kubernetes, cert-manager, Gateway API,
Envoy Gateway, Envoy AI Gateway, KServe and any required LWS/GIE versions from
official releases. Specifically prove LLMInferenceService without llm-d/EPP.
Record chart versions, archive hashes, OCI digests, image digests and HF commits.
Dependencies must fail closed on missing pins; no `latest` in deployed resources.

Official references: [k0s](https://docs.k0sproject.io/),
[KServe](https://kserve.github.io/website/),
[Envoy Gateway](https://gateway.envoyproxy.io/),
[Envoy AI Gateway](https://aigateway.envoyproxy.io/),
[vLLM](https://docs.vllm.ai/), [Dex](https://dexidp.io/docs/),
[oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/),
[OpenTelemetry](https://opentelemetry.io/docs/collector/).
