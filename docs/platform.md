# Kubernetes platform: storage milestone

Helmfile is the sole owner of platform Helm releases. k0s installs the native
cluster only; `infra/k0s/k0s.yaml` has no Helm extensions. The previous umbrella
is retained as migration input, not installed by this milestone.

## Installed releases

| Order | Release / namespace | Upstream source |
| --- | --- | --- |
| 1 | local-path-provisioner / local-path-provisioner | Rancher v0.0.37 chart from its verified source archive |
| 2 | rustfs / rustfs | RustFS chart 1.0.5, standalone |
| 3 | storage-bootstrap / rustfs | Local chart with a Kubernetes bucket initialization and S3 qualification Job |

`platform/helmfile.yaml.gotmpl` expresses these dependencies with `needs`.
Helmfile 1.8.3 and Helm 4.3.1 run `sync` with `wait`, `waitForJobs` and bounded
timeouts. No helm-diff plugin or separate Helm installation commands are needed.
The bootstrap Job is a post-install/post-upgrade hook retained for inspection;
the next run replaces only that Job, not buckets or data.

`platform/artifacts.lock` pins the tool archives, Rancher source archive and
RustFS chart archive by SHA-256. `prepare.sh` checks bytes before extraction/use,
and values pin every workload/init/helper image by digest. Official upstream
images use the repository's approved exception; no new image build is needed.

## Execution and state

Ignition copies platform sources to `/etc/ai-inference-basics/platform/` and
adds `platform-install.service`. The service runs after `k0sinstall.service`,
defers across the staged CoreOS provisioning reboot, then waits for the API and
Ready node. It executes Helmfile; the provisioner, RustFS and bucket operations
all run in Kubernetes pods, not as host storage services.

Verified tools and downloaded sources live in `/var/lib/ai-inference-basics/platform`.
The repository workspace and `.local/` are not runtime dependencies. The temporary
admin kubeconfig and generated credentials use private temporary files removed on
exit. An execution lock rejects overlapping installations.

`rustfs-root` is created once as a Kubernetes Secret in `rustfs`; retries reuse it.
The root credentials are not written into Git, Helm values, rendered charts or
logs. This milestone uses them only for RustFS initialization and qualification.
Per-application bucket-scoped identities will be added with those consumers;
do not reuse the root credentials for model-serving pods.

The unit reconciles on boot and can be explicitly restarted to apply its current
copied configuration. Updating files on the workstation does not update Ignition
copies in an existing VM. For cloud-init integration later, install the same source
tree and adapt the service's k0s dependency to that bootstrap environment.

## Storage and S3

The default StorageClass `local-path-provisioner` creates local volumes under
`/var/lib/local-path-provisioner` using `WaitForFirstConsumer` and reclaim policy
`Delete`. RustFS uses one 20 GiB PVC, `rustfs-data`, with a Recreate deployment
strategy. Local Path Provisioner does not enforce the requested PVC size as a
filesystem quota: monitor free disk space on the 64 GiB VM disk.

Buckets created idempotently:

- `loki`, `tempo`, `mimir-blocks`, `mimir-ruler`, `mimir-alertmanager`;
- `models`, `benchmark-results`;
- `platform-checks` for the qualification sentinel.

The endpoint is `http://rustfs-svc.rustfs.svc.cluster.local:9000`. Only ClusterIP
services are created; the console and ingress are disabled until browser access
is integrated. This internal lab endpoint uses HTTP. Applications must configure
the S3 endpoint, region `us-east-1` and path-style addressing.

The Job checks bucket creation and authenticated PUT/GET/DELETE, rejects anonymous
object reads, and verifies a previous sentinel when reexecuted. Buckets do not
contain model weights yet. This is single-node storage, not HA: PVCs survive pod
recreation, but destroying the VM destroys the disk and its objects.

## Commands inside the VM

```sh
sudo systemctl status platform-install.service --no-pager
sudo journalctl -u platform-install.service --no-pager
sudo k0s kubectl get storageclass local-path-provisioner
sudo k0s kubectl -n local-path-provisioner get pods
sudo k0s kubectl -n rustfs get pods,pvc,jobs
sudo k0s kubectl -n rustfs logs job/storage-bootstrap
```

To reconcile again using the current guest files:

```sh
sudo systemctl restart platform-install.service
```

The upstream `task devenv:up` waits for native provisioning, not for this platform
unit. `active (exited)` for this unit means all three releases and the S3 Job passed.

## Offline validation on the workstation

Use an existing Python environment with PyYAML and an isolated build directory:

```sh
export PLATFORM_STATE_DIR=/tmp/opencode/platform-check
bash platform/prepare.sh
export PATH="$PLATFORM_STATE_DIR/bin:$PATH"
export PLATFORM_ARTIFACTS="$PLATFORM_STATE_DIR/artifacts"
helmfile -f platform/helmfile.yaml.gotmpl show-dag
python3 tests/validate_storage.py
```

The offline check validates the resolved dependency graph, resource ownership,
namespace boundaries, digest pins (including helper pods), PVC configuration and
absence of credentials or public ingress. It is not boot evidence.

Runtime qualification succeeded after correcting the temporary kubeconfig ordering
and RustFS Service DNS name. All three releases deployed, the S3 Job passed, and a
RustFS pod replacement followed by Helmfile reexecution preserved the PVC identity,
credentials and existing sentinel object. The final corrected recipe has not been
tested on a second clean VM boot.

## Subsequent milestones

The agreed next steps are cert-manager, Envoy Gateway and Agent Router, KServe
with three InferenceServices, Dex/oauth2-proxy, ttyd with Zellij CLI and code-server,
and separate Grafana/Loki/Tempo/Mimir releases with node/cluster OTel Collectors.
HAMi and DCGM will target eligible GPU nodes. These components are not installed
by the storage milestone.
