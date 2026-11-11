#!/usr/bin/env python3
"""Resolve k0s's active Linux/kube-router images into a reviewed config artifact."""
import concurrent.futures
import json
import pathlib
import subprocess
import yaml

root = pathlib.Path(__file__).resolve().parent.parent
config = yaml.safe_load(subprocess.check_output([
    str(root / '.local/bin/k0s'), 'config', 'create', '--include-images'
]))
images = config['spec']['images']
for unused in ('windows', 'calico', 'pushgateway'):
    images.pop(unused, None)

def lock(item):
    ref = item['image'] + ':' + item['version']
    raw = subprocess.check_output(['skopeo', 'inspect', '--raw', 'docker://' + ref])
    import hashlib
    digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
    item['version'] += '@' + digest
    return ref, digest

leaves = []
def walk(node):
    if isinstance(node, dict):
        if 'image' in node and 'version' in node:
            leaves.append(node)
        else:
            for child in node.values():
                walk(child)
walk(images)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    pins = dict(pool.map(lock, leaves))
target = root / 'infra/k0s'
target.mkdir(parents=True, exist_ok=True)
(target / 'images.lock.json').write_text(json.dumps(pins, indent=2) + '\n')
minimal = {
    'apiVersion': 'k0s.k0sproject.io/v1beta1', 'kind': 'ClusterConfig',
    'metadata': {'name': 'ai-inference-basics'},
    'spec': {
        'api': {'sans': ['127.0.0.1', 'localhost']},
        'network': {'provider': 'kuberouter'},
        'telemetry': {'enabled': False}, 'images': images,
    },
}
(target / 'config.yaml').write_text(yaml.safe_dump(minimal, sort_keys=False))
