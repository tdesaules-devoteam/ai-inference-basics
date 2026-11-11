# Operations

Run from the repository root:

```sh
task up
task ssh
task down
```

`up` creates/provisions the lab and waits for readiness. `down` destroys the guest
disk; there is no separate stop/destroy operator interface in this version.
The original devenv runtime manages VM identity, SSH and disk lifecycle.

Inside the VM, mise supplies kubectl, k9s, Helm and Task. Bootstrap writes the
instructor's private kubeconfig to `~/.kube/config`.

```sh
kubectl get nodes
kubectl get pods -A
kubectl get charts.helm.k0sproject.io -n kube-system
kubectl -n ai-inference-basics get llmisvc,isvc,gateway,httproute
helm list -A
k9s
sudo journalctl -u ai-inference-basics-bootstrap.service
```

The guest bootstrap's ready marker is `/var/lib/ai-inference-basics/ready`.
Its presence means native k0s, the four k0s-managed chart releases and the model
resource readiness checks passed. It does not prove every browser/API test passed.

Use the k0s configuration as the deployment authority. Do not run a competing
manual upgrade against one of its releases. To rebuild the disposable lab, use
`task down`, then `task up`.
