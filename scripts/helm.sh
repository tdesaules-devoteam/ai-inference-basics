#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
version=v4.3.1
sha=0403a88ae20913d11b10a2467b50087721fea7581736da6b9d3992f5357fe54b
if [[ ! -x .local/bin/helm ]]; then
  [[ $(uname -sm) == 'Linux x86_64' ]] || { echo 'Pinned Helm bootstrap currently supports Linux x86_64.' >&2; exit 1; }
  mkdir -p .local/bin
  curl -fL --retry 3 "https://get.helm.sh/helm-$version-linux-amd64.tar.gz" -o .local/helm-bootstrap.tar.gz
  echo "$sha  .local/helm-bootstrap.tar.gz" | sha256sum -c - >&2
  tar -xzf .local/helm-bootstrap.tar.gz -C .local
  install .local/linux-amd64/helm .local/bin/helm
fi
exec .local/bin/helm "$@"
