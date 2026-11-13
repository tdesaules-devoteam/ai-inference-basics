# Implementation status

## Cluster and foundation milestones

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
- [x] Retrieve official OCI charts by digest and RustFS from its HTTP repository at an exact version.
- [x] Fold six-bucket initialization into RustFS extraManifests; remove the separate storage-bootstrap chart.
- [x] Replace the host credential service with ordered pre-install/pre-upgrade hooks; qualify creation, RBAC and upgrade preservation in an isolated namespace.
- [x] Deploy cert-manager, Envoy Gateway and Agent Router in dedicated namespaces.
- [x] Qualify the gateway-to-Agent-Router mock OpenAI request path, S3 access and temporary-resource cleanup.
- [x] Reexecute the six-release bootstrap and verify PVC/credential preservation.
- [x] Observe user-initiated clean down/up: native tools, kubeconfig, controller alias, six releases and RustFS pre/post hooks succeeded without intervention.
- [ ] Qualify future cloud-init integration.

## Subsequent milestones

- [x] Replace LLMInferenceService with three CPU InferenceServices in inference-service.
- [x] Import pinned model artifacts into RustFS and configure read-only S3 access.
- [x] Qualify TLS, Bearer rejection, real chat/SSE, embeddings and reranking through the Gateway.
- [x] Qualify participant RBAC, independent PVCs and direct-access network isolation.
- [x] Provide Dex/oauth2-proxy, ttyd with Zellij CLI, code-server and administration tools.
- [x] Qualify both browser journeys, terminal commands, editors, Headlamp and cross-user/header-spoof rejection.
- [x] Run vLLM bench from a participant bastion through the internal TLS/Bearer Gateway.
- [ ] Publish the bastion image when registry authorization is available; local import is required meanwhile.
- [ ] Deploy Grafana, Loki, Tempo and Mimir separately with RustFS storage.
- [ ] Deploy node and cluster OpenTelemetry Collector pipelines.
- [ ] Configure HAMi/DCGM for eligible GPU nodes only.
- [ ] Migrate legacy umbrella tests and CI to the complete Helmfile platform.

The previous umbrella and its tests describe the former full inference lab.
`tests/validate_storage.py` validates the current storage milestone. Development
reports remain ignored; source pushes and OCI publication require authorization.
