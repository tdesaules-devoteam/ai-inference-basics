#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
mkdir -p .local
exec 9>.local/devenv.lock
flock 9
export AI_INFERENCE_BASICS_PROJECT_ROOT="$ROOT"
key=${AI_INFERENCE_BASICS_SSH_KEY:-$HOME/.ssh/id_ed25519.pub}
[[ -s "$key" ]] || { echo "Missing public SSH key: $key" >&2; exit 1; }
export AI_INFERENCE_BASICS_SSH_PUBLIC_KEY
AI_INFERENCE_BASICS_SSH_PUBLIC_KEY=$(cat "$key")
unset GITHUB_TOKEN BESZEL_KEY BESZEL_PASSWORD BESZEL_USER
patch="$ROOT/infra/devenv/patches/runtime.patch"
if git -C .devenv apply --check "$patch" 2>/dev/null; then
  git -C .devenv apply "$patch"
elif ! git -C .devenv apply --reverse --check "$patch" 2>/dev/null; then
  echo 'Runtime differs from the reviewed patch; preserve changes and inspect manually.' >&2
  exit 1
fi
[[ -s .devenv/config.k ]] || { echo 'Create local .devenv/config.k; see docs/devenv.md.' >&2; exit 1; }
if [[ ! -s .devenv/.uuid ]]; then
  python3 -c 'import uuid; print(uuid.uuid4())' > .devenv/.uuid
fi
umask 077
cleanup() {
  if git -C .devenv apply --reverse --check "$patch" 2>/dev/null; then
    git -C .devenv apply --reverse "$patch"
  else
    echo 'Runtime changed during execution; retained it for manual review.' >&2
  fi
}
trap cleanup EXIT
task -t "$ROOT/.devenv/taskfile.qemu.yaml" "$@"
