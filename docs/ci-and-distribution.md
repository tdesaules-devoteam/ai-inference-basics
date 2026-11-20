# CI and OCI distribution

Branch pushes run `main`; manual release preparation on `main` and stable SemVer
tags run `release`; scheduled or manual maintenance runs `maintenance`. No VM or
private environment definition is used. All action sources are owned by the [shared catalog](https://github.com/tdesaules/github-actions).

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
advertised. Selection, qualification receipts and release-operation tests live
with their implementations in the catalog. The lab owns the render and
application assertions, including `.github/scripts/smoke-{bastion,provision}.py`.

The selector discovers application Containerfiles under `oci/`. Application
source changes rebuild the affected archives; smoke changes retest published
digests; Grype/Syft policy changes scan published digests without issuing a
functional receipt. Release preparation requalifies the full application set and
reuses unchanged manifests from the last annotated release. Before the first
source tag, maintenance takes its subjects from the public environment sample.
The shared `new-candidate-action` writes `./.candidate` only in the runner workspace
to execute those assertions inside the exact tested Docker image. No action metadata
or CI helper image is maintained or published by this repository.
