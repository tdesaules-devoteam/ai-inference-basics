# Security and access

One Dex account named `cluster-admin` is shared by the pair at one computer. Its login
email comes from `access.adminEmail` in the private environment definition. The bastion and Headlamp ServiceAccounts both have
Kubernetes `cluster-admin` rights across all namespaces, as intended for this lab.
The bastion's Linux process runs as UID 1000; its Kubernetes privileges come from
the ServiceAccount, not a privileged container.

Domain-local Helm hook Jobs generate and preserve credentials in Kubernetes:

- `dex/admin-access`: admin identity/password, bcrypt hash and the OIDC client state.
- `dex/admin-login`: email/password supplied by the private environment definition.
- `dex/oidc-client`: browser client credentials cloned by Kyverno into oauth2-proxy.
- `oauth2-proxy/oauth-config`: Kyverno combines the local OIDC client and session key.
- `oauth2-proxy/browser-session`: the stable cookie key.
- `gateway/lab-api-key`: the separate static model API key.
- `rustfs/s3-observability`: separate credentials restricted to the five telemetry buckets.
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

Model prefixes organize artifacts, but are not authorization boundaries. The
shared account can overwrite objects in any model prefix; revision naming and
import hash checks do not implement S3 Object Lock. Storage qualification checks
cross-prefix reads/writes and denies all five observability buckets.

Kyverno transforms the shared S3 source on Secret updates, then uses synchronized
clones for consumers. Public CA generation watches the source ConfigMap, and
oauth configuration watches its local source Secrets. Data-changing updates to
bastion, Dex and oauth2-proxy credential Secrets trigger scoped MutatingPolicies
that change a Deployment Pod-template annotation. This rolls out processes that
read credentials or CA bundles only at startup. Only resource versions, not
credential contents, appear in those annotations. Metadata-only Secret updates
do not trigger a rollout. The background controller has namespaced permissions
restricted to the three named Deployments. Rotation can briefly interrupt the
single-instance applications and requires runtime qualification.

The public CA is distributed through `gateway/lab-ca` and consumer trust
configuration. Private CA/server keys remain in cert-manager Secrets; publishing
the public CA does not publish those keys. The VM's administrative kubeconfig
uses the X.509 identity `kubernetes-admin` in `system:masters`; the bastion uses
`system:serviceaccount:bastion:bastion`.
