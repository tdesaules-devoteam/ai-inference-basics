#!/usr/bin/env python3
"""Render the actual Helmfile and validate storage ownership and image contracts.

Requires PyYAML, the pinned Helm/Helmfile on PATH and PLATFORM_ARTIFACTS populated
from platform/helm/artifacts.lock. Does not contact a Kubernetes cluster.
"""
import json
import re
import subprocess
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
        raise AssertionError('Credentials must not be rendered into Helm values or manifests')
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
job = next(o for o in objects if o['kind'] == 'Job')
endpoint = next(e['value'] for e in job['spec']['template']['spec']['containers'][0]['env']
                if e['name'] == 'S3_ENDPOINT')
address = urlsplit(endpoint)
assert any(address.hostname == f"{o['metadata']['name']}.{o['metadata']['namespace']}.svc.cluster.local"
           and address.port in [p['port'] for p in o['spec']['ports']]
           for o in objects if o['kind'] == 'Service'), 'S3 endpoint does not match a rendered Service'
assert job['metadata']['annotations']['helm.sh/hook'] == 'post-install,post-upgrade'
assert job['spec']['activeDeadlineSeconds'] == 300
subprocess.run(['bash', '-n', '-c', job['spec']['template']['spec']['containers'][0]['args'][0]], check=True)

# Build the resolved state as well as the manifests: needs is an orchestration
# property, not visible in Kubernetes YAML.
state = yaml.safe_load(subprocess.check_output([
    'helmfile', '-f', str(root / 'platform/helm/helmfile.yaml.gotmpl'), 'build',
], text=True))
releases = {r['name']: r for r in state['releases']}
assert releases['rustfs']['needs'] == ['local-path-provisioner/local-path-provisioner']
assert releases['storage-bootstrap']['needs'] == ['rustfs/rustfs']
assert state['helmDefaults']['wait'] and state['helmDefaults']['waitForJobs']
print(json.dumps({'releases': len(releases), 'pinned_images': len(images),
                  'storage_contract': 'valid', 'runtime_tested': False}))
