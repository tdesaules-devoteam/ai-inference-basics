# Security and access

One Dex account named `cluster-admin` is shared by the pair at one computer. Its login
email is `cluster-admin@devoteam.com`. The bastion and Headlamp ServiceAccounts both have
Kubernetes `cluster-admin` rights across all namespaces, as intended for this lab.
The bastion's Linux process runs as UID 1000; its Kubernetes privileges come from
the ServiceAccount, not a privileged container.

Domain-local Helm hook Jobs generate and preserve credentials in Kubernetes:

- `dex/admin-access`: admin identity/password, bcrypt hash and the OIDC client state.
- `dex/admin-login`: email/password supplied by the private environment definition.
- `dex/oidc-client`: the published browser client credentials, readable by the
  oauth2-proxy configuration Job.
- `oauth2-proxy/browser-session`: the stable cookie key.
- `gateway/lab-api-key`: the separate static model API key.
- `rustfs/s3-models`: shared read/write credentials for the models bucket.

No generated credential is tracked or printed by deployment automation.
Technical credential generation happens in cluster initialization Jobs.
Each model's serving workload receives the shared bucket credential and no
Kubernetes API token. The account can read/write all model prefixes; other
application buckets remain excluded.

The Gateway terminates HTTPS using a cert-manager-issued certificate from the lab
CA. Its private key stays in `gateway`; a public CA ConfigMap supplies client trust.
Internal Dex/oauth2-proxy traffic remains HTTP. Browser access uses one Dex session
through oauth2-proxy; there is no second Zellij token. Model APIs require their own
Bearer key and reject browser cookies as authorization.

NetworkPolicies restrict incoming traffic to browser backends and model servers.
This is a shared administration lab, not isolated multi-tenancy. See [lab access](lab.md)
for private credential retrieval and the distinction between active/stopped models.

`task lab:access` explicitly prints the current browser login and API key for private
operator use. It reads live Kubernetes Secrets rather than a Terraform output or
tracked values file. Terraform does not currently provision this lab; exposing
credentials through Terraform outputs would also place them in its state.

Initialization Jobs use cryptographic random generation for missing technical
keys. The Dex Job also calculates bcrypt. There are no credentials.py or kube.py
files. Kyverno policies implement cross-namespace distribution. ConfigMaps contain
code or public configuration, not credential values.

Copies into consuming namespaces are necessary because Pod Secret references
cannot cross namespaces. Model-reader credentials originate in RustFS's domain
and are synchronized into each model namespace. The compatibility names
model-reader/model-writer now hold the same account. Existing root/shared S3
credentials are preserved during upgrades without putting their values in Git.

The public CA is distributed through `gateway/lab-ca` and consumer trust
configuration. Private CA/server keys remain in cert-manager Secrets; publishing
the public CA does not publish those keys. The VM's administrative kubeconfig
uses the X.509 identity `kubernetes-admin` in `system:masters`; the bastion uses
`system:serviceaccount:bastion:bastion`.
