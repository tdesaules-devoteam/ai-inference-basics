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

Use `task ssh` and inspect `/var/lib/ai-inference-basics/credentials.json` with sudo
for the two initial Dex accounts (`alice@example.test` and `bob@example.test`).
The native Zellij login tokens are `zellij-a.token` and `zellij-b.token` in the same
guest directory. Share each token only with the assigned participant.

Zellij listens on Pod-local loopback. Caddy serves its web client through the
terminal Service and scopes its session cookie per terminal path. The additional
native-token login is intentional, not an authentication bypass.

Inside a bastion, run k9s or kubectl. A preview uses the fixed port:

```sh
kubectl -n demo port-forward --address 127.0.0.1 svc/whoami 18080:80
```

Keep it running in a Zellij pane. The preview returns 502 without the forward.
Pod replacement discards its emptyDir session state; VM replacement discards the lab.
