#!/usr/bin/env python3
"""Render the actual Helmfile and validate storage/foundation contracts.

Requires PyYAML and the pinned Helm/Helmfile on PATH. Fetches upstream charts but
does not contact a Kubernetes cluster or execute deployment hooks.
"""
import json
import re
import subprocess
import hashlib
import tempfile
from urllib.parse import urlsplit
from pathlib import Path

import yaml

root = Path(__file__).resolve().parent.parent
cluster = yaml.safe_load((root / 'platform/k0s/k0s.yaml').read_text())
assert not cluster['spec'].get('extensions', {}).get('helm'), 'Competing k0s Helm deployer configuration'
rendered = subprocess.check_output([
    'helmfile', '-f', str(root / 'platform/helm/helmfile.yaml.gotmpl'), 'template',
], text=True)
objects = list(filter(None, yaml.safe_load_all(rendered)))
owners = set()
images = []
for obj in objects:
    metadata = obj['metadata']
    key = (obj['kind'], metadata.get('namespace', ''), metadata['name'])
    assert key not in owners, f'Duplicate resource: {key}'
    owners.add(key)
    if obj['kind'] in ('Deployment', 'StatefulSet', 'DaemonSet', 'Job'):
        pod = obj['spec']['template']['spec']
        for container in pod.get('initContainers', []) + pod['containers']:
            images.append(container['image'])
    if obj['kind'] == 'Secret':
        # Agent Router generates its own MCP seed; RustFS root credentials remain external.
        assert metadata['namespace'] == 'agent-router'
        assert metadata['name'] == 'agent-router-mcp-session-encryption'
    if obj['kind'] == 'ConfigMap' and 'helperPod.yaml' in obj.get('data', {}):
        helper = yaml.safe_load(obj['data']['helperPod.yaml'])
        images.extend(c['image'] for c in helper['spec']['containers'])

assert all(re.search(r'@sha256:[a-f0-9]{64}$', image) for image in images), images
storage = next(o for o in objects if o['kind'] == 'StorageClass')
assert storage['metadata']['name'] == 'local-path-provisioner'
assert storage['volumeBindingMode'] == 'WaitForFirstConsumer'
assert storage['reclaimPolicy'] == 'Delete'
rustfs = next(o for o in objects if o['kind'] == 'Deployment' and o['metadata']['name'] == 'rustfs')
assert rustfs['metadata']['namespace'] == 'rustfs'
assert rustfs['spec']['replicas'] == 1 and rustfs['spec']['strategy']['type'] == 'Recreate'
assert any(v.get('persistentVolumeClaim', {}).get('claimName') == 'rustfs-data'
           for v in rustfs['spec']['template']['spec']['volumes'])
assert not any(o['kind'] in ('Ingress', 'Gateway', 'StatefulSet') for o in objects)
assert all(o['spec'].get('type', 'ClusterIP') == 'ClusterIP' for o in objects if o['kind'] == 'Service')
pvc = next(o for o in objects if o['kind'] == 'PersistentVolumeClaim')
assert pvc['spec']['storageClassName'] == 'local-path-provisioner'
assert pvc['spec']['resources']['requests']['storage'] == '20Gi'
job = next(o for o in objects if o['kind'] == 'Job' and o['metadata']['name'] == 'rustfs-buckets')
endpoint = next(e['value'] for e in job['spec']['template']['spec']['containers'][0]['env']
                if e['name'] == 'S3_ENDPOINT')
address = urlsplit(endpoint)
assert any(address.hostname == f"{o['metadata']['name']}.{o['metadata']['namespace']}.svc.cluster.local"
           and address.port in [p['port'] for p in o['spec']['ports']]
           for o in objects if o['kind'] == 'Service'), 'S3 endpoint does not match a rendered Service'
