# Which checks to run

The platform does not deploy this directory. CI runs the render contracts and
unit tests; the `qualify_*` scripts exercise a running, explicitly selected lab.

| Files | Purpose |
| --- | --- |
| `validate.py` | Entry point for `validate_storage.py` (foundation subset) and `validate_lab.py` (full Helmfile, including CPU/GPU and disabled selections). Uses the public fixtures. |
| `test_*.py` | Offline contracts for environment validation, hook credential handling, Kyverno reloads, model convergence and systemd units. |
| `qualify_foundations.sh`, `fixtures/`, `qualify_rustfs_hooks.sh` | Deploy temporary resources to exercise routing, signed S3 operations and isolated RustFS install/upgrade behavior. |
| `qualify_model_apis.py`, `qualify_gateway_logs.py` | Use the gateway to check real inference, authentication, streaming and token accounting. |
| `qualify_model_storage.py` | Check model snapshots and bucket access from a provision-image Pod; supply a JSON map of model locks on stdin. |
| `qualify_admin.sh`, `browser/` | Check shared workspace access and admin privileges; Playwright exercises the browser journey and correlates telemetry through Grafana. |
| `generate_model_lock.py` | Authoring utility for updating model snapshots, not a test or a boot prerequisite. |
| `qualify_benchmark.py` | Optional benchmark client; not part of routine deployment or acceptance. |

From the repository root, with `requirements-dev.txt`, Helm and Helmfile installed:

```sh
python tests/validate.py
python -m unittest discover -s tests -p 'test_*.py'
```

See [lab qualification](../docs/lab.md#validation) for runtime credentials and
context. Browser dependencies are reproducible with `npm ci` in `tests/browser`;
the local `node_modules/` and Python bytecode caches are not tracked.
