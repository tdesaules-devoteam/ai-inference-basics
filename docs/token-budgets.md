# Native model context windows

Both environments use the maximum native context declared by each pinned model.
Helmfile reads `nativeContextTokens` from the model chart and passes it as
`maxModelLen`. There is no environment divisor or implicit RoPE/YaRN extension.
Capacities come from config.json `max_position_embeddings`, or
`text_config.max_position_embeddings` for LFM3.

| Model | Maximum context in either environment |
| --- | ---: |
| qwen3-0-6b | 40960 |
| qwen3-embedding-0-6b | 32768 |
| qwen3-reranker-0-6b | 40960 |
| qwen3-8b-fp8 | 40960 |
| qwen3-embedding-4b | 40960 |
| qwen3-reranker-4b | 40960 |
| lfm3-omni-2b | 128000 |

Generation context includes the tokenized prompt and requested output budget.
vLLM receives `--max-model-len`; Omni receives `MAX_CONTEXT_TOKENS` and rejects
input plus requested output beyond this window. Embedding/reranking context
applies to each input or query/document pair.

Response budgets remain distinct: Omni currently permits 128 generated tokens
per request. Its text-character guard scales with the context; media byte,
duration, frame and pixel bounds remain unchanged. Audio token counts are not a
fixed duration in seconds.

For CPU chat, the 40,960-token window needs about 4.375 GiB of BF16 KV data
(28 layers, 8 KV heads, 128 head dimensions, two K/V tensors). Reserve 5 GiB
instead of the former 1 GiB, which exposed only 9,344 cache tokens at runtime.
The container memory limit is 12 GiB to include weights and runtime overhead.
Pooling runners do not use a generation KV cache.

These are context ceilings, not throughput or memory guarantees for concurrent
full-window requests. Resource sizing must also accommodate the other loaded
models and observability. No load benchmark was requested; GPU behavior remains
subject to later H100 qualification.
