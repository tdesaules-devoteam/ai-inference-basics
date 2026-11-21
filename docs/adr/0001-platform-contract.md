# ADR 0001: local disposable platform

Status: historical foundation design. For the qualified runtime see the
[implementation tracker](../implementation-tracker.md).

- The first version is local-only, with up/down/ssh and the original devenv lifecycle.
- config.k extends the upstream example; no schema patches or no-op provisioning units.
- Native k0s is bootstrapped inside the VM, together with instructor CLI tools.
- The former k0s Helm-deployer configuration is superseded by Helmfile;
  platform/k0s/k0s.yaml now configures only the native cluster.
- Releases partition foundations, CRDs, controllers and applications without shared
  Helm ownership. This respects cross-controller bootstrap requirements.
- Dex/oauth2-proxy protects browser tools; the former Zellij web-token design was superseded by ttyd.
- Static Bearer keys protect inference APIs independently from browser cookies.
- KServe owns model workloads; llm-d/EPP is excluded from this course.
- OpenTelemetry collects all three signal types for the local telemetry stack.
- The VM's existing bridge/mDNS provides direct access; no host SSH tunnel is added.
- Cloud directories are empty placeholders. Profiles are removed and reports ignored.
