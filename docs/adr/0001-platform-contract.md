# ADR 0001: platform contract

Status: accepted design; runtime qualification tracked separately.

- Native single-node k0s gives the local and cloud labs the same Kubernetes surface.
- Fedora CoreOS via the existing devenv submodule owns local VM mechanics. Start
  with 64 GiB disk; retain Ubuntu/cloud-init for Scaleway and GPU OS 13 for H100.
- One umbrella configuration with phased installation accommodates CRDs/webhooks.
- Keep LLMInferenceService for chat and InferenceService for pooling models;
  remove llm-d/EPP from this course and prove the no-EPP combination explicitly.
- Dex with two email accounts plus oauth2-proxy replaces Google and Keycloak.
- A static opaque Bearer key protects APIs independently from browser sessions.
- OpenTelemetry collects all signals; Prometheus/Loki/Tempo retain them.
- HAMi shares H100; standalone DCGM measures physical GPU state. No GPU Operator.
- Images use immutable digests; chart dependencies additionally require exact
  archive hashes/OCI manifest digests because Chart.lock alone is not content pinning.
- GHCR under this repository distributes the umbrella; qualify the exact package
  before publication and use its digest for deployment.
