#!/usr/bin/env python3
"""Exercise public API-key enforcement, model semantics and chat streaming."""
import json
import math
import pathlib
import subprocess
import time

root = pathlib.Path(__file__).resolve().parent.parent
key = json.loads((root / '.local/secrets/credentials.json').read_text())['api_key']
def request(path, payload, credential=key, trace_id=None):
    cmd = ['curl', '--silent', '--show-error', '--noproxy', '*', '--max-time', '180',
           '--cacert', str(root / '.local/secrets/tls.crt'), '--resolve', 'lab.ai-inference-basics.test:30443:127.0.0.1',
           '--config', '-', '-H', 'Content-Type: application/json', '--data', json.dumps(payload),
           '-w', '\n%{http_code}', 'https://lab.ai-inference-basics.test:30443' + path]
    if trace_id:
        cmd[1:1] = ['-H', f'traceparent: 00-{trace_id}-0123456789abcdef-01']
    config = f'header = "Authorization: Bearer {credential}"\n' if credential else ''
    started = time.monotonic()
    result = subprocess.run(cmd, input=config.encode(), stdout=subprocess.PIPE, check=True)
    body, status = result.stdout.decode().rsplit('\n', 1)
    return int(status), body, time.monotonic() - started

def verify():
    checks = [
        ('/v1/chat/completions', {'model': 'ai-inference-basics-chat', 'messages': [{'role': 'user', 'content': 'Reply with hello.'}], 'max_tokens': 16, 'chat_template_kwargs': {'enable_thinking': False}}),
        ('/v1/embeddings', {'model': 'ai-inference-basics-embeddings', 'input': 'Kubernetes serves model inference.'}),
        ('/cohere/v2/rerank', {'model': 'ai-inference-basics-rerank', 'query': 'What orchestrates containers?', 'documents': ['Kubernetes orchestrates container workloads.', 'Bananas are yellow fruit.']}),
    ]
    results = {}
    for path, payload in checks:
        for bad in (None, 'incorrect-key'):
            status, _, _ = request(path, payload, bad)
            assert status == 401, (path, 'unauthorized status', status)
        status, body, elapsed = request(path, payload)
        assert status == 200, (path, status, body[:500])
        data = json.loads(body)
        if 'chat' in path:
            assert data['choices'][0]['message']['content']
        elif 'embeddings' in path:
            vector = data['data'][0]['embedding']
            assert len(vector) == 1024 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector)
            again = json.loads(request(path, payload)[1])['data'][0]['embedding']
            assert max(abs(a - b) for a, b in zip(vector, again)) < 1e-5
        else:
            assert len(data['results']) == 2
            assert data['results'][0]['index'] == 0, data
            scores = {candidate['index']: candidate['relevance_score'] for candidate in data['results']}
            assert math.isfinite(scores[0]) and math.isfinite(scores[1]) and scores[0] > scores[1], scores
        results[path] = {'status': status, 'seconds': elapsed, 'missing_and_wrong_key': 401}
    payload = dict(checks[0][1], stream=True)
    status, body, elapsed = request(checks[0][0], payload)
    assert status == 200 and 'data: [DONE]' in body, body[:500]
    chunks = [json.loads(line[6:]) for line in body.splitlines() if line.startswith('data: ') and line != 'data: [DONE]']
    assert chunks and any(c.get('choices') for c in chunks)
    assert any(c.get('finish_reason') in ('stop', 'length') for chunk in chunks for c in chunk.get('choices', []))
    results['streaming'] = {'valid_sse': True, 'terminated': True, 'chunks': len(chunks), 'seconds': elapsed}
    report = root / 'reports/local-cpu/G2'
    report.mkdir(parents=True, exist_ok=True)
    (report / 'models.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results))

if __name__ == '__main__':
    verify()
