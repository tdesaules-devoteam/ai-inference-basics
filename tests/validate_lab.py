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
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

root = Path(__file__).resolve().parent.parent
os.environ['INFRA_DEFINITION'] = str(root / 'infra/infra-definition.sample.json')
definition = json.loads(Path(os.environ['INFRA_DEFINITION']).read_text())
helmfile = ['helmfile', '-f', str(root / 'platform/helmfile/helmfile.yaml.gotmpl')]
objects = list(filter(None, yaml.safe_load_all(subprocess.check_output(helmfile + ['template'], text=True))))
keys = set()
images = []
for obj in objects:
    metadata = obj['metadata']
    if 'test' in (metadata.get('annotations') or {}).get('helm.sh/hook', ''):
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
    native = yaml.safe_load((root / 'charts' / name / 'values.yaml').read_text())['nativeContextTokens']
    container = find('ServingRuntime', name, name)['spec']['containers'][0]
    assert int(container['args'][container['args'].index('--max-model-len') + 1]) == native == 32_768
    config = yaml.safe_load((root / 'charts' / name / 'values.yaml').read_text())
    # All pinned Qwen 0.6B configurations have 28 layers, 8 KV heads and
    # head_dim=128. CPU pooling also reserves BF16 KV in this vLLM version.
    assert config['kvCacheGiB'] * 1024**3 >= native * 28 * 8 * 128 * 2 * 2
    assert {'name': 'VLLM_CPU_KVCACHE_SPACE', 'value': str(config['kvCacheGiB'])} in container['env']
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
find('Job', 'rustfs-accounts', 'rustfs')
for policy in ('model-bucket-sources', 'model-bucket-access', 'oauth2-proxy-oidc-client', 'oauth2-proxy-config', 'bastion-api-key'):
    find('GeneratingPolicy', policy, '')
for namespace in ('bastion', 'dex', 'oauth2-proxy'):
    policy = find('MutatingPolicy', namespace + '-reload-credentials', '')['spec']
    assert policy['evaluation']['mutateExisting']['enabled']
    assert policy['matchConditions'][0]['expression'] == 'request.object.data != request.oldObject.data'
    role = find('Role', 'credential-reload', namespace)['rules'][0]
    assert role['resourceNames'] == [namespace] and role['verbs'] == ['get', 'update', 'patch']
    subject = find('RoleBinding', 'credential-reload', namespace)['subjects'][0]
    find('ServiceAccount', subject['name'], subject['namespace'])
assert not any(o['kind'] in ('Issuer', 'Certificate') and o['metadata'].get('namespace') in ('gateway', 'agentgateway') for o in objects)
assert not any(o['metadata']['name'] in ('gateway-public-ca', 'bastion-public-ca') for o in objects)
assert 'lab-ca' not in str(find('Deployment', 'bastion', 'bastion')['spec'])
assert find('Role', 'gateway-credentials', 'gateway')['rules'] == [
    {'apiGroups': [''], 'resources': ['secrets'], 'resourceNames': ['lab-api-key'], 'verbs': ['get', 'update']},
    {'apiGroups': [''], 'resources': ['secrets'], 'verbs': ['create']},
]
assert not any(o['kind'] in ('AIServiceBackend', 'AIGatewayRoute') for o in objects)
find('Deployment', 'agentgateway', 'agentgateway')
service = find('Service', 'agentgateway', 'agentgateway')['spec']
assert service['ports'][0]['nodePort'] == definition['network']['apiNodePort']
assert service['ports'][0]['nodePort'] != definition['network']['httpsNodePort']
config = yaml.safe_load(find('ConfigMap', 'agentgateway-config', 'agentgateway')['data']['config.yaml'])
listener = config['binds'][0]['listeners'][0]
assert listener['protocol'] == 'HTTP' and 'tls' not in listener
routes = {r['matches'][0]['path']['exact']: r for r in listener['routes']}
assert len(routes) == len(listener['routes']) == 7
expected_hash = 'sha256:' + hashlib.sha256(definition['access']['apiBearerToken'].encode()).hexdigest()
for path, route in routes.items():
    if path == '/openapi.json':
        assert 'apiKey' not in route['policies']
    else:
        assert route['policies']['apiKey'] == {'keys': [{'keyHash': expected_hash}], 'mode': 'strict'}
    if 'backends' not in route:
        continue
    target = route['backends'][0]
    name = target.get('ai', {}).get('name', 'qwen3-reranker-0-6b')
    assert target.get('host', target.get('ai', {}).get('hostOverride')) == f'{name}-predictor.{name}.svc.cluster.local:80'
    assert 'authorization' in target.get('ai', target)['policies']['requestHeaderModifier']['remove']
    assert find('NetworkPolicy', 'model-apis-gateway-only', name)['spec']['ingress'][0]['from'][0]['namespaceSelector']['matchLabels']['kubernetes.io/metadata.name'] == 'agentgateway'
