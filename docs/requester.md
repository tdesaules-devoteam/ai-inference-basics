# Browser HTTP requester

Open `/scalar/` on the **web** origin (port 30443 in the CPU sample). The same
Dex session used by the terminal and code-server protects the UI, its JavaScript
bundle and font assets. Scalar is served locally from its official
pinned image; no hosted Scalar proxy or account is needed. The Nord theme uses
the same Geist Mono font as the terminal, served locally under `/scalar/`.

On devenv, Scalar fetches `GET /openapi.json` directly from the model API origin.

1. Select an operation such as `/v1/chat/completions`, `/v1/embeddings` or `/v2/rerank`.
2. Click **Test Request** to open the embedded API client. Edit the JSON body or
   headers. Chat also offers a streaming example.
3. Click **Send**. On devenv, Scalar fetches the shared admin's model key from
   `/scalar/session-token` after Dex login. The browser holds it in memory; an
   authenticated admin can inspect it. This response is not cached. The public
   OpenAPI document contains no key. Other API clients still need a Bearer key.

The sample collection uses enabled model names from the environment definition.
Requests go directly from the browser to the configured API origin (30444 on
devenv); both listeners use HTTP on the local bridge. Agentgateway allows
the web origin to send an explicit Authorization header. The requester is scoped
to the lab API, not a general-purpose server-side proxy for arbitrary URLs.
