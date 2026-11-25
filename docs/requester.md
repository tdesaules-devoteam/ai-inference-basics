# Browser HTTP requester

Open `/requester/` on the **web** origin (port 30443 in the CPU sample). The same
Dex session used by the terminal and code-server protects the UI, its JavaScript
bundle and the OpenAPI collection. Scalar is served locally from its official
pinned image; no hosted Scalar proxy or account is needed.

1. Select **Chat completion**, **Generate embeddings** or **Rank documents**.
2. Click **Test Request** to open the embedded API client. Edit the JSON body or
   headers. Chat also offers a streaming example.
3. Enter the lab model API key in the **Bearer Token** field (the key only,
   without the `Bearer ` prefix), then click **Send**. Read the HTTP status and
   response in the client. Without the key, a model request returns 401 even
   after Dex login. The key is not embedded in the collection or persisted by
   the UI. To retrieve it privately: `task lab:access | jq -r '.api_key'`.

The sample collection uses enabled model names from the environment definition.
Requests go directly from the browser to the configured API origin (30444 on
devenv); trust the lab CA in the browser for both listeners. Agentgateway allows
the web origin to send an explicit Authorization header. The requester is scoped
to the lab API, not a general-purpose server-side proxy for arbitrary URLs.
