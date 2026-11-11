# Administration bastions

`oci/bastion/` builds a digest-addressed Fedora Minimal image containing Zellij
0.46.0 (web enabled), bash, curl, jq, git, kubectl, k9s, Helm and Task.
It is built on the host, exported as OCI and imported into k0s's embedded containerd.
No container engine runs inside Kubernetes.

After `task up`, use the hostname printed by the command:

- `https://<vm-hostname>:30443/headlamp/`
- `https://<vm-hostname>:30443/grafana/`
- `https://<vm-hostname>:30443/terminal-a/workshop`
- `https://<vm-hostname>:30443/terminal-b/workshop`
- `https://<vm-hostname>:30443/preview-a/` and `/preview-b/`

The original devenv bridge/mDNS configuration provides access. No workstation
systemd tunnel, custom hosts-file entry or loopback URL is part of this flow.
Accept/trust the lab's self-signed TLS certificate explicitly.

The instructor can inspect `.local/build/runtime/credentials.json` on the host
for the two initial Dex accounts (`alice@example.test` and `bob@example.test`).
The same information is available through the administrator kubeconfig inside the VM:

```sh
kubectl -n ai-inference-basics get secret ai-inference-basics-access \
  -o 'jsonpath={.data.credentials\.json}' | base64 -d
```

Retrieve the native Zellij token for a participant with:

```sh
kubectl -n ai-inference-basics exec deployment/workspace-a -c terminal -- \
  cat /workspace/.local/share/ai-inference-basics/web-login.txt
```

Use workspace-b for the other participant. These commands display secrets only
when the instructor explicitly requests them; share each token with its participant.

Zellij listens on Pod-local loopback. Caddy serves its web client through the
terminal Service and scopes its session cookie per terminal path. The additional
native-token login is intentional, not an authentication bypass.

Inside a bastion, run k9s or kubectl. A preview uses the fixed port:

```sh
kubectl -n demo port-forward --address 127.0.0.1 svc/whoami 18080:80
```

Keep it running in a Zellij pane. The preview returns 502 without the forward.
Pod replacement discards its emptyDir session state; VM replacement discards the lab.
