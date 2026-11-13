#!/usr/bin/env python3
"""Run inside a participant terminal; receive models.lock.json on stdin."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.request import urlopen

model = json.load(sys.stdin)['chat']
os.umask(0o077)
with tempfile.TemporaryDirectory(prefix='lab-bench-') as directory:
    target = Path(directory)
    for entry in model['files']:
        if entry['path'] not in ('config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json', 'merges.txt'):
            continue
        with urlopen(f'https://huggingface.co/{model["repository"]}/resolve/{model["revision"]}/{entry["path"]}', timeout=60) as response:
            data = response.read()
        assert len(data) == entry['size'] and hashlib.sha256(data).hexdigest() == entry['sha256']
        (target / entry['path']).write_bytes(data)
    command = ['vllm', 'bench', 'serve', '--backend', 'openai-chat',
               '--base-url', os.environ['OPENAI_BASE_URL'].removesuffix('/v1'),
               '--endpoint', '/v1/chat/completions', '--model', 'ai-inference-basics-chat',
               '--tokenizer', directory, '--dataset-name', 'random', '--num-prompts', '3',
               '--random-input-len', '32', '--random-output-len', '16',
               '--max-concurrency', '1', '--save-result', '--result-dir', directory,
               '--result-filename', 'result.json']
    # CLI logs may include configuration; keep them private and emit selected metrics only.
    with (target / 'bench.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    if result.returncode:
        raise RuntimeError('Bastion benchmark failed; no credentials or command output emitted')
    metrics = json.loads((target / 'result.json').read_text())
    assert metrics['completed'] == 3, 'Benchmark requests failed'
    print(json.dumps({key: metrics[key] for key in ('completed', 'duration', 'request_throughput', 'output_throughput')}))
