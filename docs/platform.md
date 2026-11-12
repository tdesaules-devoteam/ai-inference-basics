# Kubernetes platform: storage and gateway foundations

Helmfile is the sole owner of the platform releases. k0s configures the native
cluster only; `platform/k0s/k0s.yaml` has no Helm extensions. Project-authored
charts belong in `charts/`; this milestone uses upstream charts exclusively.

## Releases and upstream sources

| Release | Namespace | Chart version | Upstream source |
| --- | --- | --- | --- |
| local-path-provisioner | local-path-provisioner | 0.0.37 | OCI ghcr.io/rancher/local-path-provisioner/charts/local-path-provisioner |
| rustfs | rustfs | 1.0.5 | <https://charts.rustfs.com> |
| cert-manager | cert-manager | v1.21.3 | OCI quay.io/jetstack/charts/cert-manager |
| envoy-gateway | envoy-gateway | v1.10.0 | OCI docker.io/envoyproxy/gateway-helm |
| agent-router-crds | agent-router | v1.2.1 | OCI docker.io/envoyproxy/ai-gateway-crds-helm |
| agent-router | agent-router | v1.2.1 | OCI docker.io/envoyproxy/ai-gateway-helm |

The complete OCI manifest digests are recorded directly in
`platform/helm/helmfile.yaml.gotmpl`. Helmfile 1.8.3 / Helm 4.3.1 fetch these official
references directly; there is no custom downloader, artifact lock or required
PLATFORM_ARTIFACTS directory. The qualified RustFS HTTP archive SHA-256 is checked
by `tests/validate_storage.py`. Its version pin is not OCI content addressing:
runtime installation trusts the upstream HTTP repository for version 1.0.5.

The OCI Local Path Provisioner chart has the same templates and values as the
previous GitHub source chart; its Chart.yaml differs only in serialization.
All application/init/helper images, including controller-generated Envoy/extProc
images, are pinned by digest. The upstream image exception remains applicable.

## Dependency and readiness contract

```text
local-path-provisioner → rustfs (including bucket Job)

cert-manager ────────────┐
envoy-gateway ───────────┼→ agent-router
agent-router-crds ───────┘
```

Independent prerequisites install in parallel. `wait`, `waitForJobs` and explicit
timeouts gate Helmfile dependency groups. Additional postsync hooks wait for the
required CRDs to be Established, Agent Router's Certificate to be Ready and its
webhook CA bundle to be injected. cert-manager's upstream startup API check and
Envoy Gateway's certificate-generation hooks remain enabled.

Agent Router is the renamed Envoy AI Gateway project: upstream chart/API/image
names still use ai-gateway. Its controller and Service are named `agent-router`.
Envoy Gateway's extension manager connects to
`agent-router.agent-router.svc.cluster.local:1063`; Agent Router's Envoy RBAC points
to `envoy-gateway`. Envoy data-plane pods are created in each Gateway's namespace.
No model API, public Gateway or browser route is installed in this milestone.
QuotaPolicy and the optional rate-limit server are not enabled yet.

## RustFS buckets and persistent data

The default StorageClass `local-path-provisioner` creates local volumes under
`/var/lib/local-path-provisioner`, with `WaitForFirstConsumer` and reclaim policy
`Delete`. RustFS is a standalone Deployment using the existing `rustfs-data` PVC
of 20 GiB and a Recreate strategy. Requested capacity is not a filesystem quota;
monitor free space on the 64 GiB VM disk.

`platform/helm/values/rustfs.yaml` uses the upstream `extraManifests` field for two
stages, without a dedicated chart or host credential service:

1. Pre-install/pre-upgrade hooks create the `rustfs-credentials` ServiceAccount,
   Role and RoleBinding (weights -30, -20, -10), then the credential Job (weight 0).
   Helm creates the namespace before these hooks. The Job authenticates to the
   Kubernetes API with its projected token and verifies TLS with the cluster CA.
   It reads `rustfs-root`; only HTTP 404 triggers random credential generation.
   Other API errors fail the hook. A concurrent creation (409) is followed by a
   fresh read and validation. An existing invalid Secret fails without replacement.
2. After RustFS is ready, the `rustfs-buckets` post-install/post-upgrade Job creates
   and checks the application buckets using that Secret.

The credential Job uses a digest-pinned official Python image and only the standard
library; it does not install tools or packages at runtime. It never prints credential
values. RBAC grants GET only for rustfs-root and CREATE Secrets only in the release
namespace; Kubernetes cannot restrict CREATE by resource name. No list/update/delete
permissions or ClusterRoleBinding are granted. The buckets Job has no API token.

The six buckets are:

- `loki`, `tempo`;
- `mimir-blocks`, `mimir-ruler`, `mimir-alertmanager`;
- `models`.

There is no separate storage-bootstrap chart/release. Both Jobs have a one-hour
TTL after completion/failure and are replaced before their next hook execution.
The hook RBAC and generated Secret remain until explicitly removed or their
namespace is deleted; Helm uninstall does not own the generated Secret. Upgrades
preserve the existing credentials. The hooks do not import model weights,
delete buckets or run benchmarks. Buckets omitted from the list are not deleted:
`benchmark-results` and `platform-checks` from older installations may still exist.

