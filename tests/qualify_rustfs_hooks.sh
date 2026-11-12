#!/usr/bin/env bash
# Explicit integration test: install/upgrade upstream RustFS in a disposable namespace.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
values=$(realpath "${1:-$ROOT/../platform/helm/values/rustfs.yaml}")
namespace="rustfs-hook-check-$(openssl rand -hex 4)"
test -z "$(kubectl get namespace "$namespace" --ignore-not-found -o name)"
temporary=$(mktemp -d)
cleanup() {
    status=$?
    if [[ $status != 0 ]]; then
        kubectl -n "$namespace" get pods,jobs,pvc || true
        kubectl -n "$namespace" logs job/rustfs-credentials || true
    fi
    if [[ -f "$temporary/helmfile.yaml" ]]; then
        echo '    installed: false' >> "$temporary/helmfile.yaml"
        helmfile -f "$temporary/helmfile.yaml" sync || status=1
    fi
    kubectl delete namespace "$namespace" --ignore-not-found --wait=true --timeout=180s || status=1
    rm -rf -- "$temporary"
    exit "$status"
}
trap cleanup EXIT
cat > "$temporary/helmfile.yaml" <<YAML
repositories:
  - name: rustfs
    url: https://charts.rustfs.com
helmDefaults:
  createNamespace: true
  wait: true
  waitForJobs: true
  timeout: 600
releases:
  - name: rustfs-hook-check
    namespace: $namespace
    chart: rustfs/rustfs
    version: "1.0.5"
    values:
      - "$values"
      - storageclass:
          dataStorageSize: 1Gi
YAML
helmfile -f "$temporary/helmfile.yaml" sync
kubectl -n "$namespace" logs job/rustfs-credentials | grep -Fx 'RustFS credentials created.'
kubectl -n "$namespace" logs job/rustfs-buckets
before=$(kubectl -n "$namespace" get secret rustfs-root -o json | jq -c .data | sha256sum)
account="system:serviceaccount:$namespace:rustfs-credentials"
kubectl auth can-i get secret/rustfs-root -n "$namespace" --as="$account" | grep -Fx yes
kubectl auth can-i create secrets -n "$namespace" --as="$account" | grep -Fx yes
for verb in list update patch delete; do
    if kubectl auth can-i "$verb" secrets -n "$namespace" --as="$account" >/dev/null; then exit 1; fi
done
if kubectl auth can-i get secret/another-secret -n "$namespace" --as="$account" >/dev/null; then exit 1; fi
if kubectl auth can-i create secrets -n rustfs --as="$account" >/dev/null; then exit 1; fi
helmfile -f "$temporary/helmfile.yaml" sync
kubectl -n "$namespace" logs job/rustfs-credentials | grep -Fx 'Existing RustFS credentials preserved.'
test "$before" = "$(kubectl -n "$namespace" get secret rustfs-root -o json | jq -c .data | sha256sum)"
echo 'Fresh namespace, pre-install credentials, post-install buckets, scoped RBAC and upgrade preservation passed.'
