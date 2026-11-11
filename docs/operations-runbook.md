# Operations

Run from the repository root:

```sh
task up
task ssh
task down
```

`up` creates/provisions the lab and waits for readiness. `down` destroys the guest
disk; there is no separate stop/destroy operator interface in this version.
The original devenv runtime manages VM identity and disk lifecycle. SSH uses that
persisted identity and the same SSH options directly, without KCL evaluation.

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

The inline unit's marker is `/var/lib/ai-inference-basics/initialized`: it means
the binary/configuration and bastion image have been installed, not that every
application is ready. The host-side wait checks the four k0s-managed chart releases
and model readiness before task up succeeds. Browser/API acceptance remains separate.

Use the k0s configuration as the deployment authority. Do not run a competing
manual upgrade against one of its releases. To rebuild the disposable lab, use
`task down`, then `task up`.
