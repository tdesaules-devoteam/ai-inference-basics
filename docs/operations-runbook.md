# Operations runbook

See the tracker for which commands are implemented and validated. The intended
operator interface is Task, including Terraform plan/apply/destroy.

| Command | Responsibility |
| --- | --- |
| `task doctor` | Host and profile preflight |
| `task infra:up` | Local devenv lifecycle or explicit cloud plan/apply |
| `task k0s:install` | Pinned native controller+worker bootstrap |
| `task bootstrap:access` | Gateway, Dex, oauth2-proxy and browser tools |
| `task helm:deps` | Retrieve and verify locked chart artifacts |
| `task platform:up` | Ordered CRD/controller/resource/model phases |
| `task models:verify` | Three model APIs, auth and cache |
| `task auth:verify` | Dex and browser sessions |
| `task preview:verify` | In-Pod port-forward and Caddy |
| `task observability:verify` | Actual metrics/logs/traces |
| `task gpu:verify` | H100 runtime, HAMi and DCGM |
| `task verify` | Applicable end-to-end acceptance |
| `task up` | Full supported sequence |
| `task down` | Controlled shutdown |
| `task infra:destroy` | Explicit destructive disposal |
| `task versions:check` | Dependency integrity |
| `task report` | Sanitized status/evidence |

Pass `PROFILE=local-cpu`, `scaleway-cpu-pilot` or `scaleway-h100` as appropriate.
Local routine shutdown preserves disk and identity; disposal destroys guest data.

## Browser preview

Inside a participant terminal, run:

```sh
kubectl -n demo port-forward --address 127.0.0.1 svc/whoami 18080:80
```

Caddy in the same Pod proxies `:8080` to `127.0.0.1:18080`. Browser localhost is
not involved. Preview returns 502 when no forward runs. Use a dedicated hostname
and the same OAuth protection as the terminal. Only fixed HTTP/WebSocket ports.

## Recovery

Keep instructor SSH/provider console available. Diagnose native k0s with systemd
and its embedded kubectl/containerd. Inspect CRDs/webhooks before retrying Helm.
Do not delete Helm release Secrets or replace immutable selectors blindly. A broken
browser gateway must be recoverable from the host; never add a host web IDE.
