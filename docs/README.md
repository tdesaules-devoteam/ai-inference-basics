# Documentation

<img src="logo.png" alt="Devoteam AI Inference Basics" width="220">

These living documents supersede the original implementation prompt and spec.
The [tracker](implementation-tracker.md) distinguishes requirements from evidence.

| Document | Purpose |
| --- | --- |
| [Architecture](architecture.md) | Scope, profiles and traffic paths |
| [Acceptance](acceptance.md) | Milestone gates and functional tests |
| [Model API](api.md) | Endpoints, aliases, API keys and prefix caching |
| [Development VM](devenv.md) | Local setup and lifecycle |
| [Naming and rebuild](naming-and-rebuild.md) | Source rename and operator-controlled VM reconstruction |
| [Security](security-and-access.md) | Dex, API keys and Kubernetes identities |
| [Workspaces](workspaces.md) | Fedora Minimal, Zellij tokens, tools and previews |
| [Observability](observability.md) | OTel signals, prefix cache and GPU telemetry |
| [Operations](operations-runbook.md) | Operator interface and recovery |
| [Versions](versions-and-compatibility.md) | Pins, provenance and compatibility |
| [Costs](cost-and-lifecycle.md) | Cloud gates, TTL and cleanup |
| [Cloud](cloud.md) | Terraform inputs and saved-plan workflow |
| [GPU](gpu.md) | HAMi, DCGM and NVIDIA runtime qualification |
| [CI and distribution](ci-and-distribution.md) | Workflow status and OCI publication |
| [Troubleshooting](troubleshooting.md) | Failure diagnosis |
| [Release notes](release-notes.md) | Implemented changes |
| [Decisions](adr/0001-platform-contract.md) | Agreed architecture decisions |
