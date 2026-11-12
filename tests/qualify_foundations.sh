#!/usr/bin/env bash
# Run explicitly against the intended kubectl context. Creates only temporary test resources.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
check="platform-check-$(openssl rand -hex 4)"
cleanup() {
    status=$?
    if [[ $status != 0 ]]; then
        kubectl -n "$check" get pods,gateways,httproutes,aigatewayroutes -o wide || true
        kubectl -n "$check" get events --sort-by=.metadata.creationTimestamp || true
        kubectl -n "$check" logs request || true
        kubectl -n rustfs logs "job/$check" --all-containers=true || true
    fi
    cleanup_failed=0
    kubectl -n rustfs delete job "$check" --ignore-not-found --wait=true --timeout=60s >/dev/null || cleanup_failed=1
    # Let controllers finalize their resources while the namespace is still active.
    kubectl -n "$check" delete aigatewayroute smoke --ignore-not-found --wait=true --timeout=90s >/dev/null || cleanup_failed=1
    kubectl -n "$check" delete aiservicebackend upstream --ignore-not-found --wait=true --timeout=90s >/dev/null || cleanup_failed=1
    kubectl -n "$check" delete gateway smoke --ignore-not-found --wait=true --timeout=120s >/dev/null || cleanup_failed=1
    kubectl -n "$check" delete deployment --all --wait=true --timeout=120s >/dev/null || cleanup_failed=1
    kubectl delete namespace "$check" --ignore-not-found --wait=true --timeout=180s >/dev/null || cleanup_failed=1
    kubectl delete gatewayclass "$check" --ignore-not-found --wait=true --timeout=60s >/dev/null || cleanup_failed=1
    if [[ $status == 0 && $cleanup_failed != 0 ]]; then status=1; fi
    exit "$status"
}
trap cleanup EXIT
kubectl create namespace "$check"
sed "s/__CHECK__/$check/g" "$ROOT/fixtures/foundations.yaml" | kubectl apply -f -
kubectl wait "gatewayclass/$check" --for=condition=Accepted --timeout=120s
kubectl -n "$check" wait gateway/smoke --for=condition=Programmed --timeout=180s
kubectl -n "$check" rollout status deployment/upstream --timeout=180s
service=$(kubectl -n "$check" get service -l gateway.envoyproxy.io/owning-gateway-name=smoke -o jsonpath='{.items[0].metadata.name}')
kubectl -n "$check" run request --restart=Never \
    --image=docker.io/curlimages/curl:8.18.0@sha256:d94d07ba9e7d6de898b6d96c1a072f6f8266c687af78a74f380087a0addf5d17 \
    --command -- sh -ec "curl --fail --silent --show-error --retry 30 --retry-all-errors --retry-delay 2 --max-time 10 \
    -H 'Content-Type: application/json' -d '{\"model\":\"platform-smoke\",\"stream\":false,\"messages\":[{\"role\":\"user\",\"content\":\"hello\"}]}' \
    -D /tmp/headers -o /tmp/response http://$service.$check.svc.cluster.local/v1/chat/completions \
    2>/tmp/curl-errors || { cat /tmp/curl-errors >&2; exit 1; }; \
    grep -qi '^testupstream-id: platform-smoke' /tmp/headers; cat /tmp/response"
kubectl -n "$check" wait pod/request --for=jsonpath='{.status.phase}'=Succeeded --timeout=180s
kubectl -n "$check" logs request | jq -e '.choices | length > 0' >/dev/null
sed "s/__CHECK__/$check/g" "$ROOT/fixtures/s3-access.yaml" | kubectl apply -f -
kubectl -n rustfs wait "job/$check" --for=condition=Complete --timeout=180s
kubectl -n rustfs logs "job/$check"
echo 'Certificate-backed Agent Router webhook, Envoy routing, mock OpenAI response and S3 access qualified.'
