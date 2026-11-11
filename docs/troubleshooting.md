# Troubleshooting

| Symptom | First investigation |
| --- | --- |
| VM cannot launch | KVM, QEMU, sudo permission, bridge-helper and br-qemu |
| Render fails | KCL version/module filesystem access and consistent arguments |
| Wrong guest workspace | Explicit project root versus runtime Task working directory |
| SSH fails | Serial log, persisted UUID, bridge DHCP/mDNS, authorized public key |
| Guest provisioning fails | install-system-pkgs/run-topgrade journal and staged reboot |
| k0s not Ready | k0scontroller journal, CNI, CoreDNS, disk and node conditions |
| OAuth loop | Issuer, callback, DNS, CA trust, cookies and /oauth2/auth semantics |
| Preview 502 | Port-forward process and fixed in-Pod localhost port |
| Model fails | CPU flags, image architecture, pooling adapter, memory and HF revision |
| Missing traces | Actual instrumentation/OTLP export, then Collector and Tempo |
| GPU OOM | Physical versus HAMi budgets, KV/concurrency, CUDA graph overhead |

Record exact failures and the smallest reproducible workaround. Do not mark a
milestone complete after rendering only. Preserve sanitized failure evidence.
