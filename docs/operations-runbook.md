# Operating the CPU lab

Run these tasks on the workstation from the repository root, after completing
[local setup](devenv.md):

| Task | Effect |
| --- | --- |
| `task devenv:up attach=false` | Start or provision the VM without attaching an interactive SSH session. |
| `task devenv:ssh` | Connect to the guest using its native bridge and mDNS name. |
| `task devenv:stop` | Stop the VM and retain its disk, workspace and buckets. |
| `task devenv:down` | Destroy the VM disk, including its local persistent volumes. |

## Check readiness inside the guest

SSH availability does not mean the models are ready. On a first boot, check
provisioning, then Helmfile, then the inference services:

```sh
systemctl --failed
systemctl status platform-images-ready.service platform-k0s-bootstrap.service --no-pager
sudo journalctl -b -u platform-k0s-bootstrap.service --no-pager
helm list -A
kubectl get nodes
kubectl get inferenceservices -A
kubectl -n gateway get gateway,httproute
```

A successful bootstrap uses the environment copied to `/etc/ai-inference-basics`.
In the CPU sample all three Qwen services should be Ready. If a model is
intentionally stopped, expect the KServe `Stopped=True` condition and zero
predictor Pods instead. To verify actual responses, use the [API examples](api.md).

## Apply a configuration change

Edit the private environment JSON and validate it on the workstation. Ignition
copies are first-boot inputs: before reconciling an existing guest, synchronize
the changed definition and any changed chart, values or unit files to their
installed locations. Preserve the private definition's permissions. Reload systemd
if units changed; if image pins changed, restart `platform-images-ready.service`.
Then run `sudo systemctl restart platform-k0s-bootstrap.service` inside the guest.
Helmfile owns the releases; `platform/k0s/k0s.yaml` configures the cluster itself.

For failures see [troubleshooting](troubleshooting.md); for browser, S3 and
telemetry qualification see [acceptance](acceptance.md).
