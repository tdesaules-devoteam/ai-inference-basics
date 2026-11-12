# Versions and validation scope

| Component | Selection |
| --- | --- |
| devenv runtime | 895792e5980cb7fee1354bec5442fb42b483df93, unmodified |
| KCL | Operator-managed 0.13.3; rendering verified with the upstream correction |
| Fedora CoreOS | Default from the pinned runtime: 44.20261023.3.1 stable |
| Native k0s | v1.37.2+k0s.1, binary checksum and addon image digests pinned |
| Host/guest Helm | 4.3.1 |
| Guest kubectl / k9s / Task | 1.37.2 / 0.51.0 / 3.54.0 |
| Bastion | Fedora Minimal 45, Zellij 0.46.0 |

The chart's Chart.yaml, Chart.lock, dependencies.sha256 and vendored archives are
the platform dependency contract. Values pin workload images and HF model revisions.
The k0s YAML retains native addon image pins. The bastion's Containerfile pins base
images, selected RPMs and downloaded tool checksums.

Current offline checks render the three storage releases from Helmfile, verify
image pins and reject resource ownership conflicts. An authorized clean VM rebuild
qualified the four inline units, storage releases and S3 access. Earlier full-lab
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
