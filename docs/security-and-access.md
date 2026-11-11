# Security and access

Host preparation generates Dex passwords, bcrypt hashes, OAuth client/cookie
secrets, the inference API key and a local TLS certificate in the private, ignored
`.local/build/runtime/` directory. Ignition copies the resulting credential
manifests into the guest with mode 0600; the k0s manifest deployer creates Secrets.
Automation does not print credential values. task down destroys the guest state
and removes the marked host preparation directory, allowing fresh credentials for
the next VM. Retries before destruction preserve the same credentials.

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
