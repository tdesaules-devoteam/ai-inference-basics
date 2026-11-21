# Shared administration bastion image

The public AMD64 image runs ttyd with the Zellij CLI and code-server in separate
containers sharing a workspace PVC. It includes kubectl, k9s, Helix, Starship,
vLLM's CLI and the Nord/Geist browser assets. Tools and Python dependencies have
checksum locks; the final RPM inventory is in `/usr/share/ai-inference-basics/rpms.txt`.

The terminal runs as UID 1000. Its Kubernetes permissions come from the bastion
ServiceAccount, not the Linux user. Dex and oauth2-proxy handle browser login.
Credential and import Jobs use the **provision** image (including RustFS `rc`),
not this administration image.

The environment definition normally selects a public GHCR digest. To build and
smoke-test a local alternative, run `bash oci/prepare.sh bastion` on Linux AMD64.
It writes `dist/bastion.oci.tar`, `dist/bastion.ref` and `dist/bastion.SHA256SUMS`.
See [lab setup](../../docs/lab.md) for local imports and image selection.