The internal endpoint is `http://rustfs-svc.rustfs.svc.cluster.local:9000`, using
region `us-east-1` and path-style S3 addressing. Only ClusterIP services are exposed;
the RustFS console is disabled. Data survives pod replacement but is lost when the
VM disk is destroyed. Root credentials are reserved for administration/bootstrap;
per-application bucket-scoped credentials will accompany the application consumers.

## Provisioning units

Ignition copies Helmfile and values to `/etc/ai-inference-basics/platform/helm/`.
Tool installers and the per-user kubeconfig unit live in `platform/units/`.
The bootstrap requires verified Helm/Helmfile/kubectl and the k0s readiness unit.
Helm controls credential preparation inside Kubernetes. The temporary bootstrap
kubeconfig is removed on success or stop/failure. Chart fetching is owned by Helmfile.

The source also provides `platform-k0s-controller.service` as an alias of the
native `k0scontroller.service`. Existing guests need an explicit migration or a
fresh provision to acquire this installer-created alias; native k0s remains intact.

The independent `platform-kubeconfig@USERNAME.service` generates a user-owned
administrator kubeconfig (directory 0700, file 0600) and preserves existing files.
The instance name supplies `%i`; the home path comes from the account database.
kubectl, Helm, Helmfile and k9s are in `/usr/local/bin`; curl uses the signed OS
package in `/usr/bin`. No mise activation is needed for Kubernetes administration.
The non-CoreOS package-manager branches and cloud-init integration are not qualified.

## Commands inside the VM

```sh
sudo systemctl status platform-k0s-bootstrap.service --no-pager
sudo journalctl -u platform-k0s-bootstrap.service --no-pager
helm list -A
kubectl get pods -A
kubectl -n rustfs get pvc,jobs
kubectl -n rustfs logs job/rustfs-credentials
kubectl -n rustfs logs job/rustfs-buckets
kubectl -n agent-router get certificates,issuers
```

To reconcile the current guest copies, use
`sudo systemctl restart platform-k0s-bootstrap.service`. Updating source files
on the workstation does not automatically update Ignition copies. Native
`task devenv:up` does not wait for this platform unit to finish.

## Migration from the former storage release

The authorized migration removed the old hook-only `storage-bootstrap` release
through a temporary Helmfile declaration with `installed: false`, then removed its
retained Job. This did not uninstall RustFS or Local Path Provisioner. The RustFS
PVC UID and credential data were compared before and after and preserved.
No existing bucket or object was deleted. For other existing guests, perform this
explicit migration; merely omitting a release from Helmfile does not uninstall it.

## Validation

With Helm 4.3.1, Helmfile 1.8.3 and a Python environment containing PyYAML:

```sh
helmfile -f platform/helm/helmfile.yaml.gotmpl show-dag
helmfile -f platform/helm/helmfile.yaml.gotmpl lint
python3 tests/validate_storage.py
python3 tests/test_platform_units.py
python3 tests/test_rustfs_credentials.py
```

Rendering checks namespaces, resource ownership, OCI pins, HTTP archive checksum,
image pins, the six-bucket hook and cross-namespace gateway configuration. Upstream
charts with a leading `v` in Chart.yaml produce SemVer warnings under Helm lint;
strict mode rejects that upstream metadata. Their sources are not rewritten locally.

`tests/test_rustfs_credentials.py` executes the actual inline hook code with API
fixtures for creation, reuse, malformed data, access/server errors and concurrent
creation. `bash tests/qualify_rustfs_hooks.sh` installs and upgrades the official
RustFS chart in an isolated namespace, checks effective RBAC and stable credentials,
then removes that test release and namespace. It does not delete the main Secret.
This fresh-namespace install/upgrade test passed, including effective RBAC checks.
The main release was then migrated without changing its Secret UID/data or PVC,
and signed/anonymous S3 tests passed. The old credential service was removed from
the guest; no VM or RustFS workload restart was needed for the migration.

Run `bash tests/qualify_foundations.sh` explicitly in the intended kubectl context
to exercise a temporary Gateway, Agent Router route and upstream mock OpenAI server,
then authenticated/anonymous S3 requests. It cleans up its namespace, GatewayClass,
test Job and uniquely named temporary S3 object. It creates no extra bucket.

This qualification passed in the authorized VM, including certificate-backed
webhook injection, Gateway programming, a JSON OpenAI response, S3 access and
cleanup. Reexecuting all six releases preserved the RustFS PVC, root credentials
and Agent Router MCP encryption seed. No systemd unit was failed. The complete
foundation milestone has not yet been qualified on a newly recreated VM.

Later milestones cover KServe and three InferenceServices, model imports, browser
authentication and bastion tools, then separate Grafana/Loki/Tempo/Mimir and OTel
Collectors. These components are not installed by this foundation milestone.
