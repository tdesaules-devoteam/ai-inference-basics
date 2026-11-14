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
os.environ['INFRA_DEFINITION'] = str(root / 'infra/infra-definition.sample.json')
definition = json.loads(Path(os.environ['INFRA_DEFINITION']).read_text())
helmfile = ['helmfile', '-f', str(root / 'platform/helmfile/helmfile.yaml.gotmpl')]
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
        for container in spec.get('initContainers', []) + spec['containers']:
            if container.get('command') == ['python3', '-c']:
                compile(container['args'][0], metadata['name'], 'exec')
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

names = [name for name, config in definition['models'].items() if config['enabled']]
assert len([o for o in objects if o['kind'] == 'InferenceService']) == len(names)
assert not any(o['kind'].startswith('LLMInference') for o in objects)
for name in names:
    model = find('InferenceService', name, name)
    assert model['metadata']['annotations']['serving.kserve.io/stop'] == str(definition['models'][name]['replicas'] == 0).lower()
    assert model['spec']['predictor']['serviceAccountName'] == 'model-reader'
    assert model['spec']['predictor']['model']['runtime'] == name
    lock = json.loads((root / 'charts' / name / 'files/model.lock.json').read_text())
    assert model['spec']['predictor']['model']['storageUri'] == f's3://models/{name}/{lock["revision"]}/'
    assert all(re.fullmatch('[a-f0-9]{64}', f['sha256']) and f['size'] > 0 for f in lock['files'])
    find('Job', 'model-import', name)
    assert not any(o['kind'] == 'Job' and o['metadata']['name'] == 'model-credentials' for o in objects)
    assert not (root / 'charts' / name / 'files/kube.py').exists()
deployment = find('Deployment', 'bastion', 'bastion')
assert len(deployment['spec']['template']['spec']['containers']) == 2
assert deployment['spec']['template']['spec']['serviceAccountName'] == 'bastion'
find('PersistentVolumeClaim', 'bastion', 'bastion')
assert find('ClusterRoleBinding', 'bastion-admin', '')['roleRef']['name'] == 'cluster-admin'
headlamp_binding = next(o for o in objects if o['kind'] == 'ClusterRoleBinding'
                        and any(s.get('namespace') == 'headlamp' for s in o.get('subjects', [])))
assert headlamp_binding['roleRef']['name'] == 'cluster-admin'
find('Job', 'dex-config', 'dex')
find('Job', 'oauth2-proxy-session', 'oauth2-proxy')
find('Job', 'rustfs-models-account', 'rustfs')
for policy in ('model-bucket-access', 'oauth2-proxy-oidc-client', 'oauth2-proxy-config', 'gateway-public-ca', 'bastion-api-key', 'bastion-public-ca'):
    find('GeneratingPolicy', policy, '')
find('Certificate', 'lab-root-ca', 'gateway')
find('Certificate', 'lab-tls', 'gateway')
assert find('Role', 'gateway-credentials', 'gateway')['rules'] == [
    {'apiGroups': [''], 'resources': ['secrets'], 'resourceNames': ['lab-api-key'], 'verbs': ['get', 'update']},
    {'apiGroups': [''], 'resources': ['secrets'], 'verbs': ['create']},
]
assert find('SecurityPolicy', 'model-api-key', 'gateway')['spec']['apiKeyAuth']['extractFrom'] == [{'headers': ['Authorization']}]
assert not any(o['metadata'].get('namespace') in ('inference-service', 'lab-a', 'lab-b') for o in objects)
state = yaml.safe_load(subprocess.check_output(helmfile + ['build'], text=True))
releases = {r['name']: r for r in state['releases']}
assert len(releases) == 25
assert len([r for r in releases.values() if r.get('installed', True)]) == 22
assert all('postRenderer' not in r for r in releases.values())
assert releases['dex']['needs'] == ['dex/dex-config']
assert 'lab-bootstrap' not in releases and 'models' not in releases
for name in names:
    assert releases[name]['namespace'] == name
    assert 'rustfs/rustfs' in releases[name]['needs']
