# AI Inference Basics

<img src="docs/logo.png" alt="Devoteam AI Inference Basics" width="280">

A disposable, browser-first inference lab on native single-node k0s. The VM is
created and provisioned from scratch through the existing QEMU devenv runtime.

```sh
task up     # prepare artifacts, create/provision VM, wait for the lab
task ssh    # connect to the VM
task down   # destroy the VM
```

See [local setup](docs/devenv.md) before the first run. These are the only public
Task commands; preparation and readiness functions are delegated to internal tasks.

## Structure

- `.devenv/config.k`: local VM provisioning, based on `exemple.config.k`.
- `infra/k0s/k0s.yaml`: native k0s configuration and ordered Helm deployment.
- `infra/cloud-init/`, `infra/terraform/`: empty local placeholders, no cloud code.
- `oci/bastion/`: Fedora Minimal administration image with Zellij and CLI tools.
- `cluster/`: host configuration preparation, readiness checks and internal tasks.
- `charts/ai-inference-basics/`: digest-pinned platform umbrella.
- `tests/`: offline checks; `reports/` is optional, local-only and ignored by Git.

k0s's Helm deployer installs the local packaged chart. The future OCI destination
is `oci://ghcr.io/tdesaules-devoteam/ai-inference-basics/charts/ai-inference-basics`;
publication is not needed for this local version and has not been performed.

The platform includes Envoy Gateway, Agent Router, KServe/vLLM and three official
Qwen CPU models, Dex/oauth2-proxy, Zellij bastions, Headlamp, Caddy previews and
OpenTelemetry. Google and llm-d/EPP are outside this version.

**Current validation:** offline rendering and source checks only for this revised
provisioning flow. No VM was started, stopped or reconfigured during the refactor.

[Documentation](docs/README.md) · [Implementation status](docs/implementation-tracker.md)
