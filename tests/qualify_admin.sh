#!/usr/bin/env bash
# Run with the lab administrator context after the shared workspace is Ready.
set -euo pipefail
for identity in system:serviceaccount:bastion:bastion system:serviceaccount:headlamp:headlamp; do
  kubectl auth can-i '*' '*' --all-namespaces --as="$identity" | grep -Fx yes
done
kubectl -n bastion exec deployment/bastion -c terminal -- kubectl auth can-i '*' '*' --all-namespaces | grep -Fx yes
marker="qualification-$(openssl rand -hex 8)"
trap 'kubectl -n bastion exec deployment/bastion -c terminal -- rm -f "/workspace/$marker" >/dev/null' EXIT
kubectl -n bastion exec deployment/bastion -c terminal -- bash -ec 'echo shared-admin > "$1"' _ "/workspace/$marker"
test "$(kubectl -n bastion exec deployment/bastion -c editor -- cat "/workspace/$marker")" = shared-admin
test "$(kubectl -n bastion get deployment -o json | jq '.items | length')" = 1
echo 'Shared workspace and full bastion/Headlamp administrator rights passed.'
