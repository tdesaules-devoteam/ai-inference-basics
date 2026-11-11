# Repository contract

- Source, documentation, comments and commits are English.
- Use the devenv, helm, container and github-actions skills for their respective work.
- Native k0s controller+worker only; no nested Kubernetes in Docker/Podman.
- Local VM uses `.devenv`, Fedora CoreOS, 12 CPUs, 32 GiB RAM and 64 GiB disk.
- Keep local `.devenv/config.k`, identity and credentials untracked and preserve them.
- Dex with two email-based accounts and oauth2-proxy protects browser tools.
- Administration workspaces use Fedora Minimal and Zellij's native web client,
  with a separate native login token per workspace; ttyd is superseded.
- Model APIs require a separate static Bearer key enforced at Envoy Gateway.
- No Google, Keycloak, llm-d, EPP, game app or RAG application in this MVP.
- Chat uses LLMInferenceService; embeddings/reranker use InferenceService.
  Prove no-EPP compatibility before declaring inference ready; do not silently
  replace the requested resource types.
- One Helm umbrella contract, staged for CRD/webhook readiness. Lock every image
  by digest and every dependency archive by checksum/OCI digest.
- User-approved exception: official upstream application images may use bases
  outside the container skill allowlist, with provenance and digest recorded.
  Project-owned builds must still use allowed bases in every stage.
- Publish the umbrella to this repository's GHCR namespace; record its real digest.
- Terraform operations run through Task; show the saved plan before apply.
- CPU cloud acceptance and teardown gate H100; one H100 gates the training fleet.
- Record exact commands, versions, sanitized results and outstanding issues in
  reports and docs/implementation-tracker.md. Never check off unexecuted acceptance.
- Commit logical units locally with Conventional Commits and a why-body.
  Do not push source changes without explicit authorization.
