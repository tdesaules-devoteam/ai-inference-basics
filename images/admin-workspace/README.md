# Zellij administration workspace

Digest-pinned Fedora Minimal 45 in both stages, with bash, curl, jq, git, kubectl,
k9s, Helm, Task and checksum-pinned Zellij 0.46.0 (web-enabled GNU binary).
No privileged mode or container engine is installed. Initial qualification is AMD64.

```sh
podman build --format docker -f images/admin-workspace/Containerfile -t localhost/ai-inference-basics-admin:dev .
podman run --rm --entrypoint bash localhost/ai-inference-basics-admin:dev -c \
  'zellij --version && kubectl version --client && helm version && k9s version && task --version'
```

Resolve the resulting OCI manifest digest before chart deployment. Local testing
uses Docker build format to honor the Containerfile SHELL setting, then exports an
OCI archive and locks that exported manifest. This does not install Docker in k0s.
Local testing
may import the exact OCI archive into k0s containerd; publication to GHCR requires
package-write credentials and must preserve that artifact's digest.

Zellij web listens on Pod-local loopback. The Caddy sidecar forwards the terminal
Service to it; external TLS and Dex/oauth2-proxy remain at the gateway. Zellij
additionally requires its native login token, generated once per workspace and
kept in its writable home. The instructor copies it to a protected local file via
`task workspace:credentials`; no token is written to container logs.

Caddy scopes Zellij's `session_token` cookie to each terminal path, avoiding cookie
collisions between the two workspaces on the local lab hostname. The two login
steps are intentional and user-approved; no authentication-bypass proxy is added.
