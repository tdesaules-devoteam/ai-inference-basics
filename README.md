# AI Inference Basics

<img src="docs/logo.png" alt="Devoteam AI Inference Basics" width="280">

A disposable QEMU CPU lab with native single-node k0s and 16 Helmfile releases:
storage, TLS and gateway foundations, three KServe inference services, Dex browser
authentication and one shared cluster-admin ttyd/Zellij and code-server workspace.
Each model has its own chart and namespace and starts with one replica by default.

```sh
task devenv:up     # create/provision the VM
task devenv:ssh    # connect to the VM
task devenv:down   # destroy the VM
```

See [local setup](docs/devenv.md) before the first run. The root Taskfile exposes
the upstream devenv tasks directly. The bastion currently requires an explicit
local image import; see [lab access and qualification](docs/lab.md).

## Structure

- `.devenv/config.k`: local VM provisioning, based on `exemple.config.k`.
- `platform/k0s/k0s.yaml`: minimal native k0s configuration, copied directly by Ignition.
- `platform/helmfile/`: ordered Helmfile releases, upstream chart values and checks.
- `infra/`: environment JSON schema/sample and the shared Helmfile values adapter.
- `platform/units/`: inline tool installers, per-user kubeconfig generation and platform bootstrap.
- `platform/cloud-init/`, `platform/terraform/`: empty local placeholders, no cloud code.
- `oci/bastion/`: Fedora Minimal administration image with Zellij and CLI tools.
- `charts/`: six model charts, one shared bastion chart and one gateway/TLS chart.
- `tests/`: render checks and opt-in runtime qualification; `reports/` stays local and ignored.

See [the platform](docs/platform.md) for upstream chart references, namespace
boundaries, deployment and test commands.
See [the lab](docs/lab.md) for browser paths, model APIs, credentials and image import.

**Current layout:** one Dex account named `admin` for pair training, full Kubernetes
administration from the bastion and Headlamp, separate Bearer model APIs and
prefix-scoped RustFS model credentials. The VM retains its 24-vCPU/48-GiB/64-GiB
sizing. Registry publication remains unavailable; a fresh VM requires explicit
bastion image import. See [qualification](docs/lab.md#validation).

**Foundation history:** a temporary
Gateway/Agent Router route returned a mock OpenAI response; signed S3 operations
and anonymous rejection passed, and test resources were removed. Reexecuting the
bootstrap preserved the PVC and credential Secrets. A subsequent user-initiated
down/up qualified the full foundation bootstrap from a clean VM without intervention.
All six releases reached revision 1 and both RustFS hooks completed. The former storage-bootstrap chart is removed;
no existing buckets were deleted.
RustFS credential generation and bucket initialization now run as pre/post Helm
hooks in extraManifests. Fresh-namespace creation, upgrade preservation and scoped
RBAC were qualified; the host credential service has been removed.

[Documentation](docs/README.md) · [Implementation status](docs/implementation-tracker.md)
