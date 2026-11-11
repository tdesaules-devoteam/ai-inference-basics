#!/usr/bin/env python3
"""Record allowlisted cluster/version facts, excluding credentials and addresses."""
import datetime
import json
import pathlib
import subprocess
import yaml

root = pathlib.Path(__file__).resolve().parent.parent
def guest(command):
    return subprocess.check_output(['bash', str(root / 'scripts/guest.sh'), command]).decode()
nodes = json.loads(guest('sudo /usr/local/bin/k0s kubectl get nodes -o json'))
pods = json.loads(guest('sudo /usr/local/bin/k0s kubectl get pods -A -o json'))
models = json.loads(guest('sudo /usr/local/bin/k0s kubectl -n ai-inference-basics get llmisvc,isvc -o json'))
report = root / 'reports/local-cpu/G1'
report.mkdir(parents=True, exist_ok=True)
result = {
    'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'cpu_features': [flag for flag in ('avx2', 'avx512f', 'avx512_bf16')
                     if flag in guest("grep -m1 '^flags' /proc/cpuinfo").split()],
    'nodes': [{'os': n['status']['nodeInfo']['osImage'], 'kubelet': n['status']['nodeInfo']['kubeletVersion'],
               'runtime': n['status']['nodeInfo']['containerRuntimeVersion'],
               'cpu': n['status']['capacity']['cpu'], 'memory': n['status']['capacity']['memory'],
               'ready': next(c['status'] for c in n['status']['conditions'] if c['type'] == 'Ready')}
              for n in nodes['items']],
    'workloads': [{'namespace': p['metadata']['namespace'], 'name': p['metadata']['name'],
                   'phase': p['status']['phase'],
                   'ready': all(c.get('ready', False) for c in p['status'].get('containerStatuses', [])),
                   'images': [c['image'] for c in p['spec'].get('initContainers', []) + p['spec']['containers']]}
                  for p in pods['items'] if p['status']['phase'] != 'Succeeded'],
    'models': [{'kind': m['kind'], 'name': m['metadata']['name'],
                'ready': next((c['status'] for c in m.get('status', {}).get('conditions', []) if c['type'] == 'Ready'), 'Unknown')}
               for m in models['items']],
    'disk': guest("df -h --output=size,used,avail,pcent /var | tail -1").strip(),
}
(report / 'runtime.json').write_text(json.dumps(result, indent=2) + '\n')
values = yaml.safe_load((root / 'charts/ai-inference-basics/values.yaml').read_text())
images = set()
def walk(node):
    if isinstance(node, str) and '@sha256:' in node:
        images.add(node)
    elif isinstance(node, dict):
        for v in node.values(): walk(v)
    elif isinstance(node, list):
        for v in node: walk(v)
walk(values)
g0 = root / 'reports/local-cpu/G0'
g0.mkdir(parents=True, exist_ok=True)
(g0 / 'dependencies.json').write_text(json.dumps({
    'chart': yaml.safe_load((root / 'charts/ai-inference-basics/Chart.yaml').read_text()),
    'image_references_and_tags': sorted(images),
    'cpu_model_pins': values['models'],
    'archive_checksums': (root / 'charts/ai-inference-basics/dependencies.sha256').read_text().splitlines(),
    'workspace': json.loads((root / '.local/workspace-image.json').read_text()),
}, indent=2) + '\n')
print('Sanitized runtime and dependency evidence recorded under reports/local-cpu/.')
