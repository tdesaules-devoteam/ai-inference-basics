# Kubernetes platform: storage milestone

Helmfile is the sole owner of platform Helm releases. k0s installs the native
cluster only; `platform/k0s/k0s.yaml` has no Helm extensions. The previous umbrella
is retained as migration input, not installed by this milestone.

## Installed releases

| Order | Release / namespace | Upstream source |
| --- | --- | --- |
| 1 | local-path-provisioner / local-path-provisioner | Rancher v0.0.37 chart from its verified source archive |
| 2 | rustfs / rustfs | RustFS chart 1.0.5, standalone |
| 3 | storage-bootstrap / rustfs | Local chart with a Kubernetes bucket initialization and S3 qualification Job |

`platform/helm/helmfile.yaml.gotmpl` expresses these dependencies with `needs`.
Helmfile 1.8.3 and Helm 4.3.1 run `sync` with `wait`, `waitForJobs` and bounded
timeouts. No helm-diff plugin or separate Helm installation commands are needed.
The bootstrap Job is a post-install/post-upgrade hook retained for inspection;
the next run replaces only that Job, not buckets or data.

`platform/units/platform-helm-charts-prepare.service` contains the URLs and SHA-256
pins for the Rancher source archive and RustFS chart archive inline. It verifies
bytes before extraction/use; no separate artifacts.lock file is needed.
Tool archive and executable checksums live in their respective installation units;
the installed executable is verified before deciding whether to skip its download.
Values pin every workload/init/helper image by digest. Official upstream
images use the repository's approved exception; no new image build is needed.

## Execution and state

Ignition copies Helm inputs to `/etc/ai-inference-basics/platform/helm/` and loads
units from `platform/units/`. Separate units install k0s, Helm, Helmfile, kubectl,
k9s and curl; a template unit creates the user's administrator kubeconfig.
The bootstrap is split into focused units:

| Unit | Responsibility |
| --- | --- |
| platform-helm-charts-prepare | Download/verify chart sources and extract the upstream Rancher chart |
| platform-k0s-ready | Wait for the native API and Ready node |
| platform-rustfs-credentials | Create/reuse the RustFS namespace and root Secret, after readiness |
| platform-k0s-bootstrap | Coordinate dependencies, run Helmfile and check the S3 Job |

The first three are dependency-activated by the bootstrap, rather than enabled
independently at boot. `Requires` and `After` enforce prerequisite success/order;
`PartOf` restarts the preparation units when the bootstrap is explicitly restarted.
The standalone tool installers and native controller are not restarted by this.
Commands remain inline; no prepare.sh or install.sh is copied or executed.
The provisioner, RustFS and bucket operations run in Kubernetes pods.

The native controller keeps its upstream name `k0scontroller.service`. Its alias
`platform-k0s-controller.service` is created by the installer, allowing platform-style
commands without breaking the native k0s service management commands.

Verified tools live in `/usr/local/bin`, outside mise. curl uses the signed OS
package at `/usr/bin/curl`, already present in the CoreOS base image. Its unit
installs via rpm-ostree, dnf or apt-get only when the binary is absent; curl follows
the OS package version rather than a separate GitHub binary pin. Chart downloads and Helm
state remain in `/var/lib/ai-inference-basics/platform`; the existing PVC paths and
Kubernetes Secrets are unchanged. The repository workspace and `.local/` are not
runtime dependencies. The temporary admin kubeconfig uses a private runtime
directory and is removed on success or unit stop/failure. Generated credentials
use a private temporary file removed on exit.

`rustfs-root` is created once as a Kubernetes Secret in `rustfs`; retries reuse it.
The root credentials are not written into Git, Helm values, rendered charts or
logs. This milestone uses them only for RustFS initialization and qualification.
Per-application bucket-scoped identities will be added with those consumers;
do not reuse the root credentials for model-serving pods.

The unit reconciles on boot and can be explicitly restarted to apply its current
copied configuration. Updating files on the workstation does not update Ignition
copies in an existing VM. For cloud-init integration later, install the same source
tree and adapt the service's k0s dependency to that bootstrap environment.

## Native administration tools

