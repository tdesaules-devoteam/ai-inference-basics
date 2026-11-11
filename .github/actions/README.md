# Dedicated CI operations

Each directory owns a fixed-operation Go executable, action metadata and multistage
Containerfile. `Dockerfile` is a symlink for GitHub's local Docker-action builder.
These are bootstrap sources; digest-pinned released action images are pending GHCR
publication. They are not a general command dispatcher.

| Action | Input | Output / failure contract |
| --- | --- | --- |
| check | Event/ref, Git history | Selected build/test flags and literal JSON file lists; rejects wrong manual ref/missing history |
| lint-helm | Source chart and profiles | Dependency integrity, schema/lint, image pins and resource names |
| build-helm | Source chart | Exact `dist/*.tgz` plus SHA256SUMS |
| test-helm | Candidate archive/checksum | Render-qualified receipt; corrupt or missing candidates fail |
| fetch-helm | Tracked immutable publication receipt and tag | Original published bytes; never rebuilds |
| publish-helm | Qualified archive, source SHA and token via environment | GHCR push/pull byte verification and OCI receipt; refuses version replacement |

Build locally with `podman build --format docker -t localhost/ai-inference-basics-ci-<operation>:dev
.github/actions/<operation>`. Run `.github/scripts/test-actions.py` after all images
exist. The test covers exact artifact integrity, schema failures and refusal of
unqualified publication; it does not publish or claim hosted execution.
