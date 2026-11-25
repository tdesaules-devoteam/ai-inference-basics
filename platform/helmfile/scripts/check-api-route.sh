#!/usr/bin/env bash
set -euo pipefail
definition=${INFRA_DEFINITION:?Infrastructure definition required}
if [[ $(jq -r .environment "$definition") == devenv ]]; then
  kubectl -n agentgateway rollout status deployment/agentgateway --timeout=180s
  kubectl -n gateway wait certificate/model-api-tls --for=condition=Ready --timeout=180s
elif jq -e '.models | any(.enabled)' "$definition" >/dev/null; then
  kubectl -n gateway wait httproute/model-api \
    '--for=jsonpath={.status.parents[0].conditions[?(@.type=="ResolvedRefs")].status}=True' --timeout=180s
fi
