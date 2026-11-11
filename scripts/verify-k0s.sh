#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl wait node --all --for=condition=Ready --timeout=180s && sudo /usr/local/bin/k0s kubectl -n kube-system rollout status deployment/coredns --timeout=120s && test -f ~/workspace/charts/ai-inference-basics/Chart.yaml && test "$(nproc)" = 12'
bash scripts/guest.sh 'sudo /usr/local/bin/k0s kubectl get pods -A -o json' | python3 -c '
import json,sys
pods=json.load(sys.stdin)["items"]
bad=[c["image"] for p in pods for c in p["spec"].get("initContainers",[])+p["spec"]["containers"] if "@sha256:" not in c["image"]]
assert not bad, bad
print("All active Pod and init-container images are digest-pinned.")'
