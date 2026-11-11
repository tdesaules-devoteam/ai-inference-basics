# Administration bastion image

Digest-pinned Fedora Minimal with bash, curl, jq, git, kubectl, k9s, Helm, Task and
the checksum-pinned Zellij 0.46.0 web binary. No container engine or privileged shell.

`oci/prepare.sh` builds and smoke-tests the AMD64 image, exports an OCI archive,
records its exact digest/checksum and packages the umbrella. Guest bootstrap imports
that verified archive into k0s's embedded containerd. Docker build format is used
only to honor Containerfile SHELL semantics before OCI export.

Zellij binds Pod-local loopback. The Caddy sidecar exposes its web client and the
fixed port-forward preview. Dex and native Zellij token authentication remain
separate; automation never prints the generated tokens.
