# Troubleshooting

- **KCL 0.13.3 rejects external file probes:** initialize the pinned submodule
  revision, which includes the upstream host-file access correction. No local
  KCL override or runtime patch is needed. `task ssh` connects directly using the
  persisted VM identity without evaluating KCL.
- **VM startup fails:** use the original devenv dependency/network diagnostics.
  The host must already provide KVM, br-qemu, bridge-helper permissions and mDNS.
- **Provisioning fails:** `task ssh`, then inspect the journals for
  install-system-pkgs, run-topgrade and ai-inference-basics-bootstrap.
- **Wrong workspace:** config.k overrides only the workspace fsdev path so the
  shared directory is the repository root despite the include running in .devenv.
- **Charts do not converge:** inspect `kubectl get charts -n kube-system -o yaml`,
  controller readiness and webhook certificates. k0s owns Helm reconciliation.
- **Browser fails:** use the VM hostname printed by up, check bridge/mDNS and trust
  the guest's self-signed certificate. Do not add a host tunnel as a workaround.
- **Preview 502:** start the canonical port-forward in the matching bastion.

This version is rebuilt with down/up. Do not manually uninstall the four related
releases as a substitute for destroying the disposable VM.
