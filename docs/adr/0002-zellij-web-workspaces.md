# ADR 0002: native Zellij web administration

Status: accepted by the user and locally browser-qualified.

Replace ttyd with Zellij 0.46.0's web-enabled upstream binary in a digest-pinned
Fedora Minimal image. Retain bash/curl/git/jq, kubectl, k9s, Helm and Task. Each
participant keeps a dedicated Pod and Kubernetes identity.

Zellij requires native authentication and does not consume oauth2-proxy identity
headers. The user explicitly chose **Dex login followed by a Zellij token**, rather
than retaining ttyd or implementing a transparent authentication bridge.

Zellij binds Pod-local loopback. Caddy forwards the terminal Service, strips the
configured browser path prefix and rewrites the native cookie Path per workspace.
The browser-facing base_url config and server-side path stripping were validated
against the selected binary. TLS remains at Envoy; no unsafe plaintext Zellij
listener on all interfaces is required.

Automation generates one native token per workspace, saves recovery copies only
in protected instructor files and never logs them. Tests prove another workspace's
token is rejected, the native cookie is Secure/HttpOnly/path-scoped, k9s renders
over WebSocket, and in-Pod port-forward previews work.

Session state is emptyDir-backed and disposable. Browser disconnects preserve a
running named session; Pod replacement resets sessions and native tokens. Explicit
installer elevation changes the Pod identity and requires recollecting tokens.
