# Implementation status

## Current local-only revision

- [x] Public Task interface reduced to up/down/ssh; functions delegated internally.
- [x] Direct inclusion of the upstream devenv Taskfile; temporary patch removed.
- [x] Only local config.k adapted within .devenv, preserving normal units/defaults.
- [x] Reverted the local KCL download and Taskfile PATH override at the user's request.
- [x] Import the upstream KCL correction and verify configuration/Butane rendering with KCL 0.13.3.
- [x] Inherit the runtime's CoreOS 44 stable image and declare hardware directly in config.k.
- [x] Restore task ssh without KCL evaluation; a connection to the existing VM succeeded.
- [x] OCI sources moved to oci/bastion; obsolete cloud/profile/wrapper code removed.
- [x] infra/k0s/k0s.yaml defines the ordered local Helm-deployer configuration.
- [x] Prepare final k0s.yaml and credentials on the host; copy them directly through Ignition.
- [x] Install checksum-verified k0s inline in the systemd unit; remove guest bootstrap scripts.
- [x] Preserve the requested 24 vCPU / 48 GiB / 64 GiB sizing and Beszel configuration.
- [x] Reports retained locally and removed from Git tracking.
- [ ] Boot and qualify this revised provisioning flow with operator authorization.
- [ ] Verify native Helm-deployer convergence across controller/CRD dependencies;
  the selected k0s implementation does not enforce the documented ordering fields.
- [ ] Validate native hostname browser access and the complete functional journey.
- [ ] Observe hosted CI and publish the chart (no source push authorized).

Earlier runtime evidence describes the former orchestration, not this revision.
Local development reports are ignored and are never a prerequisite for CI or startup.
