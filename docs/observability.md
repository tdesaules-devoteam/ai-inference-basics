# Observability

The umbrella includes digest-pinned otel-lgtm with an OpenTelemetry Collector,
Prometheus, Loki, Tempo and Grafana. The Collector scrapes Envoy Gateway/vLLM,
collects Pod logs and accepts OTLP traces. Grafana is behind Dex/oauth2-proxy.

Chat explicitly enables vLLM prefix caching. Verify repeated-prefix cache counters
and first-content latency during runtime qualification; caches are per replica,
not shared response caches. No cache-aware llm-d routing is installed.

The local telemetry Pod has bounded memory and an ephemeral data volume. Its data
is disposable. The optional upstream GPU dependencies are disabled in this CPU lab;
no DCGM hardware results are claimed without NVIDIA hardware.
