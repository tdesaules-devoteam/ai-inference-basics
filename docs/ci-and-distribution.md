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

Here `x86_64` (Linux) and `amd64` (OCI) mean the same thing. The current lab
ships AMD64 binaries and Python wheels. ARM64 is a distinct target and is not
advertised. Both development and release run CI-operation fixtures. Developers
can run the same suite with `python3 .github/scripts/test-actions.py`.

The selector discovers application Containerfiles under `oci/`. Application
source changes rebuild the affected archives; smoke changes retest published
digests; Grype/Syft policy changes scan published digests without issuing a
functional receipt. Release preparation requalifies the full application set and
reuses unchanged manifests from the last annotated release. Before the first
source tag, maintenance takes its subjects from the public environment sample.
The `helpers` dispatch on main builds and exercises the repository's CI actions
and publishes them by digest without creating a Git tag or publishing lab images.
