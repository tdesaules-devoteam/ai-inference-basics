#!/usr/bin/env python3
"""Prove a normal workshop workspace cannot bypass protected backends."""
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent
targets = ['http://headlamp/headlamp/', 'http://ai-inference-basics-chat-kserve-workload-svc:8000/v1/models',
           'http://ai-inference-basics-embeddings-predictor/v1/models', 'http://ai-inference-basics-rerank-predictor/v1/models',
           'http://workspace-b:8080/', 'http://telemetry:3000/grafana/']
results = {}
for url in targets:
    response = subprocess.run(['bash', str(root / 'scripts/guest.sh'),
        'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics exec deployment/workspace-a -c terminal -- '
        f'curl -sS --max-time 3 -o /dev/null -w "%{{http_code}}" {url}'],
        capture_output=True)
    assert response.returncode != 0 and response.stdout.strip() == b'000', (url, response.stdout)
    results[url] = 'blocked'
for resource in ('secrets', 'clusterrolebindings'):
    response = subprocess.run(['bash', str(root / 'scripts/guest.sh'),
        'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics exec deployment/workspace-a -c terminal -- '
        f'kubectl auth can-i get {resource} --all-namespaces'], capture_output=True)
    assert response.stdout.strip() == b'no'
    results[resource] = 'denied'
report = root / 'reports/local-cpu/G1'
report.mkdir(parents=True, exist_ok=True)
(report / 'access-isolation.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results))
