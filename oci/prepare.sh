#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
# Logging helpers belong to the pinned upstream runtime.
# shellcheck source=/dev/null
source .devenv/scripts/utils.sh
[[ $(uname -sm) == 'Linux x86_64' ]] || { _error_handler 'This lab is currently prepared for Linux x86_64'; exit 1; }
for binary in podman skopeo curl tar sha256sum python3; do command -v "$binary" >/dev/null; done
mkdir -p .local/build
_log title 'Build the administration bastion'
podman build --format docker -f oci/bastion/Containerfile -t localhost/ai-inference-basics-bastion:dev .
podman run --rm --entrypoint bash localhost/ai-inference-basics-bastion:dev -c \
  'zellij --version && kubectl version --client && k9s version && helm version --short && task --version'
podman save --format oci-archive -o .local/build/bastion.oci.tar localhost/ai-inference-basics-bastion:dev
skopeo inspect --raw oci-archive:.local/build/bastion.oci.tar > .local/build/bastion.manifest.json
_log title 'Package the locked local umbrella chart'
(cd charts/ai-inference-basics && sha256sum -c dependencies.sha256)
bash oci/helm.sh package charts/ai-inference-basics --destination .local/build
python3 - <<'PY'
import hashlib,json,pathlib,re
root=pathlib.Path.cwd(); build=root/'.local/build'
version=re.search(r'^version:\s*(\S+)',(root/'charts/ai-inference-basics/Chart.yaml').read_text(),re.M).group(1)
chart=build/f'ai-inference-basics-{version}.tgz'
digest='sha256:'+hashlib.sha256((build/'bastion.manifest.json').read_bytes()).hexdigest()
data={'version':version,'chart_file':chart.name,'chart_sha256':hashlib.sha256(chart.read_bytes()).hexdigest(),
      'image':'localhost/ai-inference-basics-bastion@'+digest,
      'image_archive':'bastion.oci.tar','image_archive_sha256':hashlib.file_digest((build/'bastion.oci.tar').open('rb'),'sha256').hexdigest()}
(build/'artifacts.json').write_text(json.dumps(data,indent=2)+'\n')
PY
_log success 'Local artifacts ready; VM provisioning remains owned by devenv'
