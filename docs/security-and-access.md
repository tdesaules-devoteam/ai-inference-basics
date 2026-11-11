# Security and access

## Browser sessions

Dex runs inside k0s with its password database enabled and exactly two static
email-based identities per lab. IDs remain stable across upgrades. Generate bcrypt
password hashes and distribute Dex configuration through an existing Kubernetes
Secret. oauth2-proxy is the OIDC client; no custom authentication service.

Validate OIDC discovery, issuer/callback URLs, explicit email allowlists, login,
logout, invalid credentials, CSRF, Secure/HttpOnly/SameSite cookies, redirects and
WebSockets locally before cloud acceptance. `/oauth2/auth` alone returns 202/401;
it does not implement the interactive redirect. Use a tested gateway integration
or oauth2-proxy reverse-proxy mode. Strip spoofed identity headers at the boundary.

Local browser routing must remain private to the workstation, with trusted local
TLS and names consistently reachable from the browser and in-cluster OIDC client.
Cloud uses valid DNS/TLS and one HTTPS NodePort (30443 initially). Keep API 6443
private and SSH limited to instructor CIDRs.

## Inference API

Every externally exposed model route requires `Authorization: Bearer <static-key>`.
Generate a high-entropy key per environment, store it in a Secret, never in values,
logs, source or command output. Enforce it using the selected Envoy Gateway's
supported API-key policy; verify opaque Bearer parsing rather than using JWT
validation. Test absent/incorrect keys, all model routes and direct backend bypass.
Browser cookies do not authenticate model API requests. Remove keys at lab teardown.

## Kubernetes identities

Dex authenticates web sessions; Kubernetes SAs authorize in-Pod kubectl/k9s.
These are separate identities, not automatically per-user Kubernetes OIDC RBAC.
Use a dedicated SA and workspace per participant. Headlamp's shared read-oriented
identity must have tested permissions and must not trust user-supplied auth headers.
A separately labeled temporary installer identity can install cluster CRDs/Helm.
The shared disposable workshop does not promise hostile-user tenant isolation.

Use NetworkPolicies where supported to prevent protected backend bypass. Preserve
instructor SSH/provider-console recovery if a learner breaks gateway/RBAC. Session
secrets and Dex credentials are per lab and destroyed with it. Never put secrets
in Terraform user data/state if avoidable; both can retain bootstrap values.
