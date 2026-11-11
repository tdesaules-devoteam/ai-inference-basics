# Project naming and an explicit local rebuild

The source project, chart, Helm release, Kubernetes namespace and model aliases
use `ai-inference-basics`. The OCI destination is
`oci://ghcr.io/tdesaules-devoteam/ai-inference-basics/charts/ai-inference-basics`.
The logo is `docs/logo.png`.

The rename changed repository files only. Existing VM resources, certificates,
secrets, image imports and tunnel state were not migrated. Historical test evidence
is preserved unchanged in `reports/archive/pre-rename/`.

## Rebuild when the operator explicitly chooses to

The following destroys guest data. Run it from the repository root, on the host.
The first command also stops any old-name browser tunnel belonging to this checkout.

```sh
systemctl --user stop "*-browser-$(cat .devenv/.uuid).service"
task infra:destroy PROFILE=local-cpu
ssh-keygen -R "$(cat .devenv/.uuid).local"

# Preserve old local credentials/certificates rather than reusing the old hostname.
stamp=$(date +%Y%m%d-%H%M%S)
test ! -d .local/secrets || mv .local/secrets ".local/secrets-before-rename-$stamp"
test ! -f .local/workspaces.yaml || mv .local/workspaces.yaml ".local/workspaces-before-rename-$stamp.yaml"

# Start the VM, install native k0s and the platform, then run local acceptance.
task up PROFILE=local-cpu
task devenv:ssh
```

Inside the VM:

```sh
cat /etc/os-release
sudo /usr/local/bin/k0s status
sudo /usr/local/bin/k0s kubectl get nodes
sudo /usr/local/bin/k0s kubectl get pods -A
sudo /usr/local/bin/k0s kubectl -n ai-inference-basics get llmisvc,isvc,gateway,httproute
exit
```

Back on the host, `task verify PROFILE=local-cpu` runs the applicable model,
browser, telemetry and isolation checks. `task report` records sanitized evidence.
`task infra:up` alone starts only the base VM; it does not rebuild the platform.

For interactive browser access, follow [the workspace guide](workspaces.md) for
`lab.ai-inference-basics.test`, the new local TLS certificate and native Zellij tokens.
