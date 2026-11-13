# Shared administration workspace

Pair training uses one computer, one Dex account named `admin`, and one shared
workspace in namespace `bastion`. Its Deployment contains ttyd with Zellij CLI
and code-server, sharing a 2-GiB PVC. There is no separate Zellij web-token login.

- `/terminal/`: shared Zellij session.
- `/code/`: shared editor and files (not a Live Share collaboration service).
- `/headlamp/`: full Kubernetes administration through the same browser login.

The bastion and Headlamp ServiceAccounts have `cluster-admin` permissions across
all namespaces. The terminal's Linux process remains non-root. The namespace and
workspace are shared intentionally; there are no Alice/Bob instances or `lab-a`
and `lab-b` namespaces in new installs.

The Fedora Minimal image includes kubectl, k9s, vLLM benchmarking, curl, bash,
Zellij, Starship, jq, Helix, code-server and RustFS rc. It is built on the host and
currently imported locally into native k0s. No nested container engine is needed.

See [lab access](lab.md) for private credential retrieval, the image prerequisite,
model activation and qualification commands. A persistent workspace survives Pod
replacement; destroying the disposable VM destroys its local storage.
