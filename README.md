# AI Inference Basics

<img src="docs/logo.png" alt="Devoteam AI Inference Basics" width="280">

A disposable QEMU VM with native single-node k0s. The current provisioning scope
includes a native base cluster and the first Helmfile milestone: Local Path
Provisioner, RustFS and an S3 initialization/qualification Job.

```sh
task devenv:up     # create/provision the VM
task devenv:ssh    # connect to the VM
task devenv:down   # destroy the VM
```

See [local setup](docs/devenv.md) before the first run. The root Taskfile exposes
the upstream devenv tasks directly. No host artifact preparation is required.

## Structure

- `.devenv/config.k`: local VM provisioning, based on `exemple.config.k`.
- `platform/k0s/k0s.yaml`: minimal native k0s configuration, copied directly by Ignition.
- `platform/helm/`: ordered Helmfile releases, values, local charts and chart-source checksums.
- `platform/units/`: inline installation units for k0s, Helm, Helmfile and platform bootstrap.
- `platform/cloud-init/`, `platform/terraform/`: empty local placeholders, no cloud code.
- `oci/bastion/`: Fedora Minimal administration image with Zellij and CLI tools.
- `charts/ai-inference-basics/`: digest-pinned platform umbrella.
- `tests/`: offline checks; `reports/` is optional, local-only and ignored by Git.

The previous umbrella chart and OCI sources remain migration material. See
[the storage platform](docs/platform.md) for the active deployment and test commands.
Older platform documents describe the broader lab, not the components installed now.

**Current validation:** Helmfile rendering and source checks pass. The authorized
VM run validated the three storage releases, S3 access and persistence across a
RustFS pod replacement and Helmfile reexecution. The subsequent directory and unit
reorganization is offline-validated only; the running VM retains the previous layout.

[Documentation](docs/README.md) · [Implementation status](docs/implementation-tracker.md)
