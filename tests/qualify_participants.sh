#!/usr/bin/env bash
# Explicitly run against the lab context after both participant deployments are Ready.
set -euo pipefail
marker="qualification-$(openssl rand -hex 8)"
cleanup() {
  for user in a b; do
    kubectl -n bastion exec "deployment/bastion-$user" -c terminal -- rm -f "/workspace/$marker" >/dev/null || true
  done
}
trap cleanup EXIT
for user in a b; do
  other=a
  [[ $user == a ]] && other=b
  account="system:serviceaccount:bastion:bastion-$user"
  kubectl auth can-i create deployments -n "lab-$user" --as="$account" | grep -Fx yes
  if kubectl auth can-i create deployments -n "lab-$other" --as="$account" >/dev/null; then exit 1; fi
  if kubectl auth can-i create pods/exec -n bastion --as="$account" >/dev/null; then exit 1; fi
  if kubectl auth can-i get secrets -n gateway --as="$account" >/dev/null; then exit 1; fi
  kubectl -n bastion exec "deployment/bastion-$user" -c terminal -- kubectl -n "lab-$user" get pods
  kubectl -n bastion exec "deployment/bastion-$other" -c terminal -- curl -fsS -o /dev/null http://127.0.0.1:8080/healthz
  kubectl -n bastion exec "deployment/bastion-$user" -c terminal -- bash -ec 'echo "$1" > "$2"' _ "$user" "/workspace/$marker"
  test "$(kubectl -n bastion exec "deployment/bastion-$user" -c editor -- cat "/workspace/$marker")" = "$user"
  kubectl -n bastion exec "deployment/bastion-$other" -c terminal -- test ! -e "/workspace/$marker"
  kubectl -n bastion exec "deployment/bastion-$user" -c terminal -- rm "/workspace/$marker"
  for target in "http://bastion-$other.bastion.svc.cluster.local:8080/healthz" \
                'http://ai-inference-basics-chat-predictor.inference-service.svc.cluster.local/health'; do
    kubectl -n bastion exec "deployment/bastion-$user" -c terminal -- bash -c \
      'curl -s -o /dev/null --connect-timeout 2 --max-time 3 "$1"; status=$?; [[ $status == 7 || $status == 28 ]]' _ "$target"
  done
done
echo 'Participant RBAC, per-user PVCs and direct-access network isolation passed.'
