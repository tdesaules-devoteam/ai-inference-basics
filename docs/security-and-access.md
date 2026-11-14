# Security and access

One Dex account named `admin` is shared by the pair at one computer. Its login
email is `ai-inference-basics@devoteam.com`. The bastion and Headlamp ServiceAccounts both have
Kubernetes `cluster-admin` rights across all namespaces, as intended for this lab.
The bastion's Linux process runs as UID 1000; its Kubernetes privileges come from
the ServiceAccount, not a privileged container.

Domain-local Helm hook Jobs generate and preserve credentials in Kubernetes:

- `dex/admin-access`: admin identity/password and the OIDC client state.
- `dex/admin-login`: optional operator-supplied email/password override, kept out of Git.
- `dex/oidc-client`: the published browser client credentials, readable by the
  oauth2-proxy configuration Job.
- `oauth2-proxy/browser-session`: the stable cookie key.
- `gateway/lab-api-key`: the separate static model API key.
- `rustfs/s3-<model>`: distinct reader/writer credentials for each model prefix.

No generated credential is tracked or printed by automation. The rendering plugin
only appends resource definitions; credential generation happens in the cluster.
Each model's serving workload receives read-only credentials and no Kubernetes API
token. Object access is limited to that model's prefix; bucket metadata permission
supports KServe's initial HeadBucket operation.

The Gateway terminates HTTPS using a cert-manager-issued certificate from the lab
CA. Its private key stays in `gateway`; a public CA ConfigMap supplies client trust.
Internal Dex/oauth2-proxy traffic remains HTTP. Browser access uses one Dex session
through oauth2-proxy; there is no second Zellij token. Model APIs require their own
Bearer key and reject browser cookies as authorization.

NetworkPolicies restrict incoming traffic to browser backends and model servers.
This is a shared administration lab, not isolated multi-tenancy. See [lab access](lab.md)
for private credential retrieval and the distinction between active/stopped models.
