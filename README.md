# AI Inference Basics

<img src="docs/logo.png" alt="Devoteam AI Inference Basics" width="280">

A disposable QEMU VM with native single-node k0s. The current provisioning scope
is the base Kubernetes cluster only, using the existing devenv runtime.

```sh
task devenv:up     # create/provision the VM
task devenv:ssh    # connect to the VM
task devenv:down   # destroy the VM
```

See [local setup](docs/devenv.md) before the first run. The root Taskfile exposes
the upstream devenv tasks directly. No host artifact preparation is required.

## Structure

- `.devenv/config.k`: local VM provisioning, based on `exemple.config.k`.
- `infra/k0s/k0s.yaml`: minimal native k0s configuration, copied directly by Ignition.
- `infra/cloud-init/`, `infra/terraform/`: empty local placeholders, no cloud code.
- `oci/bastion/`: Fedora Minimal administration image with Zellij and CLI tools.
- `charts/ai-inference-basics/`: digest-pinned platform umbrella.
- `tests/`: offline checks; `reports/` is optional, local-only and ignored by Git.

The chart and OCI sources remain development material; they
are not invoked or deployed by the current VM lifecycle. Older platform documents
describe that broader lab, not the minimal cluster installed now.

**Current validation:** offline rendering and source checks only for this revised
provisioning flow. No VM was started, stopped or reconfigured during the refactor.

[Documentation](docs/README.md) · [Implementation status](docs/implementation-tracker.md)
