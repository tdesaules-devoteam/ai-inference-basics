#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p "$HOME/.config" "$XDG_RUNTIME_DIR"
[[ -e "$HOME/.bashrc" ]] || cp /etc/lab-bashrc "$HOME/.bashrc"
if [[ -r /var/run/secrets/kubernetes.io/serviceaccount/token && ! -e "$HOME/.kube/config" ]]; then
  mkdir -p "$HOME/.kube"
  cat > "$HOME/.kube/config" <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: lab
    cluster:
      server: https://kubernetes.default.svc
      certificate-authority: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
users:
  - name: participant
    user:
      tokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
contexts:
  - name: lab
    context:
      cluster: lab
      user: participant
      namespace: ${LAB_NAMESPACE:-default}
current-context: lab
EOF
fi
if [[ -r /etc/lab-ca/ca.crt ]]; then
  cat /etc/ssl/certs/ca-certificates.crt /etc/lab-ca/ca.crt > "$HOME/.config/lab-ca-bundle.pem"
fi
export ZELLIJ_AUTO_ATTACH=true
exec ttyd --writable --check-origin --port 7681 --base-path "${TERMINAL_BASE_PATH:-/terminal}" \
    zellij --config /etc/zellij/config.kdl attach --create lab
