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
        source = "../infra/k0s/k0s.yaml"
        path = "/etc/k0s/k0s.yaml"
        mode = 384
        user.name = "root"
        group.name = "root"
    }
]
```

Additional custom copies place the Helmfile, values, local bootstrap chart,
artifact lock and scripts from `platform/` under `/etc/ai-inference-basics/platform`.
The appended platform unit reads `../platform/platform-install.service` through
KCL `file.read`; it runs Helmfile after k0s is available.

The minimal YAML selects kube-router and disables telemetry. Remaining settings
and system images use the pinned k0s binary's defaults. It contains no Helm
extensions, application credentials or placeholders.

## Installation

The appended `k0sinstall.service` runs after normal devenv provisioning. It defers
installation when an rpm-ostree deployment is staged, allowing the runtime's
normal reboot to complete first. It then:

1. Downloads the AMD64 binary from the GitHub release `v1.37.2+k0s.1` into
   `/tmp/k0s.download`, isolated with systemd `PrivateTmp=yes`.
2. Verifies SHA-256 `4770cf89ff45e43292819f6e3a02a25a453bc750c777f6f7ad2de335f3f41df5`.
3. Installs it at `/usr/local/bin/k0s` with mode 0755 and validates `/etc/k0s/k0s.yaml`.
4. Creates the native service using `k0s install controller --single --config /etc/k0s/k0s.yaml`.
5. Enables and starts `k0scontroller.service`, then records successful installation
   in `/var/lib/k0s-install/initialized`.

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
sudo systemctl status k0sinstall.service k0scontroller.service
sudo journalctl -u k0sinstall.service -u k0scontroller.service
sudo k0s status
sudo k0s kubectl get nodes
sudo k0s kubectl get pods -A
```

k0s embeds kubectl; no generated user kubeconfig is required for these commands.
The node may take a few minutes to become Ready while system images download.
The installation marker indicates service startup, not Kubernetes readiness.

Ignition copies files at first boot. Editing the host YAML does not update an
existing guest. Recreating the disposable VM requires the operator's permission.
The native k0s boot and storage platform have been exercised in the VM. The storage
qualification required two source/guest corrections (temporary kubeconfig ordering
and the upstream RustFS Service name). See the current scope in [platform setup](platform.md).
