#!/usr/bin/env bash
# Build, qualify and export local OCI artifacts; never operate a VM or publish.
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
[[ $(uname -sm) == 'Linux x86_64' ]] || { echo 'Linux AMD64 build required.' >&2; exit 1; }
for binary in podman python3 sha256sum; do command -v "$binary" >/dev/null; done
mkdir -p dist
selection=${1:-all}
case "$selection" in
  all) images=(bastion provision lfm3-omni-2b-transformers) ;;
  bastion|provision|lfm3-omni-2b-transformers|lfm3-omni-2b-transformers-cuda) images=("$selection") ;;
  *) echo 'Expected all, bastion, provision, lfm3-omni-2b-transformers or lfm3-omni-2b-transformers-cuda.' >&2; exit 2 ;;
esac
for name in "${images[@]}"; do
  image="localhost/ai-inference-basics-$name:dev"
  source=$name
  build_args=()
  if [[ $name == lfm3-omni-2b-transformers-cuda ]]; then
    source=lfm3-omni-2b-transformers
    build_args=(--build-arg REQUIREMENTS_LOCK=requirements-cuda.lock --build-arg TORCH_BACKEND=cu128)
  fi
  podman build --format docker "${build_args[@]}" -f "oci/$source/Containerfile" -t "$image" .
  case "$name" in
    bastion)
      podman run --rm --entrypoint bash "$image" -ec \
        'kubectl version --client; k9s version; ttyd --version; zellij --version; starship --version; hx --version; code-server --version; curl --version; jq --version; vllm bench serve --help >/dev/null; python3 -c "import json5"; test -s /usr/share/ai-inference-basics/ttyd.html' ;;
    provision)
      podman run --rm --entrypoint python3 "$image" -c 'import huggingface_hub,boto3,bcrypt,yaml'
      podman run --rm --entrypoint rc "$image" --version ;;
    lfm3-omni-2b-transformers|lfm3-omni-2b-transformers-cuda)
      podman run --rm --entrypoint python3 "$image" -c 'import torch,torchcodec,soundfile,librosa,server; from transformers import AutoModelForImageTextToText,AutoProcessor; import sys; assert bool(torch.version.cuda) == (sys.argv[1] == "cuda")' "${name##*-}"
      podman run --rm --entrypoint ffprobe "$image" -version ;;
  esac
  podman save --format oci-archive -o "dist/$name.oci.tar" "$image"
  digest=$(python3 - "dist/$name.oci.tar" <<'PY'
import hashlib, json, sys, tarfile
with tarfile.open(sys.argv[1]) as archive:
    index = json.load(archive.extractfile('index.json'))
    assert len(index['manifests']) == 1, 'Expected one native image manifest'
    digest = index['manifests'][0]['digest']
    assert digest.startswith('sha256:')
    payload = archive.extractfile('blobs/sha256/' + digest.split(':')[1]).read()
    assert digest == 'sha256:' + hashlib.sha256(payload).hexdigest()
    print(digest)
PY
)
  echo "localhost/ai-inference-basics-$name@$digest" > "dist/$name.ref"
  (cd dist && sha256sum "$name.oci.tar" "$name.ref" > "$name.SHA256SUMS")
  echo "Smoke-tested $name artifact (model inference requires separate qualification):"
  cat "dist/$name.ref"
done
echo 'Import explicitly into k0s, then align image references in the local infra-definition environment JSON.'
