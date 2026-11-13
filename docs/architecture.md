# Local lab architecture

The lab runs native single-node k0s in a 24-vCPU, 48-GiB RAM, 64-GiB Fedora CoreOS
VM. The upstream devenv lifecycle renders KCL/Butane/Ignition; focused systemd units
install native tools and invoke Helmfile. There is no nested container cluster.

Helmfile is the only release reconciler. Infrastructure charts are fetched directly
from upstream with manifest-digest pins for OCI and exact HTTP chart versions.
Project charts own five application domains: gateway, bastion and the three models.
Each model's chart, release, namespace and S3 prefix have the same normalized name.

```text
Browser / API client
        |
        | HTTPS :30443, native VM hostname
        v
gateway: Envoy + certificates + routes
        |                         |
        | browser                 | static Bearer API key
        v                         v
oauth2-proxy <-- OIDC --> dex      Agent Router
        |                         |
        +--> bastion              +--> qwen3-0-6b
        |    ttyd/Zellij          +--> qwen3-embedding-0-6b
        |    code-server          +--> qwen3-reranker-0-6b
        +--> headlamp                    |
                                         | read-only S3 initialization
                                         v
                                       RustFS
```

Envoy Gateway in `envoy-gateway` is the control plane configuring the proxy in
`gateway`. KServe in `kserve` manages the model InferenceServices. TLS terminates
at the Gateway; browser application Services use internal HTTP.

One Dex account, `admin`, uses the shared workspace and Headlamp. Both Kubernetes
ServiceAccounts have cluster-admin rights. Authentication at oauth2-proxy remains
mandatory; browser cookies are not accepted as model API credentials.

Models start with one replica; KServe's stop annotation supports an explicit
zero-replica override. Imports use huggingface_hub
with pinned revisions, SHA-256 verification and boto3 uploads. Each model receives
distinct reader/writer identities restricted to its S3 prefix. Stopped models need
explicit reactivation; there is no request-triggered scale-from-zero.

Credential generation is domain-local. A deterministic Helm 4 post-renderer adds
Jobs and RBAC to upstream releases where chart extension points are insufficient.
It does not run provisioning while rendering. See [lab operations](lab.md) for
ownership, access, model activation and qualification.
