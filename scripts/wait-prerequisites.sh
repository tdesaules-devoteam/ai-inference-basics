#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/cert-manager-webhook --timeout=180s && sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/cert-manager-cainjector --timeout=180s'
# Deployment readiness does not prove that cainjector has populated the API
# server's admission CA bundle, especially when enabling a subchart on upgrade.
for ((attempt = 1; attempt <= 60; attempt++)); do
  if printf '%s\n' '{"apiVersion":"cert-manager.io/v1","kind":"Issuer","metadata":{"name":"ai-inference-basics-admission-probe","namespace":"ai-inference-basics"},"spec":{"selfSigned":{}}}' |
      bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl apply --dry-run=server --request-timeout=5s -f -' >/dev/null 2>&1; then
    echo 'cert-manager admission TLS and CA injection are ready.'
    exit 0
  fi
  sleep 2
done
echo 'cert-manager admission is not ready; inspect webhook endpoints and CA injection.' >&2
exit 1
