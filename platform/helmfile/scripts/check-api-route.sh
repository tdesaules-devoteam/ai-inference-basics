#!/usr/bin/env bash
set -euo pipefail
definition=${INFRA_DEFINITION:?Infrastructure definition required}
if [[ $(jq -r .environment "$definition") == devenv ]]; then
  kubectl -n agentgateway rollout status deployment/agentgateway --timeout=180s
  # A Ready proxy can still be serving its previous configuration after a reload.
  # Check the exact new contract from the API listener, without using any credential.
  host=$(jq -r .network.hostname "$definition")
  port=$(jq -r .network.apiNodePort "$definition")
  until curl --noproxy '*' --fail --silent --max-time 5 "http://$host:$port/openapi.json" |
    jq -e '.openapi == "3.1.0" and .paths["/v1/models"].get != null and .paths["/openapi.json"].get.security == []' >/dev/null
  do
    (( SECONDS < 180 )) || { echo 'Public model API contract did not converge.' >&2; exit 1; }
    sleep 2
  done
elif jq -e '.models | any(.enabled)' "$definition" >/dev/null; then
  kubectl -n gateway wait httproute/model-api \
    '--for=jsonpath={.status.parents[0].conditions[?(@.type=="ResolvedRefs")].status}=True' --timeout=180s
fi
