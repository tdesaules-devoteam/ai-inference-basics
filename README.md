# AI Inference Basics

<img src="docs/logo.png" alt="Devoteam AI Inference Basics" width="280">

A disposable, browser-first Kubernetes inference lab for **AI Inference Basics**
Native single-node k0s runs three official Qwen models behind Envoy Gateway and
Agent Router (Envoy AI Gateway). Helm owns platform configuration; Task is the
operator interface. This repository is under implementation, not a ready release.

## Start here

- [Documentation index](docs/README.md)
- [Architecture and scope](docs/architecture.md)
- [Implementation tracker](docs/implementation-tracker.md)
- [Local development VM](docs/devenv.md)
- [Naming and explicit rebuild](docs/naming-and-rebuild.md)
- [Operations](docs/operations-runbook.md)
- [Security and access](docs/security-and-access.md)
- [Versions and compatibility](docs/versions-and-compatibility.md)
- [Acceptance criteria](docs/acceptance.md)

## Delivery sequence

1. Local QEMU/KVM CPU: Fedora CoreOS, 12 vCPU, 32 GiB RAM, 64 GiB disk.
2. One Scaleway CPU pilot: Terraform/cloud-init, DNS/TLS, Dex authentication,
   re-apply and complete resource teardown.
3. One Scaleway H100 pilot: GPU OS 13, HAMi, DCGM, two chat replicas and BF16
   embedding/reranker. Training fleet creation remains gated by pilot evidence.

Browser access uses **Dex + oauth2-proxy**, two email-based accounts, Zellij/k9s,
Headlamp and Caddy previews. Model APIs use an independent static Bearer key.
OpenTelemetry collects metrics, logs and traces for Prometheus, Loki, Tempo and
Grafana. Chat prefix caching is explicitly tested.

Google, Keycloak, llm-d/EPP and the game application are outside this MVP.

## Distribution

The umbrella chart is intended for
`oci://ghcr.io/tdesaules-devoteam/ai-inference-basics/charts/ai-inference-basics`.
Images and chart archives must be digest/checksum locked. An intended registry
location is not evidence of publication; see the tracker for actual status.

## Development

```sh
git submodule update --init --recursive
task --list
```

Follow the local VM guide before launching. Keep passwords, API keys, kubeconfigs,
Terraform state and generated Ignition outside Git. Commits use Conventional
Commits; deployment evidence is stored under `reports/` after sanitization.

The administration Pods use **Fedora Minimal 45** with bash, curl, kubectl, k9s,
Helm, Task and **Zellij 0.46.0's native web client**. Zellij requires a second,
workspace-specific login token after Dex sign-in; ttyd has been replaced.
See [browser workspaces](docs/workspaces.md) for credentials and URLs.
