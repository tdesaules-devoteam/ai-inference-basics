# Local lab architecture

The current lab uses native single-node k0s in a 12-vCPU, 32-GiB RAM, 64-GiB Fedora CoreOS
VM. The upstream devenv lifecycle renders KCL/Butane/Ignition; focused systemd units
install native tools and invoke Helmfile. There is no nested container cluster.

Helmfile is the only release reconciler. Infrastructure charts are fetched directly
from upstream with manifest-digest pins for OCI and exact HTTP chart versions.
Project charts own six active application domains: gateway, bastion and four models.
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
        +--> headlamp              +--> lfm3-omni-2b
                                         |
                                         | read-only S3 initialization
                                         v
                                       RustFS
```

Envoy Gateway in `envoy-gateway` is the control plane configuring the proxy in
`gateway`. KServe in `kserve` manages the model InferenceServices. TLS terminates
at the Gateway; browser application Services use internal HTTP.

One Dex account, `cluster-admin`, uses the shared workspace and Headlamp. Both Kubernetes
ServiceAccounts have cluster-admin rights. Authentication at oauth2-proxy remains
mandatory; browser cookies are not accepted as model API credentials.

Models start with one replica; KServe's stop annotation supports an explicit
zero-replica override. Imports use huggingface_hub
with pinned revisions, SHA-256 verification and boto3 uploads. Each model receives
the shared models-bucket credential through Kyverno. Stopped models need
explicit reactivation; there is no request-triggered scale-from-zero.

Credential initialization is domain-local. Native chart extensions declare Jobs
and Kyverno policies; Dex uses a separate configuration chart ordered by Helmfile.
The infrastructure JSON controls the desired state. See [lab operations](lab.md) for
ownership, access, model activation and qualification.

Caddy is a sidecar in the oauth2-proxy Pod, in namespace `oauth2-proxy`.
After authentication it routes browser paths to ttyd, code-server and Headlamp,
including code-server path rewriting. Envoy remains the external entrypoint.

The Scaleway environment substitutes larger GPU Qwen models. GPU Operator
configures Container Toolkit, HAMi handles GPU sharing, and DCGM Exporter exposes
hardware metrics. These hardware paths are unqualified on the CPU VM; see
[GPU and Omni](gpu-and-omni.md) for image boundaries and model selection.
