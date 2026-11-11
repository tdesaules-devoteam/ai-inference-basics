#!/usr/bin/env bash
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run on the GPU host as root.' >&2; exit 1; }
[[ $(/usr/local/bin/k0s version) == 'v1.37.2+k0s.1' ]] || { echo 'Unqualified k0s version.' >&2; exit 1; }
command -v nvidia-smi >/dev/null
command -v nvidia-ctk >/dev/null
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
nvidia-ctk --version | grep -F '1.20.1' >/dev/null || {
  echo 'Install and qualify NVIDIA Container Toolkit 1.20.1 before configuring this runtime.' >&2
  exit 1
}
[[ -S /run/k0s/containerd.sock ]] || { echo 'k0s embedded containerd socket is missing.' >&2; exit 1; }
mkdir -p /etc/k0s/containerd.d
target=/etc/k0s/containerd.d/nvidia.toml
if [[ -e $target ]]; then
  echo 'Existing NVIDIA drop-in retained. Inspect it before changing runtime settings.'
else
  nvidia-ctk runtime configure --runtime=containerd --config="$target"
  chmod 600 "$target"
fi
echo 'Drop-in prepared for k0s dynamic runtime configuration. Validate RuntimeClass and a CUDA Pod before HAMi.'
