# Repository contract

- Source, documentation, comments and commits are English.
- Use devenv, helm, container and github-actions skills for their respective work.
- This version is a disposable local CPU lab. Include native tasks as task devenv:*.
- Include the upstream devenv Taskfile directly. Within `.devenv`, edit only the
  ignored, user-owned config.k, starting from exemple.config.k. Keep identity and
  other local runtime state intact. No runtime patches or lifecycle wrappers.
- Use custom_pkgs/custom_mise_tools/custom_files/custom_copies and append units.
  Do not replace normal provisioning units with no-ops.
- Keep platform/k0s/k0s.yaml. platform/cloud-init and platform/terraform are empty placeholders.
- Keep Helmfile orchestration and upstream chart values in platform/helmfile,
  with readiness checks in platform/helmfile/scripts. Keep the shared environment
  values adapter in infra/helmfile/lab.yaml.gotmpl, project-authored charts
  (including dedicated configuration charts) in charts, and systemd units in
  platform/units.
- Describe the desired infrastructure in a schema-validated environment JSON.
  Track the schema and a sample with placeholder credentials; keep real
  environment definitions containing credentials untracked. Helmfile values
  adapt this definition rather than maintaining competing environment defaults.
- Keep one resource declaration per chart template, using kebab-case kind filenames
  (for example cluster-role.yaml). Add a purpose suffix for distinct resources of
  the same kind; loops may instantiate that resource for participants or models.
- Use block-style YAML mappings and sequences in charts rather than inline flow
  collections, except empty collections and literal JSON application arguments.
- Install k0s, Helm, Helmfile, kubectl, k9s and curl through separate units. Generate
  user kubeconfigs through `platform-kubeconfig@.service`, preserving existing files.
  Keep provisioning logic inline in focused units, coordinated by
  platform-k0s-bootstrap.service; do not add external provisioning shell scripts.
- Preserve the native k0scontroller.service; platform-k0s-controller.service is its alias.
- Helmfile fetches charts directly from upstream repositories: pin official OCI
  charts by manifest digest, or exact versions for HTTP-only repositories. Verify
  the qualified HTTP archive checksum in tests; do not add a chart downloader unit.
- No profiles directory. Reports are development-local and must remain untracked.
- Build the administration image in oci/bastion, using Fedora Minimal, ttyd and Zellij CLI.
- Native k0s controller+worker; never nested Kubernetes in Docker/Podman.
- Helmfile owns platform releases, with explicit needs and readiness checks. Do not
  install the same releases with the k0s Helm deployer or another reconciler.
  Use upstream charts and a namespace per component; verify downloaded artifact bytes.
- Dex and oauth2-proxy authenticate browser access, including ttyd with Zellij CLI.
  Model APIs use a separate static Bearer key enforced at Envoy Gateway.
- Chat, embeddings and reranker use InferenceService. No llm-d/EPP.
- Each model has its own chart, release, namespace and matching S3 prefix.
  The environment definition explicitly selects installed releases, imports and
  zero or one inference replica; zero uses KServe's supported stopped state.
- One shared admin account uses the bastion workspace and Headlamp, both with
  cluster-admin access. No per-participant workspaces or namespaces.
- Use upstream chart settings and native extraObjects/extraManifests extension
  points first. When an upstream chart cannot express a required resource, use
  a focused project-authored chart in charts, ordered explicitly by Helmfile
  needs. Configuration releases may share their component's namespace. Do not
  use a custom post-renderer, Helm plugin, or placeholder-substitution layer.
- Domain initialization Jobs create missing technical credentials using a
  cryptographic generator and preserve existing values. A Dex configuration Job
  computes the password's bcrypt hash. Kyverno owns cross-namespace Secret
  synchronization and public CA publication; cert-manager owns TLS keys and
  certificates. Keep credentials.py and kube.py removed.
- Use one shared non-admin S3 account for the models bucket, configured by a
  RustFS rc Job and distributed by Kyverno. Model S3 prefixes remain separate;
  the shared account is not granted access to the observability buckets.
- Local Path Provisioner runs in local-path-provisioner; RustFS runs in rustfs on a PVC.
- Initialize the six application buckets through RustFS extraManifests; no dedicated
  storage-bootstrap chart or benchmark-results/platform-checks buckets in new installs.
- Generate/preserve RustFS credentials in a pre-install/pre-upgrade Job with
  namespaced RBAC; initialize buckets in a post-install/post-upgrade Job.
- Observability uses separate Grafana, Loki, Tempo and Mimir deployments, with
  OpenTelemetry Collector for node, application and cluster signals.
- Pin workload images by digest. Official upstream
  images have a user-approved base-image exception; own builds use allowed bases.
- Reuse the VM's native bridge/mDNS access. No host systemd SSH tunnel.
- Do not operate the VM without explicit permission. Offline checks are not boot evidence.
- Keep changes and Conventional Commits local; do not push without authorization.
