# AI Inference Basics

<img src="docs/logo.png" alt="Devoteam AI Inference Basics" width="280">

A disposable QEMU VM with native single-node k0s. The current provisioning scope
includes native k0s plus Helmfile-managed storage and gateway foundations:
Local Path Provisioner, RustFS, cert-manager, Envoy Gateway and Agent Router.

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
- `platform/helm/`: ordered Helmfile releases and per-component values.
- `platform/units/`: inline tool installers, per-user kubeconfig generation and platform bootstrap.
- `platform/cloud-init/`, `platform/terraform/`: empty local placeholders, no cloud code.
- `oci/bastion/`: Fedora Minimal administration image with Zellij and CLI tools.
- `charts/`: reserved for project-authored charts to publish; current releases are upstream charts.
- `tests/`: offline checks; `reports/` is optional, local-only and ignored by Git.

See [the platform](docs/platform.md) for upstream chart references, namespace
boundaries, deployment and test commands.
Older platform documents describe the broader lab, not the components installed now.

**Current validation:** all six releases deployed in the authorized VM. A temporary
Gateway/Agent Router route returned a mock OpenAI response; signed S3 operations
and anonymous rejection passed, and test resources were removed. Reexecuting the
bootstrap preserved the PVC and credential Secrets. The full foundation milestone
has not yet had a clean-boot test. The former storage-bootstrap chart is removed;
no existing buckets were deleted.
RustFS credential generation and bucket initialization now run as pre/post Helm
hooks in extraManifests. Fresh-namespace creation, upgrade preservation and scoped
RBAC were qualified; the host credential service has been removed.

[Documentation](docs/README.md) · [Implementation status](docs/implementation-tracker.md)
