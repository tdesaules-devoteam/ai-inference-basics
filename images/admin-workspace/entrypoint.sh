#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p "$HOME/.local/share/ai-inference-basics" "$XDG_RUNTIME_DIR"
if [[ ! -s "$HOME/.local/share/ai-inference-basics/web-login.txt" ]]; then
  zellij --config /etc/zellij/config.kdl web --create-token > "$HOME/.local/share/ai-inference-basics/web-login.txt"
fi
exec zellij --config /etc/zellij/config.kdl web --start
