# Scaleway pilot preparation

Terraform 1.17.2 / Scaleway provider 2.91.0 is the initial validated schema baseline.
No cloud apply is authorized implicitly by local work. Native k0s bootstrap shares
the local binary checksum and Linux image pins. DNS, trusted TLS, platform chart
installation, secret distribution and GPU runtime remain additional cloud gates.

Use `.local/terraform/<session>/inputs.tfvars.json` with protected permissions.
Required inputs: project_id, training_session_id, session_started_at (fixed RFC3339),
image_id (resolved local UUID), authorized_ssh_cidrs, authorized_https_cidrs,
base_domain and ssh_public_key. Defaults select one CPU pilot, 128-GB SBS 5K boot
volume and eight-hour TTL. Verify live type/zone availability before planning.

```sh
task infra:plan PROFILE=scaleway-cpu-pilot SESSION=cpu-pilot-001
task infra:up PROFILE=scaleway-cpu-pilot SESSION=cpu-pilot-001
task infra:destroy PROFILE=scaleway-cpu-pilot SESSION=cpu-pilot-001
```

The wrapper uses separate local state/data directories per session and applies a
saved plan after displaying it. State is local for the initial operator pilot;
a protected remote backend and external TTL controller are required before training.
Expiry tags and Terraform preconditions do not themselves destroy a running VM.

The boot volume is managed through the verified instance root_volume SBS schema,
with delete_on_termination=true. Public IPs and security groups are explicit tracked
resources; only instructor SSH and permitted HTTPS CIDRs are admitted. No 6443 rule.
Cloud-init contains only public SSH material and pinned bootstrap configuration,
not Dex passwords, cookie secrets or the inference key.

The supplied cloud-init currently bootstraps k0s only. Do not consider a successful
apply a ready lab. Cloud runtime, re-apply, DNS/TLS, cleanup audit, GPU OS 13 selection,
NVIDIA containerd integration and external TTL have not yet been qualified.
