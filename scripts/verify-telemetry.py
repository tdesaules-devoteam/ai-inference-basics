#!/usr/bin/env python3
"""Verify all three OTel ingestion paths and a real gateway scrape."""
import json
import pathlib
import subprocess
import time
import urllib.parse
import uuid
import runpy

root = pathlib.Path(__file__).resolve().parent.parent
def request(url, body=None):
    command = 'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics exec -i deployment/telemetry -c lgtm -- curl -fsS '
    if body is not None:
        command += "-H 'Content-Type: application/json' --data-binary @- "
    result = subprocess.run(['bash', str(root / 'scripts/guest.sh'), command + "'" + url + "'"],
                            input=json.dumps(body).encode() if body is not None else None,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return json.loads(result.stdout)

now = time.time_ns()
trace = uuid.uuid4().hex
resource = {'attributes': [{'key': 'service.name', 'value': {'stringValue': 'ai-inference-basics-smoke'}}]}
request('http://telemetry:4318/v1/traces', {'resourceSpans': [{
    'resource': resource, 'scopeSpans': [{'scope': {'name': 'ai-inference-basics-smoke'}, 'spans': [{
        'traceId': trace, 'spanId': uuid.uuid4().hex[:16], 'name': 'pipeline-smoke', 'kind': 1,
        'startTimeUnixNano': str(now), 'endTimeUnixNano': str(now + 1000000),
    }]}],
}]})
request('http://telemetry:4318/v1/logs', {'resourceLogs': [{
    'resource': resource, 'scopeLogs': [{'logRecords': [{
        'timeUnixNano': str(now), 'severityText': 'INFO',
        'body': {'stringValue': 'AI Inference Basics telemetry pipeline smoke'},
    }]}],
}]})

def eventually(check, timeout=90):
    deadline = time.monotonic() + timeout
    while True:
        try:
            result = check()
            if result:
                return result
        except (subprocess.CalledProcessError, KeyError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('Telemetry evidence did not arrive before timeout')
        time.sleep(3)

metric = eventually(lambda: request('http://telemetry:9090/api/v1/query?' + urllib.parse.urlencode({'query': 'up{job="envoy-gateway"}'}))['data']['result'])
assert any(float(x['value'][1]) == 1 for x in metric)
logs = eventually(lambda: request('http://telemetry:3100/loki/api/v1/query_range?' + urllib.parse.urlencode({'query': '{service_name="ai-inference-basics-smoke"}', 'limit': 10}))['data']['result'])
span = eventually(lambda: request('http://telemetry:3200/api/traces/' + trace))
model_trace = uuid.uuid4().hex
call_model = runpy.run_path(str(root / 'scripts/verify-models.py'))['request']
status, _, _ = call_model('/v1/chat/completions', {
    'model': 'ai-inference-basics-chat', 'messages': [{'role': 'user', 'content': 'Say hello.'}],
    'max_tokens': 8, 'chat_template_kwargs': {'enable_thinking': False},
}, trace_id=model_trace)
assert status == 200
def correlated():
    data = request('http://telemetry:3200/api/traces/' + model_trace)
    services = set()
    def walk(node):
        if isinstance(node, dict):
            for a in node.get('resource', {}).get('attributes', []):
                if a.get('key') == 'service.name':
                    services.add(a['value']['stringValue'])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(data)
    return sorted(services) if {'agent-router', 'ai-inference-basics-chat'}.issubset(services) else None
services = eventually(correlated)
result = {'gateway_scrape_up': True, 'otlp_log_retrieved': bool(logs),
          'otlp_trace_retrieved': bool(span), 'trace_id': trace,
          'model_trace_id': model_trace, 'correlated_services': services,
          'scope': 'Collector/backend pipeline plus correlated public chat request'}
report = root / 'reports/local-cpu/G3'
report.mkdir(parents=True, exist_ok=True)
(report / 'telemetry.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
