# Implementation status

## Cluster and foundation milestones

- [x] Expose the upstream lifecycle directly through `task devenv:*`.
- [x] Keep tracked devenv runtime files unchanged; customize only ignored config.k.
- [x] Inherit CoreOS stable; the current CPU definition targets 12 vCPU, 48 GiB RAM and 64 GiB disk.
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

- [x] Replace LLMInferenceService with three CPU InferenceServices.
- [x] Split models into matching chart/release/namespace/S3-prefix domains; the environment selects imports and zero or one replica.
- [x] Import pinned model artifacts into RustFS and distribute a shared models-bucket account.
- [x] Qualify TLS, Bearer rejection, real chat/SSE, embeddings and reranking through the Gateway.
- [x] Replace participant isolation with one shared admin workstation and cluster-admin rights.
- [x] Provide Dex/oauth2-proxy, ttyd with Zellij CLI, code-server and administration tools.
- [x] Qualify the admin browser journey, terminal, editor, Headlamp and anonymous/header-spoof rejection.
- [x] Run vLLM bench from the bastion through the internal TLS/Bearer Gateway.
- [x] Distribute credential ownership to domain-local hooks; keep CA/TLS in gateway.
- [x] Publish the tested bastion and provision images to GHCR, verify anonymous pulls, then update environment pins.
- [x] Deploy Grafana, Loki, Tempo and Mimir separately with RustFS storage.
- [x] Deploy node and cluster OpenTelemetry Collector pipelines.
- [x] Configure HAMi/DCGM for eligible GPU nodes only; CPU qualification confirms zero GPU DaemonSet Pods.
- [x] Replace the umbrella CI with Helmfile qualification and tests of exact native OCI archives.

## Current follow-up

- [x] Replace the post-renderer with native chart extensions and the dex-config chart.
- [x] Qualify browser access, the Qwen model APIs, shared S3 permissions and credential/PVC preservation.
- [x] Fix HTTP/2 buffering and qualify audio responses with curl over HTTP/1.1 and HTTP/2.
- [x] Define native maximum context windows from pinned model configurations.
- [x] Qualify the 48-GiB platform bootstrap on the retained disk: after a native stop/start all three Qwen services became Ready at 40960/32768/40960 tokens, and TLS/Bearer, SSE, embeddings and reranking passed.
- [x] Verify the eight source credential fingerprints, bastion PVC identity and workspace access across the restart. All three locked snapshots passed the shared S3 access tests.
- [ ] Resolve the separate native Topgrade OS update failure: the attempted FCOS 44 to 45 upgrade cannot resolve the layered Cockpit and SELinux policy packages.
- [x] Add the observability stack without dashboards; dashboard design will be supplied later.
- [x] Verify a real chat request through the authenticated Grafana proxies: generation counter in Mimir, matching token total in Loki, and a correlated Gateway trace in Tempo.
- [x] Activate the replacement CI and publish tested lab OCI artifacts with authorized registry credentials.

Performance benchmarking is not requested. Scaleway infrastructure and public
ACME integration are deferred until these follow-ups are complete.

The previous umbrella and its tests describe the former full inference lab.
`tests/validate_storage.py` validates the current storage milestone. Development
reports remain ignored; source pushes and OCI publication require authorization.
