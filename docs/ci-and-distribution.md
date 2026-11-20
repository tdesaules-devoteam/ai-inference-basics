# CI and OCI distribution

Branch pushes run `main`; manual release preparation on `main` and stable SemVer
tags run `release`; scheduled or manual maintenance runs `maintenance`. No VM or
private environment definition is used. See [action contracts](../.github/actions/README.md).

The Helmfile checks render both environments plus an empty model selection and
check the bytes of pinned HTTP charts. Images are built separately for native
AMD64 and exercised inside their own digest-qualified runtimes. A source tag is
prepared only after both tested manifests can be read back from GHCR. The tag
workflow uses the recorded digests, not a rebuild. GitHub job artifacts are
transfer and diagnostic files, not release image identities.

`oci/prepare.sh` provides local qualification and import while registry access is
being configured. After publishing, set `images.bastion` and `images.provision`
to the verified public digest references in the environment JSON. The bootstrap
unit pulls remote references before Helmfile and waits for explicit imports only
for `localhost/` references. Never put registry tokens into the committed sample.
