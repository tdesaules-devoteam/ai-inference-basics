# CI and chart distribution

The three workflow entrypoints remain main (branch pushes), release (manual/tag)
and maintenance (schedule/manual). No VM is started by static CI. The Terraform
action and profile-based checks have been removed from this local-only version.

The active offline platform checks are `tests/validate_lab.py` and
`tests/validate_storage.py`. They render the Helmfile releases and verify pinned
upstream chart bytes. Environment definitions are validated with JSON Schema.
The JSON/Helmfile refactor has local validation; existing hosted workflows still
require a separate review against this layout. Reports are ignored local
development data and are not release prerequisites.

Shared catalog linters use commit-pinned references with digest-pinned images.
Local Go Docker actions are still a bootstrap bridge pending their own publication.
They remain AMD64-only; hosted execution has not been observed and no push is authorized.

Helmfile fetches official charts directly and uses project charts from `charts/`.
There is no umbrella chart, custom post-renderer or k0s Helm deployer. Own OCI
images are built/exported with `oci/prepare.sh` and explicitly imported into the
native k0s containerd while registry publication remains unavailable. Publication
and runtime qualification are separate from successful local builds and renders.
