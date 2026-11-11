#!/usr/bin/env python3
"""Check rendered workload images, names and the no-EPP serving contract."""
import re
import os
import pathlib
import shutil
import subprocess
import tempfile
import yaml

# Reproduce dependencies in an isolated copy: lint must not rewrite source archives.
with tempfile.TemporaryDirectory(prefix='ai-inference-basics-dependencies-') as temporary:
    target = pathlib.Path(temporary) / 'chart'
    shutil.copytree('charts/ai-inference-basics', target)
    env = dict(os.environ, HELM_REPOSITORY_CONFIG=temporary + '/repositories.yaml',
               HELM_REPOSITORY_CACHE=temporary + '/repository-cache')
    metadata = yaml.safe_load((target / 'Chart.yaml').read_text())
    for dependency in metadata['dependencies']:
        if dependency['repository'].startswith('https://'):
            subprocess.run(['helm', 'repo', 'add', dependency['name'], dependency['repository']], env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['helm', 'dependency', 'build', str(target)], env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['sha256sum', '-c', 'dependencies.sha256'], cwd=target, check=True, stdout=subprocess.DEVNULL)

flags = [
    'envoyGateway', 'cert-manager', 'dex', 'headlamp', 'access', 'gateway',
    'kserveCRDs', 'llmCRDs', 'aiCRDs', 'kserveController', 'llmController',
    'agent-router', 'models', 'api', 'observability',
]
documents = []
for profile in ('local-cpu', 'scaleway-cpu-pilot', 'scaleway-h100'):
    command = ['helm', 'template', 'ai-inference-basics', 'charts/ai-inference-basics', '--namespace', 'ai-inference-basics', '-f', 'profiles/' + profile + '.yaml']
    for flag in flags + (['hami', 'dcgm-exporter'] if profile == 'scaleway-h100' else []):
        command += ['--set', flag + '.enabled=true']
    documents.extend(yaml.safe_load_all(subprocess.check_output(command)))
count = 0
for obj in filter(None, documents):
    name = obj.get('metadata', {}).get('name', '')
    if obj['kind'] in ('Deployment', 'DaemonSet', 'StatefulSet', 'Job', 'Service', 'ServiceAccount', 'Namespace'):
        assert re.fullmatch(r'[a-z0-9][a-z0-9.-]*', name), name
    if obj['kind'] in ('Deployment', 'DaemonSet', 'StatefulSet', 'Job'):
        spec = obj['spec']['template']['spec']
        for container in spec.get('initContainers', []) + spec.get('containers', []):
            assert re.fullmatch(r'[a-z0-9][a-z0-9-]*', container['name']), container['name']
            image = container['image']
            assert re.search(r'@sha256:[a-f0-9]{64}$', image), image
            count += 1
    if obj['kind'] == 'LLMInferenceService':
        assert not obj['spec'].get('router', {}).get('scheduler'), 'EPP is outside scope'
        assert re.search(r':[a-f0-9]{40}$', obj['spec']['model']['uri'])
    if obj['kind'] == 'InferenceService':
        for container in obj['spec']['predictor']['containers']:
            assert re.search(r'@sha256:[a-f0-9]{64}$', container['image'])
            count += 1
print(f'Validated {count} workload image pins and resource names; runtime acceptance is separate.')
