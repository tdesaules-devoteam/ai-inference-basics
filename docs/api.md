# Model APIs

In devenv, agentgateway exposes the model APIs on their own HTTP listener. Envoy serves browser traffic only. Browser sessions and
model API credentials are independent: APIs require `Authorization: Bearer <key>`.

| Endpoint | CPU sample model name and namespace |
| --- | --- |
| `POST /v1/chat/completions` | `qwen3-0-6b` |
| `POST /v1/responses` | `qwen3-0-6b` |
| `POST /v1/embeddings` | `qwen3-embedding-0-6b` |
| `POST /v2/rerank` | `qwen3-reranker-0-6b` |
| `POST /score` | `qwen3-reranker-0-6b` (pairwise score) |
| `GET /v1/models` | Configured active models (`enabled` and one desired replica), not a readiness probe |
| `GET /openapi.json` | Public specification for Scalar and API clients |

Agentgateway restricts paths and methods; vLLM validates inference payloads. The
specification endpoint is the only unauthenticated GET. The legacy Completions API
is not published. Responses creation supports streaming; stored response lookup
and cancellation are not exposed. The `platform/helmfile/openapi` fragments come
from the pinned CPU predictors, not from a union of every vLLM endpoint. On an
upgrade, fetch `/openapi.json` from each predictor after verifying `/version`,
then run `python3 platform/helmfile/scripts/model-contract.py extract TASK FILE`
for `chat`, `embeddings` and `rerank`. Review the changes before reconciling.

The CPU sample uses KServe `InferenceService` and vLLM CPU for all three.
For reranking, both `/score` and `/v2/rerank` use the publisher's
`/mnt/models/chat_template.jinja` explicitly. The template formats each query/document
pair before vLLM scores the `yes` and `no` tokens. The CPU acceptance test compares
both operations against the pinned Qwen checkpoint's Transformers reference on
two matching and two unrelated pairs. Matching the order alone is insufficient:
without the scoring template, unrelated pairs also received high scores.
For the GPU sample, use the [corresponding GPU model names](gpu.md#environment-selection). They start automatically
according to the environment JSON. Setting a model's `replicas` to zero stops selected
models as described in [lab operations](lab.md); requests do not wake stopped models.

The admin bastion has `OPENAI_BASE_URL` and `OPENAI_API_KEY` configured.
Outside the cluster, use the native VM hostname over HTTP on port 30444. The API key is stored in `gateway/lab-api-key`; do not put it in Git or logs.

## Requests from the bastion terminal

The terminal already provides `OPENAI_API_KEY` and `OPENAI_BASE_URL`. Derive the shared origin once:

```sh
BASE_URL="${OPENAI_BASE_URL%/v1}"
```

### Chat

```sh
curl --fail-with-body -sS "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-0-6b",
    "messages": [{"role": "user", "content": "Explain Kubernetes in one sentence."}],
    "max_tokens": 128,
    "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": false}
  }' | jq
```

### Streaming chat (SSE)

```sh
curl --fail-with-body -sS -N "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-0-6b",
    "messages": [{"role": "user", "content": "Explain Kubernetes in one sentence."}],
    "max_tokens": 128,
    "stream": true,
    "chat_template_kwargs": {"enable_thinking": false}
  }'
```

Expect incremental `data:` events ending with `data: [DONE]`.

### Embeddings

```sh
curl --fail-with-body -sS "$BASE_URL/v1/embeddings" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-embedding-0-6b",
    "input": ["Kubernetes manages containers.", "Paris is the capital of France."]
  }' | jq '.data[] | {index, dimensions: (.embedding | length), preview: .embedding[0:5]}'
```

Expect two vectors of 1024 dimensions. The jq filter displays only their first
five values; the API response contains the complete vectors.

### Reranking

```sh
curl --fail-with-body -sS "$BASE_URL/v2/rerank" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-reranker-0-6b",
    "query": "What is the capital of France?",
    "documents": ["Paris is the capital of France.", "Berlin is in Germany."],
    "top_n": 2
  }' | jq
```

Expect document index 0 to be ranked first.

### Missing API key

```sh
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE_URL/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-0-6b","messages":[{"role":"user","content":"Hello"}],"max_tokens":1}'
```

Expect `401`, including when a browser session is authenticated.

## Requests from the workstation

Run from the repository root. These commands retrieve the API key without printing it:

```sh
VM_HOST="$(cat .devenv/.uuid).local"
VM="$(id -un)@$VM_HOST"
BASE_URL="http://$VM_HOST:30444"
OPENAI_API_KEY="$(ssh "$VM" 'kubectl -n gateway get secret lab-api-key -o jsonpath="{.data.lab}" | base64 -d')"
```

Then use the same requests above. Afterward, `unset OPENAI_API_KEY`.
