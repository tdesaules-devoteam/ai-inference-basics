# Implementation status

## Cluster and storage milestone

- [x] Expose the upstream lifecycle directly through `task devenv:*`.
- [x] Keep tracked devenv runtime files unchanged; customize only ignored config.k.
- [x] Inherit CoreOS 44 stable with 24 vCPU, 48 GiB RAM and 64 GiB disk.
- [x] Install verified k0s inline and copy the minimal tracked configuration directly.
- [x] Make Helmfile the sole owner of platform releases, with explicit dependencies.
- [x] Add Local Path Provisioner, standalone RustFS and the S3 initialization Job.
- [x] Verify tool/source archive checksums and pin workload/init/helper images by digest.
- [x] Validate Helmfile rendering, dependency order, namespaces and storage offline.
- [x] Qualify S3 access, pod persistence and Helmfile reexecution in the authorized VM.
- [ ] Repeat a clean boot of the final recipe; the first run required source/guest fixes.

## Subsequent milestones

- [ ] Deploy cert-manager, Envoy Gateway and Agent Router in dedicated namespaces.
- [ ] Replace LLMInferenceService with three InferenceServices in inference-service.
- [ ] Import pinned model artifacts into RustFS and configure read-only S3 access.
- [ ] Provide Dex/oauth2-proxy, ttyd with Zellij CLI, code-server and administration tools.
- [ ] Deploy Grafana, Loki, Tempo and Mimir separately with RustFS storage.
- [ ] Deploy node and cluster OpenTelemetry Collector pipelines.
- [ ] Configure HAMi/DCGM for eligible GPU nodes only.
- [ ] Migrate legacy umbrella tests and CI to the complete Helmfile platform.

The previous umbrella and its tests describe the former full inference lab.
`tests/validate_storage.py` validates the current storage milestone. Development
reports remain ignored; source pushes and OCI publication require authorization.