assert job['metadata']['annotations']['helm.sh/hook'] == 'post-install,post-upgrade'
assert job['spec']['activeDeadlineSeconds'] == 300
assert job['spec']['ttlSecondsAfterFinished'] == 3600
script = job['spec']['template']['spec']['containers'][0]['args'][0]
subprocess.run(['bash', '-n', '-c', script], check=True)
assert 'for bucket in loki tempo mimir-blocks mimir-ruler mimir-alertmanager models;' in script
assert 'benchmark-results' not in rendered and 'platform-checks' not in rendered
assert not any(o['metadata']['name'] == 'storage-bootstrap' for o in objects)
credential_objects = {o['kind']: o for o in objects if o['metadata']['name'] == 'rustfs-credentials'}
assert set(credential_objects) == {'ServiceAccount', 'Role', 'RoleBinding', 'Job'}
for kind, weight in [('ServiceAccount', '-30'), ('Role', '-20'), ('RoleBinding', '-10'), ('Job', '0')]:
    obj = credential_objects[kind]
    assert obj['metadata']['namespace'] == 'rustfs'
    assert obj['metadata']['annotations']['helm.sh/hook'] == 'pre-install,pre-upgrade'
    assert obj['metadata']['annotations']['helm.sh/hook-weight'] == weight
rules = credential_objects['Role']['rules']
assert rules == [{'apiGroups': [''], 'resources': ['secrets'], 'resourceNames': ['rustfs-root'], 'verbs': ['get']},
                 {'apiGroups': [''], 'resources': ['secrets'], 'verbs': ['create']}]
credential_job = credential_objects['Job']
assert credential_job['spec']['ttlSecondsAfterFinished'] == 3600
assert credential_job['spec']['template']['spec']['serviceAccountName'] == 'rustfs-credentials'
compile(credential_job['spec']['template']['spec']['containers'][0]['args'][0], '<credential-hook>', 'exec')

deployments = {(o['metadata']['namespace'], o['metadata']['name']) for o in objects if o['kind'] == 'Deployment'}
assert {('cert-manager', 'cert-manager'), ('cert-manager', 'cert-manager-webhook'),
        ('cert-manager', 'cert-manager-cainjector'), ('envoy-gateway', 'envoy-gateway'),
        ('agent-router', 'agent-router')} <= deployments
certificate = next(o for o in objects if o['kind'] == 'Certificate')
assert certificate['metadata']['namespace'] == 'agent-router'
assert 'agent-router.agent-router.svc' in certificate['spec']['dnsNames']
gateway_config = next(o for o in objects if o['kind'] == 'ConfigMap' and o['metadata']['namespace'] == 'envoy-gateway')
assert 'agent-router.agent-router.svc.cluster.local' in str(gateway_config['data'])
assert 'envoy-gateway-system' not in rendered and 'envoy-ai-gateway-system' not in rendered

# Build the resolved state as well as the manifests: needs is an orchestration
# property, not visible in Kubernetes YAML.
state = yaml.safe_load(subprocess.check_output([
    'helmfile', '-f', str(root / 'platform/helm/helmfile.yaml.gotmpl'), 'build',
], text=True))
releases = {r['name']: r for r in state['releases']}
assert releases['rustfs']['needs'] == ['local-path-provisioner/local-path-provisioner']
assert set(releases) == {'local-path-provisioner', 'rustfs', 'cert-manager', 'envoy-gateway', 'agent-router-crds', 'agent-router'}
assert set(releases['agent-router']['needs']) == {'cert-manager/cert-manager', 'envoy-gateway/envoy-gateway', 'agent-router/agent-router-crds'}
assert state['helmDefaults']['wait'] and state['helmDefaults']['waitForJobs']
# build resolves OCI references to the Helmfile cache. Validate declared references separately.
declared = yaml.safe_load((root / 'platform/helm/helmfile.yaml.gotmpl').read_text())
for release in declared['releases']:
    if release['name'] == 'rustfs':
        assert release['chart'] == 'rustfs/rustfs' and release['version'] == '1.0.5'
    else:
        assert re.fullmatch(r'oci://.+@sha256:[a-f0-9]{64}', release['chart'])
# HTTP charts are version-pinned, not addressed by OCI manifest digest. Verify
# the qualified archive independently without adding a deployment downloader.
with tempfile.TemporaryDirectory() as directory:
    subprocess.run(['helm', 'pull', 'rustfs', '--repo', 'https://charts.rustfs.com',
                    '--version', '1.0.5', '--destination', directory], check=True)
    assert hashlib.sha256((Path(directory) / 'rustfs-1.0.5.tgz').read_bytes()).hexdigest() == '9b074f7a2d2143246b3e2ef9908c6791bbf05009766294a20e5a558bb44a6d96'
print(json.dumps({'releases': len(releases), 'pinned_images': len(images),
                  'storage_contract': 'valid', 'runtime_tested': False}))
