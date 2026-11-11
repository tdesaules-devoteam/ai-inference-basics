# H100 preparation (not hardware-qualified)

The H100 profile locks the official FP8 8B chat checkpoint (two replicas), BF16 4B
embedding/reranker, vLLM GPU image, HAMi 2.11.0 and DCGM Exporter 4.9.0. GPU charts
remain disabled by default; local static checks explicitly render them. No GPU
Operator or separate NVIDIA device plugin is installed.

After CPU cloud teardown acceptance, resolve the GPU OS 13 local image UUID and
one H100-1-80G allocation in fr-par-2. Preserve a 128-GB SBS 5K boot disk. Verify
driver/CUDA compatibility and install the selected NVIDIA Container Toolkit 1.20.1
from its official package repository, recording the actual package version.

`infra/cloud-init/configure-nvidia-k0s.sh` checks the pinned runtime and prepares
`/etc/k0s/containerd.d/nvidia.toml`; k0s uses `/run/k0s/containerd.sock`. It does not
configure a separate system containerd, replace existing settings or install a
GPU Operator. The script is prepared but cannot be hardware-qualified on this CPU VM.

Next gates: inspect k0s's merged runtime config, create the nvidia RuntimeClass,
run a digest-pinned diagnostic CUDA Pod, then enable HAMi and label the single
GPU node `gpu=on`. HAMi must be the only NVIDIA device plugin. Enable standalone
DCGM and verify its physical counters through the existing OTel receiver.

Initial HAMi limits are 20480 MiB per chat replica and 13312 MiB per pooling model,
with core shares 30/30/20/20. These are starting budgets, not measured allocations.
vLLM uses explicit memory/concurrency limits and no additional FP8 conversion.
Measure OOM/graph-capture behavior and leave driver headroom. The CPU's 0.5 memory
utilization adjustment is distinct from the proposed GPU setting.

Hardware/runtime readiness, two-user concurrency, DCGM data, replica-failure
continuity, external TTL and actual teardown remain unvalidated until the pilot.