kubectl 1.37.2 and k9s 0.51.0 are downloaded from their upstream distributions,
verified by SHA-256 and installed by dedicated systemd units. The installer skips
an executable only when its checksum matches. Helm/k0s download units depend on
the curl unit. Ordering after `run-topgrade.service` still applies when that unit
is present; rpm-ostree checks are conditional so non-CoreOS VMs can reuse the
strategy. Cloud-init integration and the apt/dnf install branches are not yet
runtime-qualified; the VM must supply bash, tar, coreutils, jq and openssl.

`platform-kubeconfig@.service` selects an existing account through its instance
name. It generates a private user-owned administrator config only if none exists,
without printing it. The user config is persistent and separate from the temporary
bootstrap kubeconfig. To enable it for an account on a future VM:

```sh
sudo systemctl enable --now platform-kubeconfig@USERNAME.service
```

Replace USERNAME with the actual account name. devenv config.k enables the instance
for `qemu_butane_user_name` automatically. Native `kubectl get nodes` and the
installer/config preservation checks passed on the running CoreOS VM without
rebooting or recreating the cluster. The expanded set of units has not yet been
tested on a fresh VM.

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
sudo systemctl status platform-k0s-bootstrap.service --no-pager
sudo journalctl -u platform-k0s-bootstrap.service --no-pager
sudo k0s kubectl get storageclass local-path-provisioner
sudo k0s kubectl -n local-path-provisioner get pods
sudo k0s kubectl -n rustfs get pods,pvc,jobs
sudo k0s kubectl -n rustfs logs job/storage-bootstrap
```

To reconcile again using the current guest files:

```sh
sudo systemctl restart platform-k0s-bootstrap.service
```

The upstream `task devenv:up` waits for native provisioning, not for this platform
unit. `active (exited)` for this unit means all three releases and the S3 Job passed.

## Offline validation on the workstation

Use an existing Python environment with PyYAML, Helm 4.3.1 and Helmfile 1.8.3
on PATH. Populate an isolated artifact directory using the pins in the preparation unit:

```sh
export PLATFORM_ARTIFACTS=/tmp/opencode/platform-check/artifacts
python3 - <<'PY'
import hashlib, os, re, urllib.request
from pathlib import Path
destination = Path(os.environ['PLATFORM_ARTIFACTS'])
destination.mkdir(parents=True, exist_ok=True)
unit = Path('platform/units/platform-helm-charts-prepare.service').read_text()
pins = re.findall(r'^\s+fetch ([a-f0-9]{64}) (\S+) (\S+);', unit, re.M)
assert len(pins) == 2
for checksum, filename, url in pins:
    target = destination / filename
    urllib.request.urlretrieve(url, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == checksum, filename
PY
tar -xzf "$PLATFORM_ARTIFACTS/local-path-provisioner-v0.0.37.tar.gz" \
  -C "$PLATFORM_ARTIFACTS" local-path-provisioner-0.0.37/deploy/chart/local-path-provisioner
helmfile -f platform/helm/helmfile.yaml.gotmpl show-dag
python3 tests/validate_storage.py
python3 tests/test_platform_units.py
```

The offline check validates the resolved dependency graph, resource ownership,
namespace boundaries, digest pins (including helper pods), PVC configuration and
absence of credentials or public ingress. It is not boot evidence.

Runtime qualification succeeded after correcting the temporary kubeconfig ordering
and RustFS Service DNS name. All three releases deployed, the S3 Job passed, and a
RustFS pod replacement followed by Helmfile reexecution preserved the PVC identity,
credentials and existing sentinel object. After the reorganization, an authorized
destruction and recreation validated all four inline units on a clean disk without
guest fixes. The three releases reached deployed revision 1, the PVC was Bound,
and signed S3 PUT/GET/DELETE plus anonymous rejection passed. The bootstrap removed
its temporary kubeconfig and no systemd units were failed.
The subsequent alias and decomposition into preparation/readiness/credentials
units have been checked offline only; the running VM has not been updated for them.

## Subsequent milestones

The agreed next steps are cert-manager, Envoy Gateway and Agent Router, KServe
with three InferenceServices, Dex/oauth2-proxy, ttyd with Zellij CLI and code-server,
and separate Grafana/Loki/Tempo/Mimir releases with node/cluster OTel Collectors.
HAMi and DCGM will target eligible GPU nodes. These components are not installed
by the storage milestone.
