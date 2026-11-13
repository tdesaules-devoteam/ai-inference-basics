#!/usr/bin/env bash
# Build and qualify the local bastion artifact. Does not operate a VM or publish.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
[[ $(uname -sm) == 'Linux x86_64' ]] || { echo 'Linux AMD64 build required.' >&2; exit 1; }
for binary in podman skopeo sha256sum; do command -v "$binary" >/dev/null; done
mkdir -p dist
image=localhost/ai-inference-basics-bastion:dev
podman build --format docker -f oci/bastion/Containerfile -t "$image" .
podman run --rm --entrypoint bash "$image" -ec \
  'kubectl version --client; k9s version; ttyd --version; zellij --version; starship --version; hx --version; code-server --version; curl --version; jq --version; rc --version; vllm bench serve --help >/dev/null; python3 -c "import bcrypt,boto3,yaml"'
podman save --format oci-archive -o dist/bastion.oci.tar "$image"
digest=$(skopeo inspect --raw oci-archive:dist/bastion.oci.tar | sha256sum | cut -d' ' -f1)
echo "localhost/ai-inference-basics-bastion@sha256:$digest" > dist/bastion.ref
(cd dist && sha256sum bastion.oci.tar bastion.ref > SHA256SUMS)
echo 'Qualified local artifact. Import explicitly into k0s, then align toolsImage in platform/helm/values/lab.yaml.gotmpl with:'
cat dist/bastion.ref
