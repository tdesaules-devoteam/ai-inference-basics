#!/usr/bin/env python3
"""Exercise real TLS/Bearer model APIs; credentials stay in a private input file."""
import json
import math
import os
from pathlib import Path
import ssl
from urllib.error import HTTPError
from urllib.request import Request, urlopen

origin = os.environ['LAB_API_ORIGIN']
key = json.loads(Path(os.environ['LAB_CREDENTIALS_FILE']).read_text())['api_key']
context = ssl.create_default_context(cafile=os.environ['LAB_CA_FILE'])


def request(path, body, token=key):
    headers = {'Content-Type': 'application/json'}
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    return urlopen(Request(origin + path, data=json.dumps(body).encode(), headers=headers), context=context, timeout=180)


chat = {'model': 'qwen3-0-6b', 'messages': [{'role': 'user', 'content': 'Reply only OK.'}],
        'max_tokens': 64, 'temperature': 0, 'chat_template_kwargs': {'enable_thinking': False}}
# Web and API ports must remain isolated even on the same hostname.
for url, body in ((os.environ['LAB_ORIGIN'] + '/v1/chat/completions', json.dumps(chat).encode()),
                  (origin + '/grafana/', None)):
    try:
        urlopen(Request(url, data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}), context=context, timeout=15)
    except HTTPError as error:
        assert error.code == 404, (url, error.code)
    else:
        raise AssertionError('Unexpected cross-gateway route: ' + url)
for token in (None, 'invalid-lab-key'):
    try:
        request('/v1/chat/completions', chat, token)
    except HTTPError as error:
        assert error.code == 401, error.code
        error.close()
    else:
        raise AssertionError('Missing/invalid Bearer key was accepted')
try:
    request('/v1/chat/completions', chat | {'model': 'not-installed'})
except HTTPError as error:
    assert error.code in (400, 403, 404), error.code
    error.close()
else:
    raise AssertionError('An unknown model was silently routed to chat')
with request('/v1/chat/completions', chat) as response:
    result = json.load(response)
assert result['choices'][0]['message']['content']
with request('/v1/chat/completions', chat | {'stream': True, 'max_tokens': 8}) as response:
    events = response.read().decode()
assert 'data: [DONE]' in events and '"choices"' in events
with request('/v1/embeddings', {'model': 'qwen3-embedding-0-6b', 'input': ['hello', 'world']}) as response:
    embeddings = json.load(response)['data']
assert len(embeddings) == 2 and len(embeddings[0]['embedding']) > 0
assert all(math.isfinite(x) for row in embeddings for x in row['embedding'])
with request('/cohere/v2/rerank', {'model': 'qwen3-reranker-0-6b', 'query': 'What is the capital of France?',
                                  'documents': ['Paris is the capital of France.', 'Berlin is in Germany.'], 'top_n': 2}) as response:
    rerank = json.load(response)['results']
assert len(rerank) == 2 and rerank[0]['index'] == 0
assert all(math.isfinite(row['relevance_score']) for row in rerank)
print(json.dumps({'tls': 'verified', 'bearer_rejection': 'passed', 'chat': 'passed',
                  'sse': 'passed', 'embedding_dimensions': len(embeddings[0]['embedding']), 'rerank': 'passed'}))
