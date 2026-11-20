# Release notes

## Unreleased: domain-oriented CPU lab

- Three active Qwen models per environment, with separate charts and namespaces.
- Thirty declared Helmfile releases, direct pinned upstream charts and domain-owned Jobs.
- Authenticated Grafana, Loki, Tempo, Mimir and two OpenTelemetry Collectors.
- One Dex admin identity; bastion and Headlamp have cluster-admin privileges.
- Hugging Face Python downloads with revision/hash locks and a shared models-bucket account.
- The environment selects installed models, imports and zero or one inference replica.
- Native ttyd/Zellij CLI and code-server share one PVC and one browser login.
- Bastion and provision image distribution remains local pending registry authorization.

## Historical umbrella layout (superseded)

- Local-only, disposable devenv workflow with public up/down/ssh commands.
- Native provisioning through config.k using the upstream extension mechanisms.
- k0s configuration owns four ordered installations of one local umbrella archive.
- Administration image moved to oci/bastion; Zellij web retains its native token login.
- Cloud code and profiles removed; cloud-init/terraform directories remain empty locally.
- Reports retained as ignored development data, not tracked release inputs.
- No VM execution or hosted publication claimed for this revision.