assert 'oauth2-proxy/oauth2-proxy' not in releases['gateway']['needs']
http_charts = [
    ('hami', 'https://project-hami.github.io/HAMi', '2.11.0', '2530d25ba1a953a5ffa8070c308a373f756c6108c5bb39fce49943f614dd9315'),
    ('gpu-operator', 'https://helm.ngc.nvidia.com/nvidia', 'v26.7.2', 'a94a88628a90fac1df8d47469baf14dd352126553f30fd1ecd8e182516ae1bf6'),
    ('dcgm-exporter', 'https://nvidia.github.io/dcgm-exporter/helm-charts', '4.9.0', '912363f217914b33c993628a7471ca4497b9ee7e0c3e99016f9b55ed205b5e3e'),
    ('dex', 'https://charts.dexidp.io', '0.26.0', '3b22c1447935221a040870508274bff85a68b2b841902097d6fcacb3e9badd03'),
    ('headlamp', 'https://kubernetes-sigs.github.io/headlamp/', '0.46.0', 'faa471a8c5c55125b3dceed1cf73000e1ced18f07e2088e5e12e75292fb9ae62'),
    ('oauth2-proxy', 'https://oauth2-proxy.github.io/manifests', '10.7.4', 'e860a4d4e758a584120d62c00363f15c5067f09167d19846be6034b696e1f19c'),
]
with tempfile.TemporaryDirectory() as directory:
    for chart, repo, version, digest in http_charts:
        subprocess.run(['helm', 'pull', chart, '--repo', repo, '--version', version, '--destination', directory], check=True)
        assert hashlib.sha256((Path(directory) / f'{chart}-{version}.tgz').read_bytes()).hexdigest() == digest
for name, namespace in [('hami-device-plugin', 'hami'), ('dcgm-exporter', 'dcgm-exporter')]:
    assert find('DaemonSet', name, namespace)['spec']['template']['spec']['nodeSelector'] == {'nvidia.com/gpu.present': 'true'}
policy = next(o for o in objects if o['kind'] == 'ClusterPolicy')['spec']
for component in ('driver', 'devicePlugin', 'migManager', 'dcgmExporter'):
    assert policy[component]['enabled'] is False
assert policy['toolkit']['enabled'] is True
for route in ('root', 'terminal', 'code', 'headlamp', 'oauth2', 'dex'):
    find('HTTPRoute', 'browser-' + route, 'gateway')
gpu_names = ['qwen3-8b-fp8', 'qwen3-embedding-4b', 'qwen3-reranker-4b', 'lfm3-omni-2b']
definition['environment'] = 'scaleway'
definition['storage']['modelsGiB'] = 100
for name, config in definition['models'].items():
    config.update(enabled=name in gpu_names, replicas=int(name in gpu_names), **{'import': name in gpu_names})
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'infra.json'
    path.write_text(json.dumps(definition))
    os.environ['INFRA_DEFINITION'] = str(path)
    objects = list(filter(None, yaml.safe_load_all(subprocess.check_output(helmfile + ['-e', 'scaleway', 'template'], text=True))))
assert {o['metadata']['name'] for o in objects if o['kind'] == 'InferenceService'} == set(gpu_names)
for name in gpu_names:
    model = find('InferenceService', name, name)['spec']['predictor']['model']
    if name.startswith('qwen3'):
        limits = model['resources']['limits']
        assert limits['nvidia.com/gpu'] == '1'
        assert int(limits['nvidia.com/gpumem']) > 0
        assert 0 < int(limits['nvidia.com/gpucores']) <= 100
        assert not any(e['name'].startswith('VLLM_CPU') for e in find('ServingRuntime', name, name)['spec']['containers'][0]['env'])
print(json.dumps({'releases': len(releases), 'models_installed_in_cpu_sample': len(names), 'shared_admin_workspace': True,
                  'pinned_workload_images': len(images), 'runtime_tested': False}))
