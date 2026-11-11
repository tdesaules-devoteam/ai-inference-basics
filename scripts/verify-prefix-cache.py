#!/usr/bin/env python3
"""Measure repeated-prefix cache counters and observed first SSE data latency."""
import json
import pathlib
import re
import runpy
import subprocess
import time
import uuid

root = pathlib.Path(__file__).resolve().parent.parent
key = json.loads((root / '.local/secrets/credentials.json').read_text())['api_key']
def counters():
    raw = subprocess.check_output(['bash', str(root / 'scripts/guest.sh'),
        'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics exec deployment/telemetry -c lgtm -- curl -fsS http://ai-inference-basics-chat-kserve-workload-svc:8000/metrics']).decode()
    return {name: sum(float(v) for v in re.findall(r'^vllm:' + name + r'\{[^\n]*\} ([0-9.e+]+)$', raw, re.M))
            for name in ('prefix_cache_queries_total', 'prefix_cache_hits_total')}

prefix = f'Experiment {uuid.uuid4().hex}. ' + ('Kubernetes schedules Pods and exposes applications through Services. ' * 45)
payload = {'model': 'ai-inference-basics-chat', 'messages': [{'role': 'user', 'content': prefix + 'Reply with one short sentence.'}],
           'stream': True, 'max_tokens': 16, 'temperature': 0, 'chat_template_kwargs': {'enable_thinking': False}}
results = []
for label in ('cold', 'warm', 'warm-repeat'):
    before = counters()
    command = ['curl', '-sS', '-N', '--fail-with-body', '--max-time', '180', '--noproxy', '*',
               '--cacert', str(root / '.local/secrets/tls.crt'), '--resolve', 'lab.ai-inference-basics.test:30443:127.0.0.1',
               '--config', '-', '-H', 'Content-Type: application/json', '--data', json.dumps(payload),
               'https://lab.ai-inference-basics.test:30443/v1/chat/completions']
    start = time.monotonic()
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    process.stdin.write(f'header = "Authorization: Bearer {key}"\n')
    process.stdin.close()
    first = None
    done = False
    for line in process.stdout:
        if line.startswith('data: ') and '[DONE]' not in line:
            event = json.loads(line[6:])
            if any(c.get('delta', {}).get('content') for c in event.get('choices', [])) and first is None:
                first = time.monotonic() - start
        done |= line.strip() == 'data: [DONE]'
    assert process.wait() == 0 and first is not None and done
    after = counters()
    results.append({'run': label, 'observed_first_content_seconds': first,
                    'total_seconds': time.monotonic() - start,
                    'cache_queries_tokens': after['prefix_cache_queries_total'] - before['prefix_cache_queries_total'],
                    'cache_hit_tokens': after['prefix_cache_hits_total'] - before['prefix_cache_hits_total']})
assert results[1]['cache_hit_tokens'] > 0 and results[2]['cache_hit_tokens'] > 0
report = root / 'reports/local-cpu/G2'
report.mkdir(parents=True, exist_ok=True)
(report / 'prefix-cache.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results))
