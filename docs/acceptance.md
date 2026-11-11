# Acceptance

Offline checks cover the k0s YAML, ordered chart rendering, archive checksums,
image pins, cross-release ownership and the config.k/Butane rendering contract.
They do not start a VM.

After explicit operator authorization, qualify a fresh `task up`:

- Fedora CoreOS resource sizing, CPU flags and correct repository workspace share.
- Normal devenv provisioning completes; native k0s and instructor tools are usable.
- Four k0s Helm Chart resources reconcile in order from the local archive.
- Browser access works directly through the VM hostname, without a host tunnel.
- Two Dex accounts and independent Zellij tokens work; unauthorized access fails.
- Chat JSON/SSE, embedding dimension/repeatability and reranker relevance pass.
- Bearer-key enforcement, NetworkPolicies and prefix-cache behavior are verified.
- Metrics, logs and correlated traces are retrievable through OpenTelemetry.
- `task down` destroys the VM; another `task up` rebuilds the lab from scratch.

Development evidence may be written to ignored reports/. No cloud or GPU acceptance
is claimed for this local CPU revision.
