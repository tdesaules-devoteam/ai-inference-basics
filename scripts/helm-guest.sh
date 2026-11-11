#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
bash scripts/helm.sh version --short >&2
printf -v args '%q ' "$@"
bash scripts/guest.sh "cd ~/workspace && sudo env KUBECONFIG=/var/lib/k0s/pki/admin.conf .local/bin/helm $args"
