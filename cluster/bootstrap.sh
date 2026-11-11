#!/usr/bin/env bash
set -euo pipefail
workspace=${1:?Shared repository path is required}
[[ $(id -u) == 0 ]] || { echo 'Bootstrap must run as root in the guest.' >&2; exit 1; }
[[ -f /var/lib/ai-inference-basics/ready ]] && exit 0
# devenv applies layered packages and handles the staged OS reboot itself.
if rpm-ostree status --json | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)["deployments"][0].get("booted") is False else 1)'; then
  echo 'Waiting for the staged reboot managed by devenv; bootstrap resumes next boot.'
  exit 0
fi
version='v1.37.2+k0s.1'
sha='4770cf89ff45e43292819f6e3a02a25a453bc750c777f6f7ad2de335f3f41df5'
if [[ ! -x /usr/local/bin/k0s ]]; then
  temporary=$(mktemp)
  trap 'rm -f "$temporary"' EXIT
  curl -fL --retry 3 "https://github.com/k0sproject/k0s/releases/download/$version/k0s-$version-amd64" -o "$temporary"
  echo "$sha  $temporary" | sha256sum -c -
  install -m 755 "$temporary" /usr/local/bin/k0s
fi
[[ $(/usr/local/bin/k0s version) == "$version" ]] || { echo 'Unexpected k0s version; recreate the lab.' >&2; exit 1; }
exec python3 /usr/local/lib/ai-inference-basics/provision.py "$workspace"
