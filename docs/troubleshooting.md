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

## Ordered Helm teardown

A raw uninstall of the initial chart timed out because KServe and Agent Router
controllers disappeared before their custom resources completed finalization.
`reports/archive/pre-rename/local-cpu/G3/lifecycle-failure.json` records the failure. The corrected
chart includes a pre-delete Job using digest-pinned kubectl and a narrowly scoped
Role. It removes the known AI route/backends, model resources/preset and Gateway
before Helm removes their controllers and CRDs.

KServe 0.21 also deliberately rejects deletion of well-known LLM presets. After
draining the model resources, the hook removes only the named
`llminferenceserviceconfig.serving.kserve.io` validator, then deletes the preset.
Its ClusterRole permits deletion of that one validator only. This is an explicit
teardown step, not a runtime admission bypass or forced finalizer removal.

For an interrupted old uninstall, restore foundation first, then CRDs, then
controllers from the same locked umbrella so finalizers can finish. Do not delete
Helm Secrets or strip finalizers blindly. Third-party CRs created outside the lab
contract require their own cleanup before removing the controllers.
