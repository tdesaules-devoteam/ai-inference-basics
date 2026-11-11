# Implementation tracker

## Source-only naming change

The project, chart, release/namespace defaults and API model aliases now use
`ai-inference-basics`. The logo is in `docs/logo.png`. This rename was performed
in repository files only; the VM and deployed resources were not migrated.
All runtime checkboxes below refer to the unchanged pre-rename evidence archived
under `reports/archive/pre-rename/`. They do not qualify a deployment with the new names.

Status: local CPU platform running and tested; cloud/hardware and publication gates
remain open. Checkboxes represent observed acceptance only. The user requested
local commits only, so no source push or hosted publication has been performed.

## G0 — Foundation

- [x] Read original requirements and record the user's superseding decisions.
- [x] Replace prompt/spec with living documentation and include project branding.
- [x] Inspect devenv and reference lab; resolve Fedora CoreOS 45 metadata.
- [x] Lock and qualify the local CPU dependency combination and active image digests.
- [x] Implement local Task interface, Helm schema/image checks and Terraform schema validation.
- [x] Implement three workflow files and run actionlint plus dedicated Docker action fixtures locally.
- [ ] Complete released CI action image publication, advisory hosted scans and release automation.
- [ ] Observe hosted CI execution (source remains local by explicit request).
- [ ] Publish/pull-verify umbrella chart in repository GHCR.

## G1 — Local VM and browser access

- [x] Render and boot 12-vCPU/32-GiB/64-GiB Fedora CoreOS 45 VM.
- [x] Verify shared root, native k0s, networking and persistence after reboot.
- [x] Validate Dex/oauth2-proxy with two accounts locally.
- [x] Validate Zellij/k9s tools, Headlamp and fixed-port Caddy previews in browser.

## G2 — CPU inference

- [x] Prove LLMInferenceService without llm-d/EPP.
- [x] Validate chat JSON/SSE, embedding and reranking with official Qwen models.
- [x] Validate static Bearer key policy and backend bypass denial.
- [x] Measure automatic prefix caching cold/warm behavior.

## G3 — Local complete journey

- [x] Query actual OTel-collected metrics, logs and traces.
- [x] Correlate one public chat trace through Envoy, Agent Router and vLLM.
- [x] Validate Helm upgrades, two Zellij workspaces, previews and read-oriented RBAC.
- [x] Verify 429 fault injection and restoration.
- [ ] Exercise a clean chart uninstall/reinstall and the elevated installer learning phase.

## G4 — Scaleway CPU

- [x] Typed Terraform/cloud-init, Task-driven plan/apply and provider-schema validation.
- [ ] Actual pilot TLS/Dex/inference tests and idempotent re-apply.
- [ ] Actual destroy and independent billable-resource audit.

## G5 — One H100

- [ ] GPU OS 13, k0s NVIDIA runtime, CUDA diagnostic, HAMi and DCGM.
- [ ] Four model Pods, concurrency, replica failure and VRAM evidence.
- [ ] Actual teardown and resource audit.

## G6 — Training

- [ ] Explicit eight-instance profile, enrollment and external eight-hour TTL.
- [ ] Timed two-user pilot, preload/recovery runbooks and final QA.
- [ ] Release 0.3.0 after all gates pass.

## Evidence and remaining prerequisites

- `reports/archive/pre-rename/local-cpu/G0/`: dependency pins, Docker action fixtures and advisory scan.
- `reports/archive/pre-rename/local-cpu/G1/`: runtime inventory, reboot, browser screenshots, native
  Zellij token rejection/cookie isolation, live k9s and backend-bypass denial.
- `reports/archive/pre-rename/local-cpu/G2/`: three API results, SSE and measured prefix-cache hits.
- `reports/archive/pre-rename/local-cpu/G3/`: correlated traces and rate-limit restoration.
- CPU cloud needs Scaleway credentials, project/image/zone selection, instructor
  CIDRs and controlled DNS/TLS. None were supplied or provisioned.
- H100 remains gated by actual CPU cloud validation and teardown. GPU charts and
  image/model pins are prepared/rendered, not hardware-qualified.
- GHCR/hosted CI awaits the owner's source push and workflow/package permissions.
- The AMD64 administration-image advisory scan found 7 Critical and 55 High
  matches; detailed package/fix data is in `G0/security.json`. These are reported,
  not used as a functional release gate.
