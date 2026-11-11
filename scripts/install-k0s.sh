#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
version='v1.37.2+k0s.1'
sha='4770cf89ff45e43292819f6e3a02a25a453bc750c777f6f7ad2de335f3f41df5'
mkdir -p .local/bin
if ! echo "$sha  .local/bin/k0s" | sha256sum -c - >/dev/null 2>&1; then
  curl -fL --retry 3 "https://github.com/k0sproject/k0s/releases/download/$version/k0s-$version-amd64" -o .local/bin/k0s
fi
echo "$sha  .local/bin/k0s" | sha256sum -c -
bash scripts/guest.sh 'bash -s' <<'GUEST'
set -euo pipefail
cd ~/workspace
if [[ -x /usr/local/bin/k0s ]]; then
  [[ $(/usr/local/bin/k0s version) == 'v1.37.2+k0s.1' ]] || { echo 'Existing k0s version differs; explicit upgrade required.' >&2; exit 1; }
else
  sudo install -m 755 .local/bin/k0s /usr/local/bin/k0s
fi
sudo mkdir -p /etc/k0s
if [[ -f /etc/k0s/k0s.yaml ]]; then
  sudo cmp infra/k0s/config.yaml /etc/k0s/k0s.yaml || { echo 'Existing k0s configuration differs; inspect before replacing.' >&2; exit 1; }
else
  sudo install -m 600 infra/k0s/config.yaml /etc/k0s/k0s.yaml
fi
if ! systemctl cat k0scontroller.service >/dev/null 2>&1; then
  sudo /usr/local/bin/k0s install controller --single --enable-worker --no-taints --config /etc/k0s/k0s.yaml
fi
sudo systemctl start k0scontroller
timeout 180 bash -c 'until sudo /usr/local/bin/k0s kubectl get nodes -o name 2>/dev/null | grep -q node/; do sleep 3; done'
sudo /usr/local/bin/k0s kubectl wait --for=condition=Ready node --all --timeout=240s
sudo /usr/local/bin/k0s kubectl -n kube-system rollout status deployment/coredns --timeout=180s
GUEST
