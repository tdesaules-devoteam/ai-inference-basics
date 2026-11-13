# Acceptance

Offline checks validate upstream archive checksums, digest-pinned workload images,
unique ownership, domain namespaces, embedded scripts, model locks and active
defaults. Strict Helm lint covers active/stopped settings; KCL/Butane checks verify
all source files are copied exactly. Offline checks do not constitute boot evidence.

After explicit VM authorization:

- The full 16-release Helmfile bootstrap completes successfully.
- One admin login reaches ttyd/Zellij, code-server and Headlamp over native HTTPS.
- Bastion and Headlamp have actual cluster-admin permissions.
- Anonymous identity-header spoofing fails, and browser cookies cannot authorize APIs.
- All three verified model snapshots are present under their named S3 prefixes.
- Each reader can read its own model but cannot write or read another model's objects.
- Models automatically reach Ready=True with one inference Pod each.
- Explicit stopping returns selected models to zero inference Pods.
- Active models produce real chat/SSE, embeddings and reranking responses.
- A short vLLM benchmark succeeds from the bastion through the internal Gateway.
- A final bootstrap preserves credentials/PVCs and restores the one-replica default.

Scripts and prerequisites are listed in [lab validation](lab.md#validation).
Observability and GPU acceptance remain future milestones. Reports stay ignored.
