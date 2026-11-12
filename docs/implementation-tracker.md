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
- [x] Consolidate sources in platform/ and inline provisioning into four dedicated units.
- [x] Destroy and recreate the VM: all four inline units and three releases succeeded without guest fixes.
- [x] Add native kubectl/k9s/curl units and per-user kubeconfig generation; validate direct kubectl access in the running VM.
- [x] Add a native-controller alias and split bootstrap responsibilities into focused inline units (offline checks).
- [ ] Qualify a fresh boot of the expanded administration-tool units and future cloud-init integration.

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
