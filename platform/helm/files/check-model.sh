#!/usr/bin/env bash
# Convergence check for a single Standard-mode KServe model, including stopped state.
set -euo pipefail
name=${1:?model name required}
if [[ $(kubectl -n "$name" get inferenceservice "$name" -o jsonpath='{.metadata.annotations.serving\.kserve\.io/stop}') == true ]]; then
  kubectl -n "$name" wait "inferenceservice/$name" --for=jsonpath='{.status.conditions[?(@.type=="Stopped")].status}'=True --timeout=300s
  until [[ $(kubectl -n "$name" get pods -l "serving.kserve.io/inferenceservice=$name" -o json | jq '.items | length') == 0 ]]; do sleep 2; done
  echo "$name is stopped with zero inference Pods."
  exit 0
fi
until
  desired=$(kubectl -n "$name" get inferenceservice "$name" -o json)
  runtime=$(kubectl -n "$name" get servingruntime "$name" -o json)
  kubectl -n "$name" get deployment "$name-predictor" -o json | jq -e \
    --arg uri "$(echo "$desired" | jq -r .spec.predictor.model.storageUri)" \
    --arg image "$(echo "$runtime" | jq -r '.spec.containers[0].image')" \
    --argjson args "$(echo "$runtime" | jq -c '.spec.containers[0].args')" \
    --argjson resources "$(echo "$desired" | jq -c '.spec.predictor.model.resources')" \
    '.spec.template.metadata.annotations["internal.serving.kserve.io/storage-initializer-sourceuri"] == $uri and
     any(.spec.template.spec.containers[]; .name == "kserve-container" and .image == $image and .args == $args and .resources == $resources)' >/dev/null
do sleep 3; done
kubectl -n "$name" rollout status "deployment/$name-predictor" --timeout=900s
kubectl -n "$name" wait "inferenceservice/$name" --for=jsonpath='{.status.conditions[?(@.type=="Ready")].status}'=True --timeout=300s
kubectl -n "$name" wait "inferenceservice/$name" --for=jsonpath='{.status.modelStatus.transitionStatus}'=UpToDate --timeout=300s
