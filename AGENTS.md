# Repository contract

- Source, documentation, comments and commits are English.
- Use devenv, helm, container and github-actions skills for their respective work.
- This version is a disposable local CPU lab. Public commands: task up/down/ssh.
- Include the upstream devenv Taskfile directly. Within `.devenv`, edit only the
  ignored, user-owned config.k, starting from exemple.config.k. Keep identity and
  other local runtime state intact. No runtime patches or lifecycle wrappers.
- Use custom_pkgs/custom_mise_tools/custom_files/custom_copies and append units.
  Do not replace normal provisioning units with no-ops.
- Keep infra/k0s/k0s.yaml. infra/cloud-init and infra/terraform are empty placeholders.
- No profiles directory. Reports are development-local and must remain untracked.
- Build the administration image in oci/bastion, using Fedora Minimal and Zellij web.
- Native k0s controller+worker; never nested Kubernetes in Docker/Podman.
- The k0s Helm deployer owns installation. The same locked umbrella may be installed
  in fixed disjoint ordered releases for CRD/controller readiness. No competing Helm
  CLI orchestration. Package the unpublished chart locally and verify its bytes.
- Dex authenticates browser access. Zellij additionally requires its native token.
  Model APIs use a separate static Bearer key enforced at Envoy Gateway.
- Chat uses LLMInferenceService; embeddings/reranker use InferenceService. No llm-d/EPP.
- Pin workload images by digest and chart archives by checksum. Official upstream
  images have a user-approved base-image exception; own builds use allowed bases.
- Reuse the VM's native bridge/mDNS access. No host systemd SSH tunnel.
- Do not operate the VM without explicit permission. Offline checks are not boot evidence.
- Keep changes and Conventional Commits local; do not push without authorization.
