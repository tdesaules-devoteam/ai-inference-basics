# Implementation tracker

Status: implementation in progress. Checkboxes represent observed acceptance only.

## G0 — Foundation

- [x] Read original requirements and record the user's superseding decisions.
- [x] Replace prompt/spec with living documentation and include project branding.
- [x] Inspect devenv and reference lab; resolve Fedora CoreOS 45 metadata.
- [ ] Lock and qualify platform versions and immutable artifacts.
- [ ] Implement Task interface and static checks.
- [ ] Implement and observe three-workflow CI.
- [ ] Publish/pull-verify umbrella chart in repository GHCR.

## G1 — Local VM and browser access

- [ ] Render and boot 12-vCPU/32-GiB/64-GiB Fedora CoreOS VM.
- [ ] Verify shared root, native k0s, networking and persistence after reboot.
- [ ] Validate Dex/oauth2-proxy with two accounts locally.
- [ ] Validate ttyd/k9s, Headlamp and fixed-port Caddy previews in browser.

## G2 — CPU inference

- [ ] Prove LLMInferenceService without llm-d/EPP.
- [ ] Validate chat JSON/SSE, embedding and reranking with official Qwen models.
- [ ] Validate static Bearer key policy and backend bypass denial.
- [ ] Measure automatic prefix caching cold/warm behavior.

## G3 — Local complete journey

- [ ] Query actual OTel-collected metrics, logs and traces.
- [ ] Validate upgrades, two workspaces, previews, RBAC and recovery.

## G4 — Scaleway CPU

- [ ] Typed Terraform/cloud-init, Task-driven plan/apply and provider validation.
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
