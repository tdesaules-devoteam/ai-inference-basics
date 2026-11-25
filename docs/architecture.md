# Local lab architecture

The devenv definition targets native single-node k0s in a 12-vCPU, 48-GiB RAM, 64-GiB Fedora CoreOS
VM. The upstream devenv lifecycle renders KCL/Butane/Ignition; focused systemd units
install native tools and invoke Helmfile. There is no nested container cluster.

Helmfile is the only release reconciler. Infrastructure charts are fetched directly
from upstream with manifest-digest pins for OCI and exact HTTP chart versions.
Project charts own gateway, bastion, Dex configuration and the selected models.
Each model's chart, release, namespace and S3 prefix have the same normalized name.

```text
Browser → HTTPS :30443 → Envoy → Dex / oauth2-proxy → bastion, Headlamp, Grafana
API client → HTTPS :30444 → agentgateway (Bearer) → KServe predictor → vLLM
```

The two TLS listeners use separate leaf certificates issued by the local CA.
Agentgateway is not an Envoy extension. Its upstream standalone chart reads
routes generated from the enabled models in the environment definition. A
focused configuration chart owns its fixed NodePort, ingress policy and leaf
certificate distribution. The CA private key stays in `gateway`. The Scaleway
sample still uses TheAgentRouter; its two public addresses are a separate milestone.

One Dex account, `cluster-admin`, uses the shared workspace and Headlamp. Both Kubernetes
ServiceAccounts have cluster-admin rights. Authentication at oauth2-proxy remains
mandatory; browser cookies are not accepted as model API credentials.

The environment JSON selects imports and zero or one inference replica;
KServe's stop annotation implements zero. Imports use huggingface_hub
with pinned revisions, SHA-256 verification and boto3 uploads. Each model receives
the shared models-bucket credential through Kyverno. Stopped models need
explicit reactivation; there is no request-triggered scale-from-zero.

Credential initialization is domain-local. Native chart extensions declare Jobs
and Kyverno policies; Dex uses a separate configuration chart ordered by Helmfile.
The infrastructure JSON controls the desired state. See [lab operations](lab.md) for
ownership, access, model activation and qualification.

Caddy is a sidecar in the oauth2-proxy Pod, in namespace `oauth2-proxy`.
After authentication it routes browser paths to ttyd, code-server, Headlamp and Grafana,
including code-server path rewriting. Envoy remains the external entrypoint.

The Scaleway environment supports larger GPU Qwen models. GPU Operator
configures Container Toolkit, HAMi handles GPU sharing, and DCGM Exporter exposes
hardware metrics. These hardware paths are unqualified on the CPU VM; see
[GPU setup](gpu.md) for image boundaries and model selection.