assert {m['id'] for m in json.loads(routes['/v1/models']['policies']['directResponse']['body'])['data']} == set(names)
assert find('Gateway', 'ai-inference-basics', 'gateway')['spec']['listeners'][0]['protocol'] == 'HTTP'
web_origin = 'http://{}:{}'.format(definition['network']['hostname'], definition['network']['httpsNodePort'])
assert listener['policies']['cors']['allowOrigins'] == [web_origin]
assert not listener['policies']['cors'].get('allowCredentials', False)
def collection():
    return yaml.safe_load(find('ConfigMap', 'requester-collection', 'requester')['data']['models.yaml'])

spec = json.loads(routes['/openapi.json']['policies']['directResponse']['body'])
assert set(routes) == set(spec['paths'])
assert 'models.yaml' not in find('ConfigMap', 'requester-collection', 'requester')['data']
root_rule, = find('HTTPRoute', 'browser-root', 'gateway')['spec']['rules']
assert root_rule['matches'] == [{'path': {'type': 'Exact', 'value': '/'}}]
extension, = root_rule['filters']
assert extension['type'] == 'ExtensionRef'
response = find('HTTPRouteFilter', extension['extensionRef']['name'], 'gateway')['spec']['directResponse']
assert (response['statusCode'], response['contentType']) == (200, 'application/json')
directory = json.loads(response['body']['inline'])
assert set(directory['web'].values()) == {web_origin + path for path in
    ('/', '/ttyd/', '/scalar/', '/code/', '/headlamp/', '/grafana/', '/dex/', '/oauth2/')}
assert {entry['url'] for entry in directory['models']} == {spec['servers'][0]['url'] + path for path in spec['paths'] if 'post' in spec['paths'][path]}
assert spec['servers'] == [{'url': 'http://{}:{}'.format(definition['network']['hostname'], definition['network']['apiNodePort'])}]
assert spec['security'] == [{'modelKey': []}]
registry = Registry().with_resource('urn:lab:openapi', Resource.from_contents(spec, default_specification=DRAFT202012))
for path, endpoints in spec['paths'].items():
    if 'post' not in endpoints:
        continue
    media = endpoints['post']['requestBody']['content']['application/json']
    pointer = path.replace('/', '~1')
    validator = Draft202012Validator({'$ref': f'urn:lab:openapi#/paths/{pointer}/post/requestBody/content/application~1json/schema'}, registry=registry)
    for example in media['examples'].values():
        validator.validate(example['value'])
    assert not validator.is_valid(dict(media['examples']['default']['value'], model='unknown-model'))
assert set(spec['paths']) == {'/v1/chat/completions', '/v1/embeddings', '/v2/rerank', '/score', '/v1/responses', '/v1/models', '/openapi.json'}
assert {operation['post']['requestBody']['content']['application/json']['examples']['default']['value']['model']
        for operation in spec['paths'].values() if 'post' in operation} == set(names)
assert definition['access']['apiBearerToken'] not in str(spec)
assert not any(o['kind'] == 'HTTPRoute' and o['metadata']['name'] == 'model-api' for o in objects)
assert not any(o['metadata'].get('namespace') in ('inference-service', 'lab-a', 'lab-b') for o in objects)
state = yaml.safe_load(subprocess.check_output(helmfile + ['build'], text=True))
releases = {r['name']: r for r in state['releases']}
platform_releases = {'kyverno', 'local-path-provisioner', 'rustfs', 'cert-manager', 'envoy-gateway',
                     'agentgateway-config', 'agentgateway', 'kserve-crds', 'kserve', 'dex-config', 'dex',
                     'headlamp', 'bastion', 'requester', 'oauth2-proxy', 'gateway', 'gpu-operator', 'hami', 'dcgm-exporter',
                     'grafana', 'loki', 'tempo', 'mimir', 'otel-node', 'otel-cluster'}
assert set(releases) == platform_releases | set(definition['models'])
assert {n for n, r in releases.items() if r.get('installed', True)} == platform_releases | set(names)
assert all('postRenderer' not in r for r in releases.values())
assert releases['dex']['needs'] == ['dex/dex-config']
assert 'lab-bootstrap' not in releases and 'models' not in releases
for name in names:
    assert releases[name]['namespace'] == name
    assert 'rustfs/rustfs' in releases[name]['needs']
