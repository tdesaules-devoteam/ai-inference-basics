# Native model context windows

Both environments use the native context documented by Qwen for each pinned model.
Helmfile reads `nativeContextTokens` from the model chart and passes it as
`maxModelLen`. There is no environment divisor or implicit RoPE/YaRN extension.
The model card defines the serving window. Five of the six pinned `config.json`
files declare 40,960 positional slots; that larger value is not the published
32K serving window. Only the 0.6B embedder declares 32,768 in both places.

| Model | Maximum context in either environment |
| --- | ---: |
| [qwen3-0-6b](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/README.md) | 32768 |
| [qwen3-embedding-0-6b](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B/blob/97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3/README.md) | 32768 |
| [qwen3-reranker-0-6b](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B/blob/e61197ed45024b0ed8a2d74b80b4d909f1255473/README.md) | 32768 |
| [qwen3-8b-fp8](https://huggingface.co/Qwen/Qwen3-8B-FP8/blob/220b46e3b2180893580a4454f21f22d3ebb187d3/README.md) | 32768 |
| [qwen3-embedding-4b](https://huggingface.co/Qwen/Qwen3-Embedding-4B/blob/5cf2132abc99cad020ac570b19d031efec650f2b/README.md) | 32768 |
| [qwen3-reranker-4b](https://huggingface.co/Qwen/Qwen3-Reranker-4B/blob/22e683669bc0f0bd69640a1354a6d0aebcfeede5/README.md) | 32768 |

Generation context includes the tokenized prompt and requested output budget.
vLLM receives `--max-model-len`. Embedding/reranking context
applies to each input or query/document pair.

For CPU chat, the 32,768-token window needs about 3.5 GiB of BF16 KV data
(28 layers, 8 KV heads, 128 head dimensions, two K/V tensors). Reserve 5 GiB
instead of the former 1 GiB, which exposed only 9,344 cache tokens at runtime.
The container memory limit is 12 GiB to include weights and runtime overhead.
The installed vLLM CPU pooling runners also allocate KV cache for these decoder
models: embeddings reserve 4 GiB (at least 3.5 GiB required) and reranking reserves
5 GiB. Their container memory limits are 10 and 12 GiB respectively. All caches
remain BF16. The devenv definition therefore targets 48 GiB of RAM.

These are context ceilings, not throughput or memory guarantees for concurrent
full-window requests. Resource sizing must also accommodate the other loaded
models and observability. No load benchmark was requested; GPU behavior remains
subject to later H100 qualification.
