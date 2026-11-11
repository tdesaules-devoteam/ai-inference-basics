# Acceptance and evidence

Each completed check needs exact commands, versions/digests, sanitized logs and
results under `reports/<profile>/<milestone>/`. Include browser screenshots where
applicable, latency/cache/RAM/VRAM measurements and open issues. Never publish
credentials, kubeconfigs, raw state or private addresses in evidence.

## G0: repository and dependency contract

Documentation, ADRs, Task interface, version matrix, immutable dependency locks,
Helm schema, Terraform validation, ShellCheck, YAML/Markdown/workflow lint and CI.
Only tested versions may be labeled compatible. Registry publication has its own
evidence: artifact digest and pull verification, not just workflow syntax.

## G1: local cluster and access

VM boot, correct shared project root, CPU flags, disk/memory, native k0s Ready,
CoreDNS/service networking and reboot persistence. Browser ttyd/k9s, Helm/Task,
Headlamp navigation and Caddy fixed-port preview work. OAuth is tested with Dex
locally, including invalid account, logout, CSRF, cookies and WebSocket terminal.

## G2: inference

Requested KServe resources reconcile without llm-d/EPP. Official Qwen CPU images
and checkpoints pass chat JSON/SSE termination, embedding numeric vector with
expected dimension and reproducibility, and reranker relevance over two candidates.
Verify stable aliases, API key rejection, no backend bypass, explicit prefix caching
and cold/warm evidence. Reranker adapter/hf_overrides must be tested, not guessed.

## G3: local complete journey

Two workspace identities, preview 502 without port-forward and successful response
with it, functional Headlamp RBAC, actual metrics/logs/traces, chart upgrade/reinstall,
cleanup and bounded fault injection (429/restore). Do not stop k0s for a browser lab.

## G4: cloud CPU hard gate

Verified Scaleway types/images/provider fields and quota; saved plan applied through
Task. Same models and Dex journeys over valid TLS, private API, working break-glass,
idempotent Terraform/Helm re-apply, actual destroy and volume/IP resource audit.

## G5: one H100 hard gate

GPU OS 13, driver/toolkit configured for k0s embedded containerd, diagnostic CUDA
Pod, HAMi without duplicate plugin, DCGM collection, four vLLM Pods Ready, official
FP8 chat x2/BF16 pooling models, concurrency and replica failure tests. Destroy and
audit before recording acceptance. No eight-node fleet before this gate passes.

## G6: training readiness

Explicit eight-instance profile, 16 accounts mapped two per VM, independent secrets,
cross-lab denial, external eight-hour teardown, image/model preloading, instructor
reset/recovery runbooks and a timed two-user pilot. Release 0.3.0 only after evidence.
