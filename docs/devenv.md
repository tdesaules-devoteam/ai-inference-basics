# Local Fedora CoreOS VM

Runtime: `.devenv` Git submodule from <https://github.com/tdesaules/qemu-dev-env>.
The project uses its QEMU/KCL/Butane/Ignition workflow, not an alternate VM manager.

Initial sizing: 12 vCPUs, 32 GiB RAM, 64 GiB virtual disk, host CPU flags, no GPU.
Fedora CoreOS 45.20261030.2.1 is in testing, not stable; pin both architecture hashes.

Prerequisites: Linux x86_64 KVM, QEMU/qemu-img, Task, KCL, Butane, jq, curl, gpgv,
SHA-256 utility, xz, SSH key, sudo, NetworkManager br-qemu and bridge-helper access.
Host bridge/firewall configuration belongs to the existing host configuration.

Initialize with `git submodule update --init --recursive`. Create local config from
`.devenv/exemple.config.k` only if absent, then adapt it; never overwrite an existing
config or copy the reference project's identity. `.devenv/config.k` stays ignored.

The runtime stores VM data in `~/.qemu/<uuid>/`; `.devenv/.uuid` is stable across
stop/start. Guest `~/workspace` must mount the repository root, not `.devenv`.
Guest writes in that share modify host source. Guest-only data lives on the VM disk.

Use `stop` for routine shutdown and `down` only for disposal. Ignition is first-boot
configuration; editing config does not reprovision a running guest. Keep submodule
updates explicit and record the new gitlink after reviewing upstream changes.

Runtime adaptation must preserve image signature/checksum verification, align both
KCL render argument sets, and avoid automatic host credential imports. No Cockpit,
Beszel or host application service is required by this lab.

## Reproduce this checkout

```sh
git submodule update --init --recursive
python3 -m venv .local/venv
.local/venv/bin/pip install -r requirements-dev.txt
.local/venv/bin/playwright install chromium
cp -n .devenv/exemple.config.k .devenv/config.k
```

For a **new** config, replace the demo content with the following. Preserve and
merge any existing user configuration instead of overwriting it.

```kcl
import .schema as schema
import .templates as templates

_user = option("qemu_butane_user_name")
config = schema.Qemu {
    os.version = "45.20261030.2.1"
    os.streams = "testing"
    checksum.x86_64 = "420f428010ba880200e5b83c116cdc4a804652efc4bbcd4846c8d3e860928f88"
    checksum.aarch64 = "d0e1786961d08f801e1af24eb87616cd7aabbda372d30b5d9e8dc6e19537011b"
    hardware.cpu = 12
    hardware.memory = {size = 32, unit = "G"}
    hardware.disk = {size = 64, unit = "G"}
    butane = schema.Butane {
        default_pkgs = []
        default_mise_tools = {}
        default_copies = []
        units = [
            {name = "install-system-pkgs.service", contents = "[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/bin/true\n[Install]\nWantedBy=multi-user.target\n"}
            {name = "run-topgrade.service", contents = "[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/usr/bin/true\n[Install]\nWantedBy=multi-user.target\n"}
            {name = "var-home-${_user}-workspace.mount", enabled = False, contents = templates.var_home_user_workspace_mount(_user)}
            {name = "var-home-${_user}-workspace.automount", contents = templates.var_home_user_workspace_automount(_user)}
            {name = "var-home-${_user}-.qemu.mount", enabled = False, contents = templates.var_home_user_qemu_mount(_user)}
            {name = "var-home-${_user}-.qemu.automount", contents = templates.var_home_user_qemu_automount(_user)}
        ]
    }
}
```

The two compatibility oneshot units are deliberately no-ops: no RPM layering or
floating topgrade updates are needed for native k0s. Project bootstrap installs
checksum-pinned k0s separately, and administration tools live in Kubernetes Pods.
The runtime's other disposable-system defaults (including permissive SELinux and
passwordless instructor sudo) remain local-development settings, not production
hardening. Host OpenCode credentials, demo users and Beszel are not provisioned.

```sh
task doctor
task up PROFILE=local-cpu
task devenv:status
task devenv:ssh
task down                  # retain disk/config/identity
task infra:destroy         # discard guest disk; preserves local identity/config
```

The root includes a small `devenv:` adapter. It serializes runtime calls, applies
the reviewed `infra/devenv/patches/runtime.patch`, runs the original
`taskfile.qemu.yaml`, and reverses the patch afterwards. The gitlink remains the
available upstream revision and clean between calls. This distributes the renderer
fixes reproducibly without an unpublished submodule commit or a duplicate VM engine.
Use the root Task commands, not the unadapted runtime directly.

The patch aligns renderer arguments and explicit project-root sharing, avoids KCL
external-file probes and host-auth imports, removes the upstream demo login, tracks
template changes and checks the selected FCOS stream. Identity is created before
rendering. Generated Butane/Ignition inherit a restrictive umask.

Update the submodule explicitly only after review; rebase/revalidate the patch
against the selected revision, record the gitlink and validate another VM boot.
FCOS updates similarly require fresh stream checksums and an intentional rebuild.
No arbitrary-path, ARM64 or macOS boot qualification is claimed.
