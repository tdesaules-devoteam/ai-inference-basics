#!/usr/bin/env python3
"""Offline validation of the ordered k0s Helm-deployer contract."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
import yaml

parser = argparse.ArgumentParser()
parser.add_argument('--chart', default='charts/ai-inference-basics')
args = parser.parse_args()
config = yaml.safe_load(Path('platform/k0s/k0s.yaml').read_text())
charts = config['spec']['extensions']['helm']['charts']
assert config['spec']['extensions']['helm']['concurrencyLevel'] == 1
assert [c['order'] for c in charts] == [1, 2, 3, 4]
assert len({c['name'] for c in charts}) == 4
owners = {}
image_count = 0
with tempfile.TemporaryDirectory(prefix='ai-inference-basics-validation-') as temporary:
    for chart in charts:
        assert chart['forceUpgrade'] is False
        assert chart['chartname'] == '/var/lib/k0s/charts/ai-inference-basics.tgz'
        # Synthetic digest is a render fixture, never a deployment artifact.
        values = chart['values'].replace('__LAB_HOSTNAME__', 'test-vm.local').replace(
            '__BASTION_IMAGE__', 'localhost/ai-inference-basics-bastion@sha256:' + 'a' * 64)
        file = Path(temporary) / (chart['name'] + '.yaml')
        file.write_text(values)
        subprocess.run(['helm', 'lint', '--strict', args.chart, '-f', str(file)], check=True)
        rendered = subprocess.check_output(['helm', 'template', chart['name'], args.chart,
            '--namespace', chart['namespace'], '--kube-version', '1.37.2', '-f', str(file)])
        for obj in filter(None, yaml.safe_load_all(rendered)):
            metadata = obj['metadata']
            key = (obj['apiVersion'], obj['kind'], metadata.get('namespace', chart['namespace']), metadata['name'])
            assert key not in owners or owners[key] == chart['name'], f'Cross-release ownership conflict: {key}'
            owners[key] = chart['name']
            if obj['kind'] in ('Deployment', 'StatefulSet', 'DaemonSet', 'Job'):
                for container in obj['spec']['template']['spec'].get('initContainers', []) + obj['spec']['template']['spec']['containers']:
                    assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', container['name']), container['name']
                    assert re.search(r'@sha256:[a-f0-9]{64}$', container['image']), container['image']
                    image_count += 1
            if obj['kind'] == 'LLMInferenceService':
                assert not obj['spec'].get('router', {}).get('scheduler')
                assert re.search(r':[a-f0-9]{40}$', obj['spec']['model']['uri'])
print(json.dumps({'ordered_releases': len(charts), 'workload_images_pinned': image_count,
                  'cross_release_ownership': 'valid', 'runtime_tested': False}))
