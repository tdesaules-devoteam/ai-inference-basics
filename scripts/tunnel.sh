#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
identity=$(cat .devenv/.uuid)
unit="ai-inference-basics-browser-$identity"
if ! systemctl --user is-active --quiet "$unit"; then
  systemd-run --user --unit="$unit" --collect \
    --property=Restart=on-failure --property=RestartSec=2s \
    /usr/bin/ssh -NT -o BatchMode=yes -o ExitOnForwardFailure=yes \
    -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
    -L 127.0.0.1:30443:127.0.0.1:30443 "$identity.local"
fi
for ((attempt = 1; attempt <= 30; attempt++)); do
  if curl --noproxy '*' --silent --fail --max-time 2 \
      --cacert .local/secrets/tls.crt --resolve lab.ai-inference-basics.test:30443:127.0.0.1 \
      https://lab.ai-inference-basics.test:30443/headlamp/ -o /dev/null; then
    echo 'Browser gateway ready on workstation loopback port 30443.'
    exit 0
  fi
  sleep 1
done
echo "Tunnel did not become ready; inspect journalctl --user -u $unit." >&2
exit 1
