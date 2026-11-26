#!/usr/bin/env python3
"""Exercise real Bearer-authenticated model APIs; credentials stay in a private input file."""
import json
import math
import os
from pathlib import Path
import ssl
from urllib.error import HTTPError
from urllib.request import Request, urlopen

origin = os.environ['LAB_API_ORIGIN']
key = json.loads(Path(os.environ['LAB_CREDENTIALS_FILE']).read_text())['api_key']
context = ssl.create_default_context(cafile=os.environ.get('LAB_CA_FILE')) if origin.startswith('https://') else None


def request(path, body, token=key):
    headers = {'Content-Type': 'application/json'}
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    return urlopen(Request(origin + path, data=json.dumps(body).encode() if body is not None else None, headers=headers), context=context, timeout=180)


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
with request('/v2/rerank', {'model': 'qwen3-reranker-0-6b', 'query': 'What is the capital of France?',
                                  'documents': ['Paris is the capital of France.', 'Berlin is in Germany.'], 'top_n': 2}) as response:
    rerank = json.load(response)['results']
assert len(rerank) == 2 and rerank[0]['index'] == 0
assert all(math.isfinite(row['relevance_score']) for row in rerank)
with request('/openapi.json', None, None) as response:
    assert response.headers.get_content_type() == 'application/json'
    spec = json.load(response)
assert set(spec['paths']) == {'/v1/chat/completions', '/v1/responses', '/v1/embeddings', '/v2/rerank', '/score', '/v1/models', '/openapi.json'}
with request('/v1/models', None) as response:
    assert {m['id'] for m in json.load(response)['data']} == {'qwen3-0-6b', 'qwen3-embedding-0-6b', 'qwen3-reranker-0-6b'}
for path, body, code in [('/v1/models', None, 401), ('/score', {}, 401), ('/v1/responses', {}, 401), ('/v1/completions', {}, 404)]:
    try:
        request(path, body, None)
    except HTTPError as error:
        assert error.code == code, (path, error.code)
    else:
        raise AssertionError(f'Unexpected access to {path}')
body = {'model': chat['model'], 'input': 'Say hello.', 'max_output_tokens': 32, 'store': False}
with request('/v1/responses', body) as response:
    assert json.load(response)['object'] == 'response'
with request('/v1/responses', body | {'stream': True}) as response:
    events = response.read().decode()
    assert 'response.created' in events and any(t in events for t in ('response.completed', 'response.incomplete'))
# Publisher's two example pairs, plus their crossed negatives. Reference values
# are softmax([no, yes])[yes] from the pinned BF16 checkpoint in Transformers.
documents = ['The capital of China is Beijing.',
             'Gravity is a force that attracts two bodies towards each other. It gives weight to physical objects and is responsible for the movement of planets around the sun.']
for query, reference in [('What is the capital of China?', [0.9995122, 0.00000525]),
                         ('Explain gravity', [0.00004909, 0.9993333])]:
    model = {'model': 'qwen3-reranker-0-6b'}
    with request('/v2/rerank', model | {'query': query, 'documents': documents}) as response:
        ranked = json.load(response)['results']
    assert [item['index'] for item in ranked] == sorted(range(2), key=reference.__getitem__, reverse=True)
    for item in ranked:
        i = item['index']
        with request('/score', model | {'text_1': query, 'text_2': documents[i]}) as response:
            score = json.load(response)['data'][0]['score']
        assert abs(score - item['relevance_score']) < 0.001
        assert abs(score - reference[i]) < 0.01, (query, i, score, reference[i])
        print(f'Rerank reference: document={i}, score={score:.6f}, expected={reference[i]:.6f}')
print(json.dumps({'transport': origin.split(':', 1)[0], 'bearer_rejection': 'passed', 'chat': 'passed',
                  'sse': 'passed', 'embedding_dimensions': len(embeddings[0]['embedding']), 'rerank': 'passed',
                  'responses_and_sse': 'passed', 'score': 'passed', 'catalog': 'passed', 'openapi': 'passed'}))
