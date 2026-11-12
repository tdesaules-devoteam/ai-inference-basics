#!/usr/bin/env bash
# Fetch verified tools and chart sources; does not access Kubernetes.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STATE=${PLATFORM_STATE_DIR:-/var/lib/ai-inference-basics/platform}
[[ $(uname -sm) == 'Linux x86_64' ]] || { echo 'Linux AMD64 is required.' >&2; exit 1; }
mkdir -p "$STATE/artifacts" "$STATE/bin"
temporary=$(mktemp -d)
trap 'rm -rf -- "$temporary"' EXIT
while read -r checksum filename url; do
    [[ -z "$checksum" || "$checksum" == \#* ]] && continue
    target="$STATE/artifacts/$filename"
    if ! echo "$checksum  $target" | sha256sum --check --status 2>/dev/null; then
        curl --fail --location --silent --show-error --connect-timeout 20 --max-time 600 --retry 3 \
            --output "$temporary/$filename" "$url"
        echo "$checksum  $temporary/$filename" | sha256sum --check --status
        install -m 0644 "$temporary/$filename" "$target"
    fi
done < "$ROOT/artifacts.lock"
tar -xzf "$STATE/artifacts/helm-v4.3.1-linux-amd64.tar.gz" -C "$temporary" linux-amd64/helm
tar -xzf "$STATE/artifacts/helmfile_1.8.3_linux_amd64.tar.gz" -C "$temporary" helmfile
install -m 0755 "$temporary/linux-amd64/helm" "$STATE/bin/helm"
install -m 0755 "$temporary/helmfile" "$STATE/bin/helmfile"
# Helm consumes the upstream chart directory from this verified source archive.
# Re-extract into a clean tree so stale files cannot survive a retry.
tar -xzf "$STATE/artifacts/local-path-provisioner-v0.0.37.tar.gz" -C "$temporary" \
    local-path-provisioner-0.0.37/deploy/chart/local-path-provisioner
rm -rf -- "$STATE/artifacts/local-path-provisioner-0.0.37"
mv "$temporary/local-path-provisioner-0.0.37" "$STATE/artifacts/"
"$STATE/bin/helm" version --short
"$STATE/bin/helmfile" version
