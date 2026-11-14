#!/usr/bin/env bash
# Build, qualify and export local OCI artifacts; never operate a VM or publish.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
[[ $(uname -sm) == 'Linux x86_64' ]] || { echo 'Linux AMD64 build required.' >&2; exit 1; }
for binary in podman skopeo sha256sum; do command -v "$binary" >/dev/null; done
mkdir -p dist
selection=${1:-all}
case "$selection" in
  all) images=(bastion provision lfm3-omni-2b-transformers) ;;
  bastion|provision|lfm3-omni-2b-transformers) images=("$selection") ;;
  *) echo 'Expected all, bastion, provision or lfm3-omni-2b-transformers.' >&2; exit 2 ;;
esac
for name in "${images[@]}"; do
  image="localhost/ai-inference-basics-$name:dev"
  podman build --format docker -f "oci/$name/Containerfile" -t "$image" .
  case "$name" in
    bastion)
      podman run --rm --entrypoint bash "$image" -ec \
        'kubectl version --client; k9s version; ttyd --version; zellij --version; starship --version; hx --version; code-server --version; curl --version; jq --version; vllm bench serve --help >/dev/null; python3 -c "import json5"; test -s /usr/share/ai-inference-basics/ttyd.html' ;;
    provision)
      podman run --rm --entrypoint python3 "$image" -c 'import huggingface_hub,boto3,bcrypt,yaml'
      podman run --rm --entrypoint rc "$image" --version ;;
    lfm3-omni-2b-transformers)
      podman run --rm --entrypoint python3 "$image" -c 'import torch,torchcodec,soundfile,librosa; from transformers import AutoModelForImageTextToText,AutoProcessor' ;;
  esac
  podman save --format oci-archive -o "dist/$name.oci.tar" "$image"
  digest=$(skopeo inspect --raw "oci-archive:dist/$name.oci.tar" | sha256sum | cut -d' ' -f1)
  echo "localhost/ai-inference-basics-$name@sha256:$digest" > "dist/$name.ref"
  (cd dist && sha256sum "$name.oci.tar" "$name.ref" > "$name.SHA256SUMS")
  echo "Qualified $name artifact:"
  cat "dist/$name.ref"
done
echo 'Import explicitly into k0s, then align image references in the local infra-definition environment JSON.'
