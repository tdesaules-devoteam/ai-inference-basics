#!/usr/bin/env bash
# Cluster bootstrap entrypoint for systemd (devenv now, cloud-init later).
set -euo pipefail
umask 077
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export PLATFORM_STATE_DIR=${PLATFORM_STATE_DIR:-/var/lib/ai-inference-basics/platform}
install -d -m 0700 "$PLATFORM_STATE_DIR"
exec 9>"$PLATFORM_STATE_DIR/install.lock"
flock -n 9 || { echo 'Another platform installation is running.' >&2; exit 1; }
bash "$ROOT/prepare.sh"
export PATH="$PLATFORM_STATE_DIR/bin:$PATH"
export PLATFORM_ARTIFACTS="$PLATFORM_STATE_DIR/artifacts"
export HELM_CACHE_HOME="$PLATFORM_STATE_DIR/helm/cache"
export HELM_CONFIG_HOME="$PLATFORM_STATE_DIR/helm/config"
export HELM_DATA_HOME="$PLATFORM_STATE_DIR/helm/data"
temporary=$(mktemp -d)
trap 'rm -rf -- "$temporary"' EXIT
unset KUBECONFIG
timeout 300 bash -c 'until /usr/local/bin/k0s kubectl get --raw=/readyz --request-timeout=5s >/dev/null 2>&1 && test -n "$(/usr/local/bin/k0s kubectl get nodes -o name --request-timeout=5s 2>/dev/null)"; do sleep 3; done'
/usr/local/bin/k0s kubeconfig admin > "$temporary/kubeconfig"
export KUBECONFIG="$temporary/kubeconfig"
/usr/local/bin/k0s kubectl wait node --all --for=condition=Ready --timeout=180s
/usr/local/bin/k0s kubectl create namespace rustfs --dry-run=client -o yaml | /usr/local/bin/k0s kubectl apply -f -
# Generate once; the Secret, not a host profile or Helm values, owns these credentials.
existing=$(/usr/local/bin/k0s kubectl -n rustfs get secret rustfs-root --ignore-not-found -o name)
if [[ -z "$existing" ]]; then
    printf 'RUSTFS_ACCESS_KEY=%s\nRUSTFS_SECRET_KEY=%s\n' \
        "$(openssl rand -hex 12)" "$(openssl rand -hex 32)" > "$temporary/rustfs.env"
    /usr/local/bin/k0s kubectl -n rustfs create secret generic rustfs-root --from-env-file="$temporary/rustfs.env"
fi
/usr/local/bin/k0s kubectl -n rustfs get secret rustfs-root -o json | \
    jq -e '.data.RUSTFS_ACCESS_KEY != null and .data.RUSTFS_SECRET_KEY != null' >/dev/null
# sync does not require helm-diff and respects needs and readiness between releases.
helmfile --file "$ROOT/helmfile.yaml.gotmpl" sync
/usr/local/bin/k0s kubectl -n rustfs wait job/storage-bootstrap --for=condition=Complete --timeout=300s
/usr/local/bin/k0s kubectl -n rustfs get pvc rustfs-data
echo 'Storage platform ready; S3 bucket initialization and read/write verification passed.'
