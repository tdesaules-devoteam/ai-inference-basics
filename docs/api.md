# Model API

Use `https://<vm-hostname>:30443` and an independent static Bearer API key from the
guest's `/var/lib/ai-inference-basics/credentials.json`. Browser cookies do not
authenticate inference calls. Never put the key in source, URLs or shell tracing.

| Endpoint | Model alias |
| --- | --- |
| POST /v1/chat/completions | ai-inference-basics-chat |
| POST /v1/embeddings | ai-inference-basics-embeddings |
| POST /cohere/v2/rerank | ai-inference-basics-rerank |

The CPU checkpoints are the official Qwen3 0.6B chat, embedding and reranker models,
pinned by Hugging Face revision. Agent Router's rerank interface is Cohere-compatible.
Chat is managed by LLMInferenceService without EPP; pooling models use InferenceService.
Direct model Services are not the public client interface.
