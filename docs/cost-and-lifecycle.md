# Costs and lifecycle

Local QEMU is developer-managed. Cloud CPU must be validated and destroyed before
one H100 is provisioned. Eight H100s require a successful one-H100 pilot plus an
explicit training request, live quota/capacity checks and visible cost estimate.

Terraform operations run through Task. Separate state/workspaces by session; tag
ownership, environment, session and absolute expiry. A saved plan must display
instance type/count before apply. Re-apply must be idempotent. Destroy instances,
dedicated volumes, IPs and DNS records, then audit provider inventory independently.

Training TTL is at most eight hours and requires an external scheduler/controller.
A VM-local shutdown does not destroy billed volumes or enforce resource cleanup.
Do not use best-effort delayed CI scheduling as proof of a strict maximum lifetime.

Historical assumption only: 8 H100 × 8h × EUR2.868/h plus 8 × 128GB × 8h ×
EUR0.000130/GB/h = EUR184.62, excluding IP/network/tax, about EUR11.54 per participant.
Verify current prices and zone capacity before any booking. No snapshots/backups or
production data. GPU local NVMe is optional and its lifecycle must be discovered.
