# Acceptance

## Without a cluster

From the repository root, `python tests/validate.py` renders the Helmfile storage
and lab contracts with Helm, Helmfile and `requirements-dev.txt` installed. It
checks CPU, GPU and disabled model selections, pinned artifacts, model locks,
namespaces and ownership. It fetches upstream charts but does not install releases.
Run `python -m unittest discover -s tests -p 'test_*.py'` for the configuration,
credential, systemd and rollout checks; some checks require the Kyverno CLI or
systemd tools. See [CI and distribution](ci-and-distribution.md) for image tests.

## With the deployed CPU lab

| What to verify | Evidence |
| --- | --- |
| Clean boot | Native `devenv:up` succeeds; the image readiness and platform bootstrap units complete. The CPU sample selects 28 of 31 declared releases. |
| Models | Three Ready InferenceServices; CA-verified chat, SSE, embeddings and reranking succeed, and invalid Bearer keys fail. |
| Browser access | One Dex login reaches the terminal, editor, Headlamp and Grafana. The terminal and editor share the workspace PVC; browser cookies cannot authorize model requests. |
| Storage | Model reader/writer aliases use one account that can read and write across all model prefixes. It cannot access any of the five observability buckets. |
| Telemetry | A real chat request produces metrics in Mimir, token counts in Loki and a correlated gateway trace in Tempo, queried through authenticated Grafana. |
| Reconciliation | On a retained disk, technical credentials and PVC identity survive a bootstrap rerun. A deliberately stopped model stays stopped until its desired replica count changes. |

The FCOS 45 clean boot and CPU runtime checks are recorded in the
[implementation tracker](implementation-tracker.md). An offline Scaleway render
is not H100 qualification. Performance benchmarks are not an acceptance gate.
Runtime commands, private inputs and fixture prerequisites are in [lab validation](lab.md#validation).
