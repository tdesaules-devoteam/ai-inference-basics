# Observability and prefix caching

OpenTelemetry Collector is the common collection/export layer, not a storage
backend. Configure OTLP receivers for traces and instrumented metrics/logs,
Prometheus receivers for existing exporters, and filelog collection for Pod logs.
Use memory limiting, batching, bounded queues and CPU-sized retention/resources.

| Signal | Backend | Required evidence |
| --- | --- | --- |
| Metrics | Prometheus | Actual vLLM and Envoy series queried |
| Logs | Loki | Actual Pod log retrieved |
| Traces | Tempo | OTLP trace retrieved by trace ID |
| Dashboards | Grafana | Authenticated browser navigation |

Track readiness, CPU/RAM, request rates/errors, TTFT, token generation and cache
metrics that the pinned versions actually export. Document propagation gaps;
collecting metrics does not prove traces exist. Instrument the three model calls
where supported; synthetic trace fixtures are not model end-to-end trace evidence.

## Automatic prefix caching

Enable vLLM automatic prefix caching explicitly for chat. Test a shared long prefix
with short outputs: capture cold/warm TTFT, errors and cache counters over repeated
requests. CPU support and metric names must be checked against the selected version.
The KV cache is local to each replica; standard balancing does not provide
cache-aware affinity. It is neither response caching nor an embedding cache.

## GPU

Standalone DCGM Exporter runs on H100 only and is scraped by OTel. Measure physical
GPU memory/utilization separately from HAMi virtual allocation. Prepare exporter
configuration and dashboards locally and exercise fixtures if useful, but do not
claim hardware validation without an NVIDIA GPU. Test two users for at least five
rounds, all four model Pods simultaneously Ready, no OOM, and chat continuity after
one replica is lost. Recovery does not promise preservation of an in-flight stream.
