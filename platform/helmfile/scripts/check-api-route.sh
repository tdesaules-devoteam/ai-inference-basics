#!/usr/bin/env bash
# Skip the model API readiness check when no model releases are selected.
set -euo pipefail
if jq -e '.models | any(.enabled)' "${INFRA_DEFINITION:?Infrastructure definition required}" >/dev/null; then
  kubectl -n gateway wait httproute/model-api \
    '--for=jsonpath={.status.parents[0].conditions[?(@.type=="ResolvedRefs")].status}=True' --timeout=180s
fi
