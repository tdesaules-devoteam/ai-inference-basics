# Participant bastion image

The digest-pinned Fedora Minimal AMD64 image includes kubectl, k9s, vLLM
(`vllm bench`), curl, bash, Zellij CLI, Starship, jq, Helix, code-server and RustFS rc.
Downloaded tools and Python dependencies have checksum locks. RPM versions actually
installed are recorded in `/usr/share/ai-inference-basics/rpms.txt` in the image.

`bash oci/prepare.sh` builds, checks the CLI tools and exports `dist/bastion.oci.tar`,
`dist/bastion.ref` and `dist/SHA256SUMS`. It does not operate the VM or publish.
The build uses Docker format for SHELL semantics, then exports an OCI archive.

ttyd runs Zellij CLI as UID 1000. code-server runs in a separate container sharing
the participant's PVC. Both are behind the same Dex/oauth2-proxy session; neither
requires a second application login. Each participant has a distinct ServiceAccount,
workspace PVC and editable namespace. Headlamp provides shared read-only inspection.

GHCR publication was rejected by the available token. The current lab uses an
explicit local k0s import with `toolsImagePullPolicy: Never`. After recreating the
VM, import the archive again and align `toolsImage` with its manifest digest before
retrying bootstrap. See [lab access and qualification](../../docs/lab.md).
