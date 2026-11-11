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

The selected upstream runtime includes the host-file access correction for KCL
0.13.3. Configuration and Butane rendering pass with that installed version.
`task ssh` reads the persisted .devenv/.uuid and connects directly with the runtime's
SSH options; connecting to an existing VM does not evaluate KCL.

```sh
git submodule update --init --recursive
cp -n .devenv/exemple.config.k .devenv/config.k
```

For a new checkout, adapt that local file using the configuration below. Preserve
existing user choices. It keeps the runtime's default packages, mise tools, copies
and units, and adds project provisioning through custom fields and `units +=`.

Image version, stream and checksums are inherited from the pinned devenv revision:
currently Fedora CoreOS 44.20261023.3.1 **stable**. config.k does not override them.
Hardware is declared once directly in config. Only the repository workspace path
is adapted in the native QEMU options. Only Linux/x86_64 rendering is checked here.

```kcl
import file
import .schema as schema

config = schema.Qemu {
    hardware = schema.Hardware {
        cpu = 24
        memory = schema.Memory {
            size = 49152
            unit = "M"
        }
        disk = schema.Disk {
            size = 64
            unit = "G"
        }
    }

    # Share the repository, not just the runtime directory containing this file.
    command.options = [
        arg.replace(
            "-fsdev local,id=fsdev1,path=${file.read_env('PWD')},",
            "-fsdev local,id=fsdev1,path=${file.read_env('AI_INFERENCE_BASICS_ROOT')},"
        )
        for arg in schema.Qemu {
            hardware = hardware
        }.command.options
    ]

    butane = schema.Butane {
        custom_pkgs = [
            "jq"
            "openssl"
        ]
        custom_mise_tools = {
            "kubectl" = "1.37.2"
            "helm" = "4.3.1"
            "github:derailed/k9s" = "0.51.0"
            "github:go-task/task" = "3.54.0"
        }
        beszel = {
            url = "http://10.10.10.1:8090"
        }
        custom_copies = [
            {
                source = "${file.read_env('AI_INFERENCE_BASICS_ROOT')}/.local/build/runtime/k0s.yaml"
                path = "/etc/k0s/k0s.yaml"
                mode = 384
                user.name = "root"
                group.name = "root"
            }
            {
                source = "${file.read_env('AI_INFERENCE_BASICS_ROOT')}/.local/build/runtime/credentials.yaml"
                path = "/var/lib/k0s/manifests/ai-inference-basics/credentials.yaml"
                mode = 384
                user.name = "root"
                group.name = "root"
            }
        ]
        units += [
            {
                name = "ai-inference-basics-bootstrap.service"
                enabled = True
                contents = """\
[Unit]
Description=Install native k0s for AI Inference Basics
ConditionVirtualization=vm
ConditionPathExists=!/var/lib/ai-inference-basics/initialized
Wants=network-online.target
Requires=run-topgrade.service
After=network-online.target run-topgrade.service
RequiresMountsFor=/var/home/${option('qemu_butane_user_name')}/workspace

[Service]
Type=oneshot
RemainAfterExit=yes
TimeoutStartSec=600
WorkingDirectory=/var/home/${option('qemu_butane_user_name')}/workspace/.local/build
ExecCondition=/usr/bin/bash -ec 'rpm-ostree status --json | jq -e ".deployments[0].booted == true" >/dev/null'
ExecStart=/usr/bin/install -d -m 0755 /usr/local/bin /var/lib/k0s/charts
ExecStart=/usr/bin/install -d -m 0700 /var/lib/ai-inference-basics
ExecStart=/usr/bin/curl --fail --location --retry 3 --output /var/lib/ai-inference-basics/k0s.download https://github.com/k0sproject/k0s/releases/download/v1.37.2+k0s.1/k0s-v1.37.2+k0s.1-amd64
ExecStart=/usr/bin/bash -ec 'echo "4770cf89ff45e43292819f6e3a02a25a453bc750c777f6f7ad2de335f3f41df5  /var/lib/ai-inference-basics/k0s.download" | sha256sum --check -'
ExecStart=/usr/bin/bash -ec 'cmp -s /var/lib/ai-inference-basics/k0s.download /usr/local/bin/k0s || install -m 0755 /var/lib/ai-inference-basics/k0s.download /usr/local/bin/k0s'
ExecStart=/usr/bin/sha256sum --check SHA256SUMS
ExecStart=/usr/bin/install -m 0644 ai-inference-basics.tgz /var/lib/k0s/charts/ai-inference-basics.tgz
ExecStart=/usr/bin/bash -ec 'systemctl cat k0scontroller.service >/dev/null 2>&1 || /usr/local/bin/k0s install controller --single --enable-worker --no-taints --config /etc/k0s/k0s.yaml'
ExecStart=/usr/bin/systemctl enable --now k0scontroller
ExecStart=/usr/bin/bash -ec 'until /usr/local/bin/k0s ctr version >/dev/null 2>&1; do sleep 2; done'
ExecStart=/usr/local/bin/k0s ctr images import --digests bastion.oci.tar
ExecStart=/usr/bin/bash -ec '/usr/local/bin/k0s ctr images tag --force localhost/ai-inference-basics-bastion:dev "$$(cat bastion.ref)"'
ExecStart=/usr/bin/bash -ec 'until /usr/local/bin/k0s kubectl get --raw=/readyz --request-timeout=5s >/dev/null 2>&1; do sleep 2; done'
ExecStart=/usr/bin/install -d -m 0700 -o ${option('qemu_butane_user_name')} -g ${option('qemu_butane_user_name')} /var/home/${option('qemu_butane_user_name')}/.kube
ExecStart=/usr/bin/bash -ec 'umask 077; /usr/local/bin/k0s kubeconfig admin > /var/home/${option('qemu_butane_user_name')}/.kube/config; chown ${option('qemu_butane_user_name')}:${option('qemu_butane_user_name')} /var/home/${option('qemu_butane_user_name')}/.kube/config'
ExecStart=/usr/bin/touch /var/lib/ai-inference-basics/initialized

[Install]
WantedBy=multi-user.target
"""
            }
        ]
    }
}
```

Preparation creates a fixed-name chart archive, a bastion OCI archive, its digest
reference and SHA256SUMS. The final k0s.yaml and private credential manifests are
rendered on the host before Ignition. Their destinations are `/etc/k0s/k0s.yaml`
and `/var/lib/k0s/manifests/ai-inference-basics/credentials.yaml`.

The unit itself downloads the pinned k0s binary from GitHub, verifies its checksum,
installs it under `/usr/local/bin`, starts the controller+worker using that exact
configuration, imports the verified bastion archive and writes the instructor's
kubeconfig. The archives are read from the shared repository. No guest Python
provisioner or intermediate k0s configuration file is needed.

```sh
task up
task ssh
task down
```

`down` destroys the guest disk. config.k and the checkout identity remain managed
by the original runtime. Guest credentials, sessions and telemetry are disposable.
After destruction, down also removes the marked, generated `.local/build/runtime`
directory so the next VM receives fresh credentials. No manual backup/rename or
known_hosts cleanup is required.

The local config is user-owned and ignored by Git. Its tracked supporting inputs
are `infra/k0s/k0s.yaml` and `cluster/`; prepared artifacts under `.local/build` are ignored.
Git does not preserve truly empty directories: cloud-init/terraform placeholders
exist locally but contain no tracked files.
