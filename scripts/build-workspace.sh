#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
podman build --format docker -f images/admin-workspace/Containerfile -t localhost/ai-inference-basics-admin:dev .
podman run --rm --entrypoint bash localhost/ai-inference-basics-admin:dev -c \
  'zellij --version && kubectl version --client && helm version --short && k9s version && task --version'
podman save --format oci-archive -o .local/admin.oci.tar localhost/ai-inference-basics-admin:dev
digest="sha256:$(skopeo inspect --raw oci-archive:.local/admin.oci.tar | sha256sum | cut -d ' ' -f1)"
bash scripts/guest.sh 'sudo /usr/local/bin/k0s ctr images import --digests ~/workspace/.local/admin.oci.tar'
bash scripts/guest.sh "sudo /usr/local/bin/k0s ctr images tag --force localhost/ai-inference-basics-admin:dev localhost/ai-inference-basics-admin@$digest"
printf 'workspaces:\n  enabled: true\n  image: localhost/ai-inference-basics-admin@%s\n  imagePullPolicy: Never\nobservability:\n  enabled: true\n' "$digest" > .local/workspaces.yaml
printf '{"image":"localhost/ai-inference-basics-admin@%s","platform":"linux/amd64","publication":"local containerd import only"}\n' "$digest" > .local/workspace-image.json
