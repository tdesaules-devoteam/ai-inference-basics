# Release notes

## Unreleased: domain-oriented CPU lab

- Five application charts: one gateway/TLS domain, one shared admin bastion and
  one chart/namespace per Qwen3 model.
- Sixteen Helmfile releases, direct pinned upstream charts and domain-owned Jobs.
- One Dex admin identity; bastion and Headlamp have cluster-admin privileges.
- Hugging Face Python downloads with revision/hash locks and prefix-scoped S3 access.
- Models start automatically with one replica; an explicit override can stop selected models.
- Native ttyd/Zellij CLI and code-server share one PVC and one browser login.
- Bastion image distribution remains local pending registry authorization.

## Historical umbrella layout (superseded)

- Local-only, disposable devenv workflow with public up/down/ssh commands.
- Native provisioning through config.k using the upstream extension mechanisms.
- k0s configuration owns four ordered installations of one local umbrella archive.
- Administration image moved to oci/bastion; Zellij web retains its native token login.
- Cloud code and profiles removed; cloud-init/terraform directories remain empty locally.
- Reports retained as ignored development data, not tracked release inputs.
- No VM execution or hosted publication claimed for this revision.
