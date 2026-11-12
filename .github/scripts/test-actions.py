#!/usr/bin/env python3
"""Exercise fixed-operation Docker actions with positive and negative fixtures."""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import yaml

root = pathlib.Path(__file__).resolve().parents[2]
def action(directory, name, success=True, env=None):
    command = ['podman', 'run', '--rm', '--security-opt', 'label=disable', '--userns=keep-id',
               '-v', f'{directory}:/github/workspace', '-w', '/github/workspace', '-e', 'HOME=/tmp',
               '-e', 'GITHUB_SHA=fixture-source', '-e', 'GITHUB_OUTPUT=/github/workspace/output']
    for key, value in (env or {}).items():
        command += ['-e', f'{key}={value}']
    command += [f'localhost/ai-inference-basics-ci-{name}:dev']
    process = subprocess.run(command, capture_output=True, text=True)
    assert (process.returncode == 0) == success, (name, process.stdout[-2000:], process.stderr[-2000:])
    return process

with tempfile.TemporaryDirectory(prefix='ci-fixture-', dir=root / '.local') as tmp:
    directory = pathlib.Path(tmp)
    for path in ('charts', 'platform/k0s', 'tests'):
        shutil.copytree(root / path, directory / path)
    subprocess.run(['git', 'init', '-q', str(directory)], check=True)
    (directory / 'output').touch()
    (directory / 'docs with spaces.md').write_text('# Fixture\n')
    subprocess.run(['git', '-C', str(directory), 'add', '.'], check=True)
    action(directory, 'check', env={'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/main'})
    assert 'docs with spaces.md' in (directory / 'output').read_text()
    action(directory, 'check', success=False, env={'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_REF': 'refs/heads/other'})
    (directory / 'event.json').write_text(json.dumps({'before': 'a' * 40}))
    action(directory, 'check', success=False, env={'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_PATH': '/github/workspace/event.json'})
    action(directory, 'lint-helm')
    values_path = directory / 'charts/ai-inference-basics/values.yaml'
    original_values = values_path.read_text()
    invalid = yaml.safe_load(original_values)
    invalid['gateway']['envoyImage'] = 'docker.io/envoyproxy/envoy:latest'
    values_path.write_text(yaml.safe_dump(invalid))
    action(directory, 'lint-helm', success=False)
    values_path.write_text(original_values)
    action(directory, 'build-helm')
    action(directory, 'test-helm')
    receipt = json.loads((directory / 'dist/qualification.json').read_text())
    assert receipt['tested'] is True and receipt['source_sha'] == 'fixture-source'
    archive = next((directory / 'dist').glob('*.tgz'))
    archive.write_bytes(archive.read_bytes() + b'corrupt')
    action(directory, 'test-helm', success=False)
    (directory / 'dist/qualification.json').unlink()
    action(directory, 'publish-helm', success=False)
    action(directory, 'fetch-helm', success=False, env={'GITHUB_REF': 'refs/tags/0.3.0'})
report = root / 'reports/local-cpu/G0'
report.mkdir(parents=True, exist_ok=True)
(report / 'docker-actions.json').write_text(json.dumps({
    'platform': 'linux/amd64', 'hosted_execution': False,
    'passed': ['selection', 'wrong_manual_ref_rejected', 'missing_history_rejected',
               'helm_lint', 'mutable_image_rejected', 'archive_package', 'archive_render',
               'corruption_rejected', 'unqualified_publication_rejected', 'missing_oci_receipt_rejected'],
}, indent=2) + '\n')
print('Docker action fixtures passed: selection, wrong-ref, lint, package, exact archive, corruption, unqualified publication, missing OCI receipt.')
