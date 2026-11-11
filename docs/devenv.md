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
