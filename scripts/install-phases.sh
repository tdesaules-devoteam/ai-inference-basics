#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
phase=${1:-foundation}
[[ ${PROFILE:-local-cpu} == local-cpu ]] || { echo 'Cloud transport is not configured.' >&2; exit 1; }
if [[ $phase == ai-controllers || $phase == models ]]; then
  bash scripts/wait-prerequisites.sh
fi
(cd charts/ai-inference-basics && sha256sum -c dependencies.sha256)
args=(upgrade --install --reset-then-reuse-values ai-inference-basics charts/ai-inference-basics --namespace ai-inference-basics --create-namespace
  -f profiles/local-cpu.yaml --set envoyGateway.enabled=true --timeout 5m)
if [[ -f .local/workspaces.yaml ]]; then args+=(-f .local/workspaces.yaml); fi
case "$phase" in
  foundation) ;;
  access|certificates|ai-crds|ai-controllers|models)
    bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics get secret ai-inference-basics-tls ai-inference-basics-ca ai-inference-basics-dex ai-inference-basics-oauth >/dev/null'
    args+=(--set gateway.enabled=true --set dex.enabled=true --set headlamp.enabled=true --set access.enabled=true)
    if [[ $phase != access ]]; then args+=(--set cert-manager.enabled=true); fi
    if [[ $phase == ai-crds || $phase == ai-controllers || $phase == models ]]; then
      args+=(--set kserveCRDs.enabled=true --set llmCRDs.enabled=true --set aiCRDs.enabled=true)
    fi
    if [[ $phase == ai-controllers || $phase == models ]]; then
      args+=(--set kserveController.enabled=true --set llmController.enabled=true --set agent-router.enabled=true)
    fi
    if [[ $phase == models ]]; then args+=(-f profiles/phases/ai-routing.yaml); fi
    ;;
  *) echo "Unsupported phase: $phase" >&2; exit 1 ;;
esac
bash scripts/helm-guest.sh "${args[@]}"
bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/envoy-gateway --timeout=180s'
if [[ $phase == certificates ]]; then
  bash scripts/wait-prerequisites.sh
fi
if [[ $phase == ai-crds ]]; then
  bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl wait crd/inferenceservices.serving.kserve.io crd/llminferenceservices.serving.kserve.io crd/aigatewayroutes.aigateway.envoyproxy.io --for=condition=Established --timeout=90s'
fi
if [[ $phase == ai-controllers ]]; then
  bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/kserve-controller-manager --timeout=180s && sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/llmisvc-controller-manager --timeout=180s && sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/ai-gateway-controller --timeout=180s'
fi
if [[ $phase == models ]]; then
  bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics wait llmisvc/ai-inference-basics-chat isvc/ai-inference-basics-embeddings isvc/ai-inference-basics-rerank --for=condition=Ready --timeout=900s'
fi
if [[ $phase != foundation ]]; then
  bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/dex --timeout=180s'
  bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/oauth2-proxy --timeout=180s'
  if [[ -f .local/workspaces.yaml ]]; then
    bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/workspace-a --timeout=180s && sudo /usr/local/bin/k0s kubectl -n ai-inference-basics rollout status deployment/workspace-b --timeout=180s'
    .local/venv/bin/python scripts/workspace-credentials.py
  fi
fi
