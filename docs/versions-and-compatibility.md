# Versions and validation scope

| Component | Selection |
| --- | --- |
| devenv runtime | 37369bd7590dd31a0b175115441984c19a50c770, unmodified |
| KCL | Operator-managed 0.13.3; rendering verified with the upstream correction |
| Fedora CoreOS | Lab config: 45.20261030.3.1 stable, with Fedora 45 SELinux policy for Cockpit |
| Native k0s | v1.37.2+k0s.1, binary checksum pinned; native addon defaults |
| Host/guest Helm | 4.3.1 |
| Helmfile | 1.8.3 |
| Local Path Provisioner | 0.0.37, official OCI chart pinned by manifest digest |
| RustFS | 1.0.5, official HTTP Helm repository, exact version |
| cert-manager | v1.21.3, official OCI chart pinned by manifest digest |
| Envoy Gateway | v1.10.0, official OCI chart pinned by manifest digest |
| Agent Router | v1.2.1 controller and CRD charts, official OCI digests |
| Guest kubectl / k9s / Task | 1.37.2 / 0.51.0 / 3.54.0 |
| Bastion | Fedora Minimal 45; tool versions and hashes in `oci/bastion/tools.lock` |

`platform/helmfile/helmfile.yaml.gotmpl` is the active dependency contract; Helmfile
retrieves upstream charts directly. OCI manifest digests and the RustFS HTTP version
are fixed there. The qualified RustFS archive checksum is checked in tests, and
values pin workload images. There is no deployment-time custom chart downloader.

Current render checks cover the full Helmfile platform, CPU/GPU selection, disabled
models, image pins, namespace boundaries and resource ownership. Unit checks cover
environment validation, credential handling, reload patches and model convergence.
The current FCOS 45 CPU platform has passed a blank-disk bootstrap with real
model APIs and browser/telemetry checks. The earlier six-release foundation update was installed in the authorized
existing VM and then qualified from scratch during a user-initiated down/up, with
all six releases at revision 1 and both RustFS hooks completing without intervention.
The earlier authorized clean rebuild qualified the storage-only flow. Earlier full-lab
tests used the former umbrella orchestration; detailed development reports remain
ignored. See [platform setup](platform.md) for the current scope.

Official references:

- [k0s Helm deployer and local archives](https://docs.k0sproject.io/v1.37.2+k0s.1/helm-charts/)
- [devenv](https://github.com/tdesaules/qemu-dev-env)
- [KServe](https://kserve.github.io/website/)
- [Agent Router](https://github.com/theagentrouter/agent-router)
- [Zellij](https://zellij.dev/documentation/)

The user approved official upstream images outside the project's build-base
allowlist. Project-owned bastion and CI builds still use allowed, pinned bases.
