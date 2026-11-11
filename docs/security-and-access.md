# Security and access

Each fresh VM generates its own Dex passwords, bcrypt hashes, OAuth client/cookie
secrets, inference API key and local TLS certificate. They live in the guest under
`/var/lib/ai-inference-basics/`, not in Terraform, Git or host-side saved profiles.
The bootstrap writes Kubernetes Secrets through the k0s manifest deployer and does
not print credential values. VM destruction removes that guest state.

Browser access uses Dex + oauth2-proxy. Zellij also requires a native per-bastion
token. Model APIs instead use an opaque static Bearer key validated by Envoy.
Kubernetes identities are separate: the instructor has an administrative kubeconfig
inside the guest, while ordinary bastion/Headlamp identities are read-oriented.

The gateway is reached directly through the VM bridge/mDNS name on HTTPS 30443.
The local certificate is self-signed and requires explicit browser trust; it is not
a publicly trusted certificate. Backend Services remain ClusterIP and protected
by NetworkPolicies. This disposable shared workshop is not hostile multi-tenancy.

The upstream devenv defaults are preserved. Review its personal configuration-copy
behavior before using a workstation containing credentials you do not want in a
development VM. Generated render artifacts must remain private and untracked.
