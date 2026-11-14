# Bound CPU model startup work

## Context

On the 12-vCPU / 32-GiB development VM, concurrent cold imports produced RustFS
UploadPart 503 responses and slow object reads. Model Deployments eventually
became Ready, but the bootstrap had already failed on Kubernetes' default
Deployment progress deadline. Because model releases shared an early Helmfile
group with administration prerequisites, that failure also prevented Dex and
oauth2-proxy from being installed.

## Decision

- Install the authenticated administration interfaces before model releases.
- Order enabled model releases sequentially through Helmfile dependencies. A
  disabled release does not become a dependency of an enabled release.
- Limit each verified model upload to two concurrent 32-MiB multipart requests
  and use adaptive retries for transient S3 failures. Preserve hash verification
  and reuse existing immutable objects.
- Check the current Deployment generation and all replica counters instead of
  treating ProgressDeadlineExceeded as an immediate, permanent startup failure.
  Keep the enclosing Helmfile timeout and final KServe Ready/UpToDate checks.

## Qualification

A complete bootstrap rerun succeeded against the existing snapshots. All four
InferenceServices and browser workloads became Ready; browser, API, multimodal
and shared-bucket access checks passed. Credential values and PVC identities
were preserved. A regression test rejects stale generations and old/incomplete
rollouts even when a previous replica is available.

The VM was not destroyed to repeat the cold import. These results establish
recovery and warm-bootstrap behavior, not a new full cold-start benchmark.

The Scaleway sample uses the exported CUDA image manifest, but its machine
resources are illustrative input values rather than a provisioned Scaleway SKU.
GPU execution still requires qualification on the target hardware.
