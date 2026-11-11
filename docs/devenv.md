# Local VM setup

The root Taskfile directly includes `.devenv/taskfile.qemu.yaml`, using the same
integration as thales-genai-lab. Only the ignored `.devenv/config.k` is customized;
the runtime source, UUID and existing VM are not modified by this refactor.

## Host prerequisites

Linux x86_64, KVM, QEMU/qemu-img, Task, compatible KCL, Butane, SSH, curl, jq, gpgv, xz, SHA-256,
Python 3.11+, rootless Podman/Skopeo, and the existing br-qemu/helper/mDNS setup.
Normal devenv sudo requirements apply. The host bridge remains host-owned.

`task up` prepares pinned Helm 4.3.1 for packaging. Task and KCL are resolved from
the operator's existing environment: the local KCL download and Taskfile PATH
override have been reverted. No global tool installation or configuration is changed.

The currently installed KCL 0.13.3 rejects the upstream runtime's external file
probes. This compatibility issue still affects the native up/down lifecycle.
`task ssh` reads the persisted .devenv/.uuid and connects directly with the runtime's
SSH options; connecting to an existing VM does not evaluate KCL.

```sh
git submodule update --init --recursive
cp -n .devenv/exemple.config.k .devenv/config.k
```

For a new checkout, adapt that local file using the configuration below. Preserve
existing user choices. It keeps the runtime's default packages, mise tools, copies
and units, and adds project provisioning through custom fields and `units +=`.

The selected image is Fedora CoreOS 45.20261030.2.1 **testing**, with both published
architecture checksums pinned. Only Linux/x86_64 rendering is checked here.

```kcl
import file
import .schema as schema

_root = file.read_env("AI_INFERENCE_BASICS_ROOT")
_user = option("qemu_butane_user_name")
_hardware = schema.Hardware {
    cpu = 12
    memory = schema.Memory {size = 32, unit = "G"}
    disk = schema.Disk {size = 64, unit = "G"}
}
_base = schema.Qemu {hardware = _hardware}

config = schema.Qemu {
    os.version = "45.20261030.2.1"
    os.streams = "testing"
    checksum.x86_64 = "420f428010ba880200e5b83c116cdc4a804652efc4bbcd4846c8d3e860928f88"
    checksum.aarch64 = "d0e1786961d08f801e1af24eb87616cd7aabbda372d30b5d9e8dc6e19537011b"
    hardware = _hardware
    # Native Task include runs in .devenv; share the target repository instead.
    command.options = [
        (arg.replace("path=${file.read_env('PWD')},security_model=passthrough", "path=${_root},security_model=passthrough") if arg.startswith("-fsdev local,id=fsdev1,") else arg)
        for arg in _base.command.options
    ]
    butane = schema.Butane {
        custom_pkgs = ["jq", "openssl", "python3-pyyaml", "python3-bcrypt"]
        custom_mise_tools = {
            "kubectl" = "1.37.2"
            "helm" = "4.3.1"
            "github:derailed/k9s" = "0.51.0"
            "github:go-task/task" = "3.54.0"
        }
        custom_copies = [
            {source = "${_root}/infra/k0s/k0s.yaml", path = "/etc/ai-inference-basics/k0s.yaml", user.name = "root", group.name = "root"}
            {source = "${_root}/.local/build/artifacts.json", path = "/etc/ai-inference-basics/artifacts.json", user.name = "root", group.name = "root"}
            {source = "${_root}/cluster/bootstrap.sh", path = "/usr/local/sbin/ai-inference-basics-bootstrap", mode = 493, user.name = "root", group.name = "root"}
            {source = "${_root}/cluster/provision.py", path = "/usr/local/lib/ai-inference-basics/provision.py", mode = 493, user.name = "root", group.name = "root"}
        ]
        units += [
            {
                name = "ai-inference-basics-bootstrap.service"
                enabled = True
                contents = """\
[Unit]
Description=Provision the AI Inference Basics lab
ConditionVirtualization=vm
Wants=network-online.target
Requires=run-topgrade.service
After=network-online.target run-topgrade.service
RequiresMountsFor=/var/home/${_user}/workspace

[Service]
Type=oneshot
RemainAfterExit=yes
TimeoutStartSec=1800
ExecStart=/usr/local/sbin/ai-inference-basics-bootstrap /var/home/${_user}/workspace

[Install]
WantedBy=multi-user.target
"""
            }
        ]
    }
}
```

Preparation creates `.local/build/artifacts.json`, the chart archive and bastion
OCI archive before devenv renders Ignition. Required text files are copied into
the guest; binary archives are read from the shared repository and checksum-verified.
The bootstrap waits for ordinary provisioning, handles the staged reboot by
deferring to devenv, installs k0s and waits for its Helm deployer.

```sh
task up
task ssh
task down
```

`down` destroys the guest disk. config.k and the checkout identity remain managed
by the original runtime. Guest credentials, sessions and telemetry are disposable;
there is no host credential backup/rename step or manual known_hosts cleanup.

The local config is user-owned and ignored by Git. Its tracked supporting inputs
are `infra/k0s/k0s.yaml`, `cluster/` and the prepared artifacts under `.local/build`.
Git does not preserve truly empty directories: cloud-init/terraform placeholders
exist locally but contain no tracked files.
