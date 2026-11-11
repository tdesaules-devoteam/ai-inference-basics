# CI and OCI distribution

Three entrypoints are implemented: branch-only `main`, tag/manual `release`, and
scheduled/manual `maintenance`. No PR trigger. Lint/build/test are distinct jobs;
tag qualification pulls the previously published chart by digest and never rebuilds.
Manual runs require main. Failed selected dependencies block publication.

Shared lint/Renovate actions use commit-pinned catalog references whose Docker
images are digest-pinned. Project Helm operations are dedicated Go Docker actions,
each with a multistage recipe. Their **local Dockerfile references are a bootstrap
bridge**, not released digest-pinned action images. Remove the bridge after building,
testing and publishing those action images and replacing runs.image with verified
docker:// digests. AMD64 qualification only is currently implemented for them.

Manual release packages the current chart version, qualifies exact bytes, pushes
to `ghcr.io/tdesaules-devoteam/ai-inference-basics/charts`, pulls by OCI digest and
compares archive bytes. It refuses replacement of an existing version. Save the
publication receipt as `charts/release.json` before stable tag qualification.

Remaining release work: bot-based version preparation/git-cliff, GitHub Release
creation, advisory Syft/Grype/Cosign evidence and native ARM64 action qualification.
No automatic stable tag is created before the runtime training gates pass.

Required external setup: workflow-capable source push, package-write workflow
permissions, package visibility/access, and `vars.BOT_APP_ID` plus
`secrets.BOT_APP_PRIVATE_KEY` for repository-scoped Renovate tokens. Avoid a duplicate
hosted Renovate App. The currently inspected local GitHub token lacks workflow and
package-write scopes; no hosted execution/publication is claimed.

Local checks do not prove hosted execution, and archive render qualification does
not prove model, browser, cloud or H100 acceptance.
