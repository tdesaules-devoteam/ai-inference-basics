# Versions and validation scope

| Component | Selection |
| --- | --- |
| devenv runtime | 895792e5980cb7fee1354bec5442fb42b483df93, unmodified |
| KCL | Operator-managed 0.13.3; rendering verified with the upstream correction |
| Fedora CoreOS | Default from the pinned runtime: 44.20261023.3.1 stable |
| Native k0s | v1.37.2+k0s.1, binary checksum pinned; native addon defaults |
| Host/guest Helm | 4.3.1 |
| Helmfile | 1.8.3 |
| Local Path Provisioner | 0.0.37, official OCI chart pinned by manifest digest |
| RustFS | 1.0.5, official HTTP Helm repository, exact version |
| cert-manager | v1.21.3, official OCI chart pinned by manifest digest |
| Envoy Gateway | v1.10.0, official OCI chart pinned by manifest digest |
| Agent Router | v1.2.1 controller and CRD charts, official OCI digests |
| Guest kubectl / k9s / Task | 1.37.2 / 0.51.0 / 3.54.0 |
| Bastion (legacy build, not deployed) | Fedora Minimal 45, Zellij 0.46.0 |

`platform/helm/helmfile.yaml.gotmpl` is the active dependency contract; Helmfile
retrieves upstream charts directly. OCI manifest digests and the RustFS HTTP version
are fixed there. The qualified RustFS archive checksum is checked in tests, and
values pin workload images. There is no deployment-time custom chart downloader.

Current render checks cover six Helmfile releases, image pins, namespace boundaries
and resource ownership. The foundation update was installed in the authorized
existing VM; a new clean boot of this complete milestone has not been tested.
The earlier authorized clean rebuild qualified the storage-only flow. Earlier full-lab
tests used the former umbrella orchestration; detailed development reports remain
ignored. See [platform setup](platform.md) for the current scope.

Official references:

- [k0s Helm deployer and local archives](https://docs.k0sproject.io/v1.37.2+k0s.1/helm-charts/)
- [devenv](https://github.com/tdesaules/qemu-dev-env)
- [KServe](https://kserve.github.io/website/)
- [Agent Router](https://github.com/theagentrouter/agent-router)
- [Zellij web client](https://zellij.dev/documentation/web-client.html)

The user approved official upstream images outside the project's build-base
allowlist. Project-owned bastion and CI builds still use allowed, pinned bases.
