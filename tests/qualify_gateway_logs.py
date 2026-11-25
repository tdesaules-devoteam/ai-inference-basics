#!/usr/bin/env python3
"""Verify actual agentgateway token accounting and supplied/generated request IDs."""
import getpass
import json
import os
from pathlib import Path
import ssl
import subprocess
import time
from urllib.request import Request, urlopen
import uuid

root = Path(__file__).resolve().parent.parent
origin = os.environ['LAB_API_ORIGIN']
key = json.loads(Path(os.environ['LAB_CREDENTIALS_FILE']).read_text())['api_key']
tls = ssl.create_default_context(cafile=os.environ['LAB_CA_FILE'])
host = os.environ.get('LAB_SSH_HOST', getpass.getuser() + '@' + (root / '.devenv/.uuid').read_text().strip() + '.local')
ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
       '-o', 'UserKnownHostsFile=' + os.environ.get('LAB_KNOWN_HOSTS', str(Path.home() / '.ssh/known_hosts')), '-o', 'LogLevel=ERROR', '-o', 'ProxyCommand=none', host]
checks = []
for stream, supplied in ((False, True), (True, True), (False, False)):
    marker = 'lab-log-check/' + uuid.uuid4().hex
    request_id = 'client-' + uuid.uuid4().hex if supplied else None
    body = {'model': 'qwen3-0-6b', 'messages': [{'role': 'user', 'content': 'Reply only OK.'}],
            'max_tokens': 16, 'temperature': 0, 'chat_template_kwargs': {'enable_thinking': False}}
    if stream:
        body.update(stream=True, stream_options={'include_usage': True})
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key, 'User-Agent': marker}
    if request_id:
        headers['X-Request-ID'] = request_id
    with urlopen(Request(origin + '/v1/chat/completions?qualification=not-in-access-log',
                         data=json.dumps(body).encode(), headers=headers), context=tls, timeout=180) as response:
        payload = response.read().decode()
    if stream:
        events = [json.loads(line[6:]) for line in payload.splitlines() if line.startswith('data: ') and line != 'data: [DONE]']
        usage = next(e['usage'] for e in reversed(events) if e.get('usage'))
    else:
        usage = json.loads(payload)['usage']
    checks.append((marker, request_id, usage))

deadline = time.monotonic() + 30
while True:
    raw = subprocess.check_output(ssh + ['kubectl -n agentgateway logs deployment/agentgateway -c agentgateway --since=5m'], text=True)
    logs = []
    for line in raw.splitlines():
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    selected = {entry.get('user_agent'): entry for entry in logs}
    if all(marker in selected for marker, _, _ in checks):
        break
    if time.monotonic() > deadline:
        raise AssertionError('Expected structured access log entries were not emitted')
    time.sleep(1)
for marker, supplied, usage in checks:
    entry = selected[marker]
    assert entry['response_code'] == 200
    assert entry['path'] == '/v1/chat/completions'
    assert entry['model'] == 'qwen3-0-6b'
    if supplied:
        assert entry['request_id'] == supplied, 'Client request ID was changed'
    else:
        uuid.UUID(entry['request_id'])
    for field, key in [('input_tokens', 'prompt_tokens'), ('output_tokens', 'completion_tokens'), ('total_tokens', 'total_tokens')]:
        assert entry[field] == usage[key], (field, entry[field], usage[key])
print('Agentgateway JSON logs match chat/SSE token usage, preserve client IDs, generate missing IDs and omit query strings.')
