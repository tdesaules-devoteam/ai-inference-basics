# Model API

All requests go through the same HTTPS Envoy listener and require an independent
static Bearer key. Browser cookies are not accepted as API credentials. The key is
generated per lab and kept in `.local/secrets/credentials.json` and the Kubernetes
`ai-inference-basics-api-key` Secret. Do not place it in URLs, source or shell tracing output.

| API | Model alias | Local checkpoint |
| --- | --- | --- |
| `POST /v1/chat/completions` | `ai-inference-basics-chat` | Qwen3-0.6B |
| `POST /v1/embeddings` | `ai-inference-basics-embeddings` | Qwen3-Embedding-0.6B |
| `POST /cohere/v2/rerank` | `ai-inference-basics-rerank` | Qwen3-Reranker-0.6B |

The rerank path is Agent Router's Cohere-compatible API, forwarded to vLLM's
`/v2/rerank`. It returns scored candidate indexes; no unrelated model or custom
inference adapter replaces the official checkpoint.

`task models:verify` checks missing/incorrect keys (401), chat JSON, valid SSE with
`[DONE]`, 1024-dimensional repeatable embeddings and relevance ordering. It also
measures prefix-cache counters and first-content timing. `task lab:limit-requests`
enables a one-request-per-minute local rate limit to demonstrate 429;
`task lab:restore` removes it.

Model Services remain ClusterIP. NetworkPolicies allow model ingress only from
the Envoy data plane and telemetry collector. Normal administration workspaces
cannot bypass the gateway to call models directly. The controller-owned
LLMInferenceService does not need its own public URL: Agent Router owns that route.
