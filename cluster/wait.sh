#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
host="$(cat .devenv/.uuid).local"
ssh_options=(-o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ProxyCommand=none)
for ((attempt = 1; attempt <= 240; attempt++)); do
  if ssh "${ssh_options[@]}" "$host" 'sudo test -f /var/lib/ai-inference-basics/ready && sudo /usr/local/bin/k0s kubectl get --raw=/readyz --request-timeout=5s >/dev/null'; then
    printf 'Lab ready: https://%s:30443/headlamp/\nConnect with: task ssh\n' "$host"
    exit 0
  fi
  if ssh "${ssh_options[@]}" "$host" 'systemctl is-failed --quiet ai-inference-basics-bootstrap.service'; then
    echo 'Guest bootstrap failed. Use task ssh, then sudo journalctl -u ai-inference-basics-bootstrap.service.' >&2
    exit 1
  fi
  sleep 5
done
echo 'Bootstrap did not finish within 20 minutes; inspect the guest bootstrap journal.' >&2
exit 1
