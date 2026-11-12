# Local VM setup

The root Taskfile includes `.devenv/taskfile.qemu.yaml` directly under `devenv:`.
The current milestone adds Local Path Provisioner and RustFS through Helmfile to
the native single-node k0s VM. See [platform setup](platform.md).
There is no preparation or runtime dependency on the repository's `.local/` directory.

## Configuration

Initialize the pinned submodule with `git submodule update --init --recursive`.
Use the operator's existing Task, KCL, Butane, QEMU/KVM and native bridge/mDNS setup.
The runtime revision is `895792e5980cb7fee1354bec5442fb42b483df93`.
It supplies Fedora CoreOS 44.20261023.3.1 stable and normal provisioning units.

`.devenv/config.k` is ignored and user-owned. The current hardware is 24 vCPU,
49152 MiB RAM and 64 GiB disk. Beszel uses `http://10.10.10.1:8090`.
The native workspace share is unchanged; installation does not use it.

The k0s custom copy reads the tracked configuration directly, relative to the
runtime directory used by Task:

```kcl
custom_copies = [
    {
        source = "../platform/k0s/k0s.yaml"
        path = "/etc/k0s/k0s.yaml"
        mode = 384
        user.name = "root"
        group.name = "root"
    }
]
```

Additional custom copies place the Helmfile, values and local bootstrap chart
from `platform/helm/` under `/etc/ai-inference-basics/platform/helm`.
Units are loaded with KCL `file.read` from `../platform/units/`:

- `platform-k0s-install.service` installs native k0s;
- `platform-helm-install.service` installs Helm from get.helm.sh;
- `platform-helmfile-install.service` installs Helmfile from GitHub;
- `platform-kubectl-install.service` installs kubectl from dl.k8s.io;
- `platform-k9s-install.service` installs k9s from GitHub;
- `platform-curl-install.service` ensures the distribution curl package is available;
- `platform-kubeconfig@<user>.service` creates the administrator kubeconfig for the selected account;
- `platform-helm-charts-prepare.service` downloads and verifies chart sources;
- `platform-k0s-ready.service` waits for the API and Ready node;
- `platform-rustfs-credentials.service` creates or reuses the RustFS Secret;
- `platform-k0s-bootstrap.service` coordinates those dependencies and runs Helmfile.

The three preparation units are dependency-activated, not enabled independently.

All provisioning commands are inline in these units. Helm, kubectl and k9s are no
longer declared in `custom_mise_tools`. Helm, Helmfile, kubectl and k9s live in
`/usr/local/bin`; curl is the distribution binary at `/usr/bin/curl`.

The minimal YAML selects kube-router and disables telemetry. Remaining settings
and system images use the pinned k0s binary's defaults. It contains no Helm
extensions, application credentials or placeholders.

## Installation

The appended `platform-k0s-install.service` runs after normal devenv provisioning. It defers
installation when an rpm-ostree deployment is staged, allowing the runtime's
normal reboot to complete first. It then:

1. Downloads the AMD64 binary from the GitHub release `v1.37.2+k0s.1` into
   `/tmp/k0s.download`, isolated with systemd `PrivateTmp=yes`.
2. Verifies SHA-256 `4770cf89ff45e43292819f6e3a02a25a453bc750c777f6f7ad2de335f3f41df5`.
3. Installs it at `/usr/local/bin/k0s` with mode 0755 and validates `/etc/k0s/k0s.yaml`.
4. Creates the native service using `k0s install controller --single --config /etc/k0s/k0s.yaml`.
5. Enables and starts `k0scontroller.service`, then records successful installation
   in `/var/lib/k0s-install/initialized`.

Installation also creates the systemd alias `platform-k0s-controller.service`.
Both names refer to the same native service, preserving k0s start/stop behavior.
The alias is a symlink created by the installer, not a second controller process.

The downloaded file is removed after installation. Only the persistent installation
marker remains under `/var/lib/k0s-install`; keeping it outside `/tmp` prevents
installation from repeating after a reboot.

The installer is a oneshot; `k0scontroller.service` runs the cluster on subsequent
boots. `--single` includes both controller and worker roles without the additional
`--enable-worker` or `--no-taints` flags. This mode is not intended for expansion
into a multi-node cluster. See the [k0s Quick Start](https://docs.k0sproject.io/stable/install/).

## Commands and checks

```sh
task devenv:up
task devenv:ssh
task devenv:down
```

The upstream up task waits for its own provisioning, not Kubernetes readiness.
Inside the VM, inspect the installer and cluster explicitly:

```sh
sudo systemctl status platform-k0s-install.service k0scontroller.service
sudo systemctl status platform-k0s-controller.service
sudo journalctl -u platform-k0s-install.service -u k0scontroller.service
sudo k0s status
sudo k0s kubectl get nodes
sudo k0s kubectl get pods -A
```

k0s embeds kubectl; no user kubeconfig is required for these sudo commands.
The user kubeconfig unit also enables direct use without sudo or mise activation:

```sh
kubectl get nodes
kubectl get pods -A
k9s
helm list -A
```

The instance name selects the user, for example `platform-kubeconfig@tdesaules.service`.
Its home directory comes from the account database rather than a hardcoded path.
The `@` marks a systemd template; `%i` expands to the account name in the instance.
The unit waits for the API, creates `~/.kube` with mode 0700 and its admin config
with mode 0600 and the user's ownership. It preserves an existing config on reruns.

kubectl/k9s installation and kubeconfig generation were also applied and tested in
the existing VM without restarting it. This addition has not had a fresh-boot test.
The node may take a few minutes to become Ready while system images download.
The installation marker indicates service startup, not Kubernetes readiness.

Ignition copies files at first boot. Editing the host YAML does not update an
existing guest. Recreating the disposable VM requires the operator's permission.
An authorized destruction and recreation validated this layout on a clean guest
disk. The four inline units completed successfully after the normal CoreOS reboot;
the three Helmfile releases and S3 qualification Job passed without guest fixes.
Existing guests created from older recipes still require reprovisioning to receive
the renamed units and copied paths.
The later controller alias and focused bootstrap units are offline-validated only;
they have not been applied to the current guest.
