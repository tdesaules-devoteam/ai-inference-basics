#!/usr/bin/env bash
# Convergence check for a single Standard-mode KServe model, including stopped state.
set -euo pipefail
name=${1:?model name required}
scripts=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
if [[ $(kubectl -n "$name" get inferenceservice "$name" -o jsonpath='{.metadata.annotations.serving\.kserve\.io/stop}') == true ]]; then
  kubectl -n "$name" wait "inferenceservice/$name" --for=jsonpath='{.status.conditions[?(@.type=="Stopped")].status}'=True --timeout=300s
  until [[ $(kubectl -n "$name" get pods -l "serving.kserve.io/inferenceservice=$name" -o json | jq '.items | length') == 0 ]]; do sleep 2; done
  echo "$name is stopped with zero inference Pods."
  exit 0
fi
until
  desired=$(kubectl -n "$name" get inferenceservice "$name" -o json)
  runtime=$(kubectl -n "$name" get servingruntime "$name" -o json)
  kubectl -n "$name" get deployment "$name-predictor" -o json |
    python3 "$scripts/model-state.py" "$desired" "$runtime"
do sleep 3; done
# The enclosing Helmfile timeout bounds this wait. A Deployment's default 600s
# progress deadline can expire during first image pulls/S3 initialization even
# though startup is still progressing. Check actual generation and replica counts.
until kubectl -n "$name" get deployment "$name-predictor" -o json |
  python3 "$scripts/model-state.py" --rollout-ready; do sleep 3; done
kubectl -n "$name" wait "inferenceservice/$name" --for=jsonpath='{.status.conditions[?(@.type=="Ready")].status}'=True --timeout=300s
kubectl -n "$name" wait "inferenceservice/$name" --for=jsonpath='{.status.modelStatus.transitionStatus}'=UpToDate --timeout=300s
