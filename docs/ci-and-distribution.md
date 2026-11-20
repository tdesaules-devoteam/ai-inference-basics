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

`oci/prepare.sh` provides an offline alternative to the published images.
When promoting a new publication, set `images.bastion` and `images.provision`
to the verified public digest references in the environment JSON. The bootstrap
unit pulls remote references before Helmfile and waits for explicit imports only
for `localhost/` references. Never put registry tokens into the committed sample.

For package publication without a Git release, dispatch `release.yml` on `main`
with `images-only=true`. This uses the same build, functional test, receipt and
public digest checks with the job's `packages: write` permission; no bot token
or source ref mutation is needed in this mode.
