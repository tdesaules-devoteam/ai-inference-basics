# CI and chart distribution

The three workflow entrypoints remain main (branch pushes), release (manual/tag)
and maintenance (schedule/manual). No VM is started by static CI. The Terraform
action and profile-based checks have been removed from this local-only version.

Dedicated Docker actions verify source, lint the chart and k0s deployment values,
package one candidate archive, and qualify those exact bytes. Tests render the
four disjoint releases from the former k0s Helm-deployer configuration. The current
storage milestone is checked separately with tests/validate_storage.py. Reports are ignored local
development data and are not release prerequisites.

Shared catalog linters use commit-pinned references with digest-pinned images.
Local Go Docker actions are still a bootstrap bridge pending their own publication.
They remain AMD64-only; hosted execution has not been observed and no push is authorized.

The umbrella's intended OCI location is
`oci://ghcr.io/tdesaules-devoteam/ai-inference-basics/charts/ai-inference-basics`.
Until publication, task up packages it locally and k0s deploys the verified .tgz.
Publication automation preserves qualified bytes and verifies a digest-addressed pull.
It must not be confused with successful runtime qualification.
