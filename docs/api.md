# Model APIs

The shared HTTPS Gateway serves the browser and model APIs. Browser sessions and
model API credentials are independent: APIs require `Authorization: Bearer <key>`.

| Endpoint | Model name and namespace |
| --- | --- |
| `POST /v1/chat/completions` | `qwen3-0-6b` |
| `POST /v1/embeddings` | `qwen3-embedding-0-6b` |
| `POST /cohere/v2/rerank` | `qwen3-reranker-0-6b` |

All three use KServe `InferenceService` and vLLM CPU. They start stopped to avoid
inference CPU/RAM usage. Activate the desired release with `LAB_MODEL_REPLICAS=1`
as described in [lab operations](lab.md); incoming requests do not wake it up.

The admin bastion has `OPENAI_BASE_URL`, `OPENAI_API_KEY` and CA trust configured.
Outside the cluster, use the native VM hostname on port 30443 and the public lab
CA. The API key is stored in `gateway/lab-api-key`; do not put it in Git or logs.
