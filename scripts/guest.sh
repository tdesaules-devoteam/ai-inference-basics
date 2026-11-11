#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
[[ -s "$ROOT/.devenv/.uuid" ]] || { echo 'Initialize the local VM first.' >&2; exit 1; }
exec ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
  "$(cat "$ROOT/.devenv/.uuid").local" "$@"
