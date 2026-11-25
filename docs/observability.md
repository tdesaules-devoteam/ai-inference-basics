# Observability

Open `/grafana/` on the lab HTTPS origin and sign in with the shared Dex account.
In Explore select Mimir (Prometheus), Loki (logs) or Tempo (traces). Helmfile
provisions these three data sources; no dashboards are installed.

`otel-node` collects container logs, host and kubelet metrics. `otel-cluster`
collects Kubernetes events, cluster metrics, vLLM and Envoy scrapes and the
gateways' OTLP spans. Only eligible GPU nodes supply DCGM metrics. Agentgateway access logs
contain the request ID, model and token counts; these fields are not Loki
index labels. A sampling rate of 100 is intentional for this local lab.

- Mimir: query `vllm:generation_tokens_total{model="qwen3-0-6b"}`.
- Loki: query `{k8s_namespace_name="agentgateway"} | json` and filter by request ID.
- Tempo: search `{ resource.service.name = "lab-model-api" }` or a trace ID.

RustFS stores logs in `loki`, traces in `tempo`, and Mimir data in `mimir-blocks`,
`mimir-ruler` and `mimir-alertmanager`. Kyverno distributes a dedicated account
for these five buckets. The models account has no access to them. Grafana uses
a PVC for its configuration and database. Keep model prompts and credentials out
of telemetry.

`node tests/browser/qualify.mjs` exercises the authenticated browser and datasource
path. It submits a uniquely marked chat request, checks Mimir's generation token
counter, matches the reported token total in Loki and searches Tempo for the
corresponding span. See [lab access](lab.md) for qualification credentials.
