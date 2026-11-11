#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
[[ $(uname -sm) == 'Linux x86_64' ]] || { echo 'This local integration is qualified for Linux x86_64 only.' >&2; exit 1; }
for tool in task kcl butane qemu-system-x86_64 qemu-img jq curl gpgv sha256sum unxz ssh python3 flock; do
  command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
[[ -r /dev/kvm && -w /dev/kvm ]] || { echo 'KVM is unavailable to the current user.' >&2; exit 1; }
[[ $(nproc) -ge 12 ]] || { echo 'The local configuration requires 12 virtual CPUs.' >&2; exit 1; }
nmcli connection show br-qemu >/dev/null
grep -Eq '^allow[[:space:]]+br-qemu$' /etc/qemu/bridge.conf
sudo -n true
[[ -s .devenv/config.k ]] || { echo 'Create local config.k following docs/devenv.md.' >&2; exit 1; }
[[ -x .local/venv/bin/python ]] || { echo 'Create .local/venv and install requirements-dev.txt.' >&2; exit 1; }
bash scripts/devenv.sh check
