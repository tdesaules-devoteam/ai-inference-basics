#!/usr/bin/env python3
"""Authoring tool: lock the selected public model snapshots, including file SHA-256."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

MODELS = {
    'chat': ('Qwen/Qwen3-0.6B', 'c1899de289a04d12100db370d81485cdf75e47ca'),
    'embeddings': ('Qwen/Qwen3-Embedding-0.6B', '97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'),
    'rerank': ('Qwen/Qwen3-Reranker-0.6B', 'e61197ed45024b0ed8a2d74b80b4d909f1255473'),
}
result = {}
for name, (repository, revision) in MODELS.items():
    with urlopen(f'https://huggingface.co/api/models/{repository}/revision/{revision}?blobs=true', timeout=60) as response:
        metadata = json.load(response)
    assert metadata['sha'] == revision
    files = []
    for item in metadata['siblings']:
        path = item['rfilename']
        if path.startswith(('onnx/', 'openvino/')):
            continue
        if not (path.endswith(('.json', '.safetensors', '.txt', '.jinja')) or path in ('LICENSE', 'README.md')):
            continue
        assert '..' not in Path(path).parts and not path.startswith('/')
        checksum = item.get('lfs', {}).get('sha256')
        if not checksum:
            with urlopen(f'https://huggingface.co/{repository}/resolve/{revision}/{quote(path)}', timeout=60) as response:
                data = response.read()
            assert len(data) == item['size']
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == item['blobId']
            checksum = hashlib.sha256(data).hexdigest()
        files.append({'path': path, 'size': item['size'], 'sha256': checksum})
    result[name] = {'repository': repository, 'revision': revision, 'files': files}
charts = Path(__file__).resolve().parent.parent / 'charts'
names = {'chat': 'qwen3-0-6b', 'embeddings': 'qwen3-embedding-0-6b', 'rerank': 'qwen3-reranker-0-6b'}
for task, snapshot in result.items():
    destination = charts / names[task] / 'files/model.lock.json'
    destination.write_text(json.dumps(snapshot, indent=2) + '\n')
print({name: sum(f['size'] for f in model['files']) for name, model in result.items()})
