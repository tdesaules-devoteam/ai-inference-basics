#!/usr/bin/env bash
# Helm post-renderer: append domain-owned hooks to the upstream release.
# No Kubernetes calls or credential generation occur while rendering.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
domain=${1:?domain required}
case "$domain" in dex|oauth2-proxy|rustfs) ;; *) exit 2 ;; esac
hostname=${LAB_HOSTNAME:?LAB_HOSTNAME required}
[[ $hostname =~ ^[a-zA-Z0-9.-]+$ ]] || exit 2
image=${LAB_TOOLS_IMAGE:-localhost/ai-inference-basics-bastion@sha256:8db01fd11860abeb0074c86956ee9b283fbd73f1b80a4184bd232cbd4172fae4}
[[ $image =~ ^[a-zA-Z0-9./:_@-]+$ ]] || exit 2
hook=pre-install,pre-upgrade
weight=0
if [[ $domain == rustfs ]]; then hook=post-install,post-upgrade; weight=10; fi
cat
for manifest in "$root/domains/common"/*.yaml "$root/domains/$domain"/*.yaml; do
  echo '---'
  sed -e "s|@DOMAIN@|$domain|g" -e "s|@HOSTNAME@|$hostname|g" \
      -e "s|@IMAGE@|$image|g" -e "s|@HOOK@|$hook|g" -e "s|@WEIGHT@|$weight|g" "$manifest"
done
if [[ $domain == rustfs ]]; then
  for model in qwen3-0-6b qwen3-embedding-0-6b qwen3-reranker-0-6b; do
    for manifest in "$root/domains/rustfs/models"/*.yaml; do
      echo '---'
      sed "s|@MODEL@|$model|g" "$manifest"
    done
  done
fi
cat <<EOF
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${domain}-domain
  namespace: ${domain}
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: before-hook-creation
data:
  kube.py: |
EOF
sed 's/^/    /' "$root/files/kube.py"
echo '  job.py: |'
sed 's/^/    /' "$root/domains/$domain/job.py"
