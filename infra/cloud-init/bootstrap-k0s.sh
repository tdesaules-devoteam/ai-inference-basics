#!/usr/bin/env bash
set -euo pipefail
version='v1.37.2+k0s.1'
sha='4770cf89ff45e43292819f6e3a02a25a453bc750c777f6f7ad2de335f3f41df5'
if [[ ! -x /usr/local/bin/k0s ]]; then
  temporary=$(mktemp)
  trap 'rm -f "$temporary"' EXIT
  curl -fL --retry 3 "https://github.com/k0sproject/k0s/releases/download/$version/k0s-$version-amd64" -o "$temporary"
  echo "$sha  $temporary" | sha256sum -c -
  install -m 755 "$temporary" /usr/local/bin/k0s
fi
[[ $(/usr/local/bin/k0s version) == "$version" ]] || { echo 'Unexpected installed k0s version.' >&2; exit 1; }
if ! systemctl cat k0scontroller >/dev/null 2>&1; then
  /usr/local/bin/k0s install controller --single --enable-worker --no-taints --config /etc/k0s/k0s.yaml
fi
systemctl enable --now k0scontroller
