#!/usr/bin/env python3
"""Validate domain ownership, admin access, active models and pinned artifacts."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import yaml

root = Path(__file__).resolve().parent.parent
os.environ.setdefault('LAB_HOSTNAME', 'fixture.local')
os.environ.setdefault('HELM_PLUGINS', str(root / 'platform/helm/plugins'))
os.environ.pop('LAB_MODEL_REPLICAS', None)
helmfile = ['helmfile', '-f', str(root / 'platform/helm/helmfile.yaml.gotmpl')]
objects = list(filter(None, yaml.safe_load_all(subprocess.check_output(helmfile + ['template'], text=True))))
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
assert all(re.search(r'@sha256:[a-f0-9]{64}$', image) for image in images), images

def find(kind, name, namespace):
    return next(o for o in objects if o['kind'] == kind and o['metadata']['name'] == name
                and o['metadata'].get('namespace', '') == namespace)

names = ('qwen3-0-6b', 'qwen3-embedding-0-6b', 'qwen3-reranker-0-6b')
assert len([o for o in objects if o['kind'] == 'InferenceService']) == 3
assert not any(o['kind'].startswith('LLMInference') for o in objects)
for name in names:
    model = find('InferenceService', name, name)
    assert model['metadata']['annotations']['serving.kserve.io/stop'] == 'false'
    assert model['spec']['predictor']['serviceAccountName'] == 'model-reader'
    assert model['spec']['predictor']['model']['runtime'] == name
    lock = json.loads((root / 'charts' / name / 'files/model.lock.json').read_text())
    assert model['spec']['predictor']['model']['storageUri'] == f's3://models/{name}/{lock["revision"]}/'
    assert all(re.fullmatch('[a-f0-9]{64}', f['sha256']) and f['size'] > 0 for f in lock['files'])
    find('Job', 'model-import', name)
    find('Job', 'model-credentials', name)
    role = find('Role', name + '-credentials', 'rustfs')
    assert role['rules'][0]['resourceNames'] == ['s3-' + name]
    assert role['rules'][0]['verbs'] == ['get']
    assert (root / 'charts' / name / 'files/kube.py').read_bytes() == (root / 'platform/helm/files/kube.py').read_bytes()
deployment = find('Deployment', 'bastion', 'bastion')
assert len(deployment['spec']['template']['spec']['containers']) == 2
assert deployment['spec']['template']['spec']['serviceAccountName'] == 'bastion'
find('PersistentVolumeClaim', 'bastion', 'bastion')
assert find('ClusterRoleBinding', 'bastion-admin', '')['roleRef']['name'] == 'cluster-admin'
headlamp_binding = next(o for o in objects if o['kind'] == 'ClusterRoleBinding'
                        and any(s.get('namespace') == 'headlamp' for s in o.get('subjects', [])))
assert headlamp_binding['roleRef']['name'] == 'cluster-admin'
for domain in ('dex', 'oauth2-proxy', 'rustfs'):
    find('Job', domain + '-domain', domain)
    role = find('Role', domain + '-domain', domain)
    assert all(r['resources'] == ['secrets'] for r in role['rules'])
find('Certificate', 'lab-root-ca', 'gateway')
find('Certificate', 'lab-tls', 'gateway')
assert find('SecurityPolicy', 'model-api-key', 'gateway')['spec']['apiKeyAuth']['extractFrom'] == [{'headers': ['Authorization']}]
assert not any(o['metadata'].get('namespace') in ('inference-service', 'lab-a', 'lab-b') for o in objects)
state = yaml.safe_load(subprocess.check_output(helmfile + ['build'], text=True))
releases = {r['name']: r for r in state['releases']}
assert len(releases) == 16
assert 'lab-bootstrap' not in releases and 'models' not in releases
for name in names:
    assert releases[name]['namespace'] == name
    assert 'rustfs/rustfs' in releases[name]['needs']
assert 'oauth2-proxy/oauth2-proxy' not in releases['gateway']['needs']
http_charts = [
    ('dex', 'https://charts.dexidp.io', '0.26.0', '3b22c1447935221a040870508274bff85a68b2b841902097d6fcacb3e9badd03'),
    ('headlamp', 'https://kubernetes-sigs.github.io/headlamp/', '0.46.0', 'faa471a8c5c55125b3dceed1cf73000e1ced18f07e2088e5e12e75292fb9ae62'),
    ('oauth2-proxy', 'https://oauth2-proxy.github.io/manifests', '10.7.4', 'e860a4d4e758a584120d62c00363f15c5067f09167d19846be6034b696e1f19c'),
]
with tempfile.TemporaryDirectory() as directory:
    for chart, repo, version, digest in http_charts:
        subprocess.run(['helm', 'pull', chart, '--repo', repo, '--version', version, '--destination', directory], check=True)
        assert hashlib.sha256((Path(directory) / f'{chart}-{version}.tgz').read_bytes()).hexdigest() == digest
print(json.dumps({'releases': len(releases), 'models_active_by_default': 3, 'shared_admin_workspace': True,
                  'pinned_workload_images': len(images), 'runtime_tested': False}))
