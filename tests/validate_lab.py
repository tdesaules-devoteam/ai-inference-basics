#!/usr/bin/env python3
"""Render the complete lab and validate cross-chart isolation, model and credential contracts."""
import json
import os
from pathlib import Path
import re
import subprocess
import hashlib
import tempfile

import yaml

root = Path(__file__).resolve().parent.parent
os.environ.setdefault('LAB_HOSTNAME', 'fixture.local')
raw = subprocess.check_output(['helmfile', '-f', str(root / 'platform/helm/helmfile.yaml.gotmpl'), 'template'], text=True)
objects = list(filter(None, yaml.safe_load_all(raw)))
keys = set()
images = []
for obj in objects:
    metadata = obj['metadata']
    if 'test' in metadata.get('annotations', {}).get('helm.sh/hook', ''):
        continue
    key = (obj['apiVersion'].split('/')[0], obj['kind'], metadata.get('namespace', ''), metadata['name'])
    assert key not in keys, key
    keys.add(key)
    if obj['kind'] in ('Deployment', 'StatefulSet', 'DaemonSet', 'Job'):
        spec = obj['spec']['template']['spec']
        images.extend(c['image'] for c in spec.get('initContainers', []) + spec['containers'])
    elif obj['kind'] == 'ServingRuntime':
        images.extend(c['image'] for c in obj['spec']['containers'])
    elif obj['kind'] == 'ClusterStorageContainer':
        images.append(obj['spec']['container']['image'])
    elif obj['kind'] == 'ConfigMap':
        for name, content in obj.get('data', {}).items():
            if name.endswith('.py'):
                compile(content, name, 'exec')
    elif obj['kind'] == 'Secret':
        assert metadata['name'] not in {'lab-access', 'lab-api-key', 'model-reader', 'model-writer', 'oauth-config', 'dex-config'}
assert all(re.search(r'@sha256:[a-f0-9]{64}$', image) for image in images), images
http_charts = [
    ('dex', 'https://charts.dexidp.io', '0.26.0', '3b22c1447935221a040870508274bff85a68b2b841902097d6fcacb3e9badd03'),
    ('headlamp', 'https://kubernetes-sigs.github.io/headlamp/', '0.46.0', 'faa471a8c5c55125b3dceed1cf73000e1ced18f07e2088e5e12e75292fb9ae62'),
    ('oauth2-proxy', 'https://oauth2-proxy.github.io/manifests', '10.7.4', 'e860a4d4e758a584120d62c00363f15c5067f09167d19846be6034b696e1f19c'),
]
with tempfile.TemporaryDirectory() as directory:
    for chart, repo, version, digest in http_charts:
        subprocess.run(['helm', 'pull', chart, '--repo', repo, '--version', version, '--destination', directory], check=True)
        assert hashlib.sha256((Path(directory) / f'{chart}-{version}.tgz').read_bytes()).hexdigest() == digest
models = [o for o in objects if o['kind'] == 'InferenceService']
assert len(models) == 3 and not any(o['kind'].startswith('LLMInference') for o in objects)
for model in models:
    assert model['metadata']['namespace'] == 'inference-service'
    predictor = model['spec']['predictor']
    assert predictor['serviceAccountName'] == 'model-reader'
    assert re.fullmatch(r's3://models/(chat|embeddings|rerank)/[a-f0-9]{40}/', predictor['model']['storageUri'])
for participant in ('a', 'b'):
    deployment = next(o for o in objects if o['kind'] == 'Deployment' and o['metadata']['name'] == 'bastion-' + participant)
    spec = deployment['spec']['template']['spec']
    assert spec['serviceAccountName'] == 'bastion-' + participant
    assert next(v for v in spec['volumes'] if v['name'] == 'workspace')['persistentVolumeClaim']['claimName'] == 'bastion-' + participant
    namespace = next(o for o in objects if o['kind'] == 'Namespace' and o['metadata']['name'] == 'lab-' + participant)
    assert namespace['metadata']['labels']['pod-security.kubernetes.io/enforce'] == 'restricted'
    assert not any(o['kind'] == 'ClusterRoleBinding' and o['roleRef']['name'] == 'cluster-admin'
                   and any(s.get('name') == 'bastion-' + participant for s in o.get('subjects', [])) for o in objects)
proxy = next(o for o in objects if o['kind'] == 'Deployment' and o['metadata']['name'] == 'oauth2-proxy')
assert len(proxy['spec']['template']['spec']['containers']) == 2
router = next(o for o in objects if o['kind'] == 'ConfigMap' and o['metadata']['name'] == 'browser-router')['data']['Caddyfile']
assert 'bind 127.0.0.1' in router and 'respond @deniedA 403' in router and 'respond @deniedB 403' in router
policy = next(o for o in objects if o['kind'] == 'SecurityPolicy' and o['metadata']['name'] == 'model-api-key')
assert policy['metadata']['namespace'] == 'gateway'
assert policy['spec']['apiKeyAuth']['extractFrom'] == [{'headers': ['Authorization']}]
lock = json.loads((root / 'charts/ai-inference-models/files/models.lock.json').read_text())
assert set(lock) == {'chat', 'embeddings', 'rerank'}
for model in lock.values():
    assert re.fullmatch(r'[a-f0-9]{40}', model['revision'])
    assert any(f['path'].endswith('.safetensors') for f in model['files'])
    assert all(re.fullmatch(r'[a-f0-9]{64}', f['sha256']) and f['size'] > 0 for f in model['files'])
print(json.dumps({'inference_services': len(models), 'pinned_workload_images': len(images),
                  'model_bytes': sum(f['size'] for m in lock.values() for f in m['files']),
                  'isolated_participants': 2, 'runtime_tested': False}))
