# Lab CI operations

`check` selects AMD64 images by changed paths and verifies manual and tag events.
`lint-helm` exercises the actual Helmfile with the public fixtures only. The
shared Buildah action exports a separate archive and untested receipt for each
selected component. Each test job verifies the receipt, imports the manifest by
digest into an isolated runner-local registry, and runs the corresponding smoke
action inside the exact image. Smoke metadata is instantiated by the shared
`new-candidate-action` operation; it is not a stand-alone tool image.

`record-qualification` rehashes the tested archive before emitting a tested
receipt. The release workflow publishes these exact archives, reads the manifests
back anonymously, and `tag-images` compares both returned digests to the tested
receipts before tagging the source. The annotated tag contains the two digests;
tag jobs qualify them again without a rebuild before creating the GitHub release.
Syft and Grype reports are advisory. The application images currently contain
x86-64-only pinned tools; this pipeline does not advertise ARM64 support.

Local Go actions use their sibling Dockerfile until dedicated images are
published. To run the release workflow configure `BOT_APP_ID` and
`BOT_APP_PRIVATE_KEY` for a repository-scoped App installation with contents
write access, enable GHCR package publication for the workflow, and permit
anonymous pulls of both packages. Maintenance uses a separate installation token.
