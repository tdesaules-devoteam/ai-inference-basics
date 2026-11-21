#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p "$HOME/.config" "$XDG_RUNTIME_DIR"
[[ -e "$HOME/.bashrc" ]] || cp /etc/lab-bashrc "$HOME/.bashrc"
# Reference the projected token file so kubectl sees token rotation without rewriting the PVC.
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
    --index /usr/share/ai-inference-basics/ttyd.html \
    --client-option 'fontFamily=Geist Mono, Symbols Nerd Font Mono, monospace' \
    --client-option 'theme={"background":"#2e3440","foreground":"#d8dee9","cursor":"#d8dee9","black":"#3b4252","red":"#bf616a","green":"#a3be8c","yellow":"#ebcb8b","blue":"#81a1c1","magenta":"#b48ead","cyan":"#88c0d0","white":"#e5e9f0","brightBlack":"#4c566a","brightRed":"#bf616a","brightGreen":"#a3be8c","brightYellow":"#ebcb8b","brightBlue":"#81a1c1","brightMagenta":"#b48ead","brightCyan":"#8fbcbb","brightWhite":"#eceff4"}' \
    zellij --config /etc/zellij/config.kdl attach --create lab