assert 'oauth2-proxy/oauth2-proxy' not in releases['gateway']['needs']
http_charts = [
    ('hami', 'https://project-hami.github.io/HAMi', '2.11.0', '2530d25ba1a953a5ffa8070c308a373f756c6108c5bb39fce49943f614dd9315'),
    ('gpu-operator', 'https://helm.ngc.nvidia.com/nvidia', 'v26.7.3', '506898724dc23aa55bbc9cbe6f3e28d413c20867e76715e726b6fff6ef13d4c7'),
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
for route in ('root', 'terminal', 'code', 'headlamp', 'requester', 'grafana', 'oauth2', 'dex'):
    find('HTTPRoute', 'browser-' + route, 'gateway')
for kind, name, namespace in [('Deployment', 'grafana', 'grafana'), ('StatefulSet', 'loki', 'loki'),
                              ('StatefulSet', 'tempo', 'tempo'), ('StatefulSet', 'mimir-ingester', 'mimir'),
                              ('DaemonSet', 'otel-node-agent', 'opentelemetry-collector'),
                              ('Deployment', 'otel-cluster', 'opentelemetry-collector')]:
    find(kind, name, namespace)
assert not any(o['kind'] == 'ConfigMap' and 'grafana_dashboard' in (o['metadata'].get('labels') or {}) for o in objects)
assert not any(o['metadata'].get('namespace') == 'mimir' and 'kafka' in o['metadata']['name'] for o in objects)
find('GeneratingPolicy', 'observability-bucket-access', '')
find('GeneratingPolicy', 'grafana-admin-access', '')
definition = json.loads((root / 'infra/infra-definition.scaleway.sample.json').read_text())
gpu_names = [name for name, config in definition['models'].items() if config['enabled']]
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'infra.json'
    path.write_text(json.dumps(definition))
    os.environ['INFRA_DEFINITION'] = str(path)
    objects = list(filter(None, yaml.safe_load_all(subprocess.check_output(helmfile + ['-e', 'scaleway', 'template'], text=True))))
assert find('Gateway', 'ai-inference-basics', 'gateway')['spec']['listeners'][0]['protocol'] == 'HTTPS'
find('Certificate', 'lab-root-ca', 'gateway')
find('Certificate', 'lab-tls', 'gateway')
assert {o['metadata']['name'] for o in objects if o['kind'] == 'InferenceService'} == set(gpu_names)
assert {operation['post']['requestBody']['content']['application/json']['examples']['default']['value']['model']
        for operation in collection()['paths'].values()} == set(gpu_names)
for name in gpu_names:
    model = find('InferenceService', name, name)['spec']['predictor']['model']
    limits = model['resources']['limits']
    assert limits['nvidia.com/gpu'] == '1'
    assert int(limits['nvidia.com/gpumem']) > 0
    assert 0 < int(limits['nvidia.com/gpucores']) <= 100
    env = find('ServingRuntime', name, name)['spec']['containers'][0]['env']
    native = yaml.safe_load((root / 'charts' / name / 'values.yaml').read_text())['nativeContextTokens']
    container = find('ServingRuntime', name, name)['spec']['containers'][0]
    assert int(container['args'][container['args'].index('--max-model-len') + 1]) == native == 32_768
    assert not any(e['name'].startswith('VLLM_CPU') for e in env)
# An infrastructure-only environment must neither import models nor publish API routes.
definition = json.loads((root / 'infra/infra-definition.sample.json').read_text())
for config in definition['models'].values():
    config.update(enabled=False, replicas=0, **{'import': False})
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'infra.json'
    path.write_text(json.dumps(definition))
    os.environ['INFRA_DEFINITION'] = str(path)
    disabled = list(filter(None, yaml.safe_load_all(subprocess.check_output(helmfile + ['template'], text=True))))
assert not any(o['kind'] in ('InferenceService', 'AIGatewayRoute', 'AIServiceBackend') for o in disabled)
assert not any(o['kind'] == 'Job' and o['metadata']['name'] == 'model-import' for o in disabled)
api_config = next(o['data']['config.yaml'] for o in disabled if o['kind'] == 'ConfigMap'
                  and o['metadata']['name'] == 'agentgateway-config')
discovery = yaml.safe_load(api_config)['binds'][0]['listeners'][0]['routes']
assert {r['name'] for r in discovery} == {'models', 'openapi'}
assert json.loads(next(r for r in discovery if r['name'] == 'models')['policies']['directResponse']['body'])['data'] == []
print(json.dumps({'releases': len(releases), 'models_installed_in_cpu_sample': len(names), 'shared_admin_workspace': True,
                  'pinned_workload_images': len(images), 'runtime_tested': False}))
