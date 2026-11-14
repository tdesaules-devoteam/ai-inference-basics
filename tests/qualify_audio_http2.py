#!/usr/bin/env python3
"""Exercise buffered Omni audio through real TLS/Bearer HTTP/1.1 and HTTP/2 clients."""
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import wave

origin = os.environ['LAB_ORIGIN'].rstrip('/')
key = json.loads(Path(os.environ['LAB_CREDENTIALS_FILE']).read_text())['api_key']
config = 'url = ' + json.dumps(origin + '/v1/chat/completions') + '\n'
config += 'header = ' + json.dumps('Authorization: Bearer ' + key) + '\n'
body = {'model': 'lfm3-omni-2b', 'messages': [
    {'role': 'user', 'content': 'Dis bonjour en français, en une courte phrase.'}],
    'modalities': ['text', 'audio'], 'audio': {'format': 'wav'}, 'max_tokens': 128}
results = []
with tempfile.TemporaryDirectory(prefix='audio-protocol-') as directory:
    root = Path(directory)
    request = root / 'request.json'
    request.write_text(json.dumps(body))
    for flag, expected in [('--http1.1', '1.1'), ('--http2', '2')]:
        output = root / 'response.json'
        result = subprocess.run(['curl', flag, '--silent', '--show-error', '--max-time', '600',
                                 '--cacert', os.environ['LAB_CA_FILE'], '--config', '-',
                                 '-H', 'Content-Type: application/json',
                                 '--data-binary', '@' + str(request), '--output', str(output),
                                 '--write-out', '%{http_code} %{http_version}'],
                                input=config, text=True, capture_output=True, check=True)
        assert result.stdout.split() == ['200', expected], result.stdout
        response = json.loads(output.read_text())
        audio = base64.b64decode(response['choices'][0]['message']['audio']['data'], validate=True)
        with wave.open(io.BytesIO(audio), 'rb') as wav:
            assert wav.getnframes() > 0 and wav.getframerate() == 24000
        results.append({'http_version': expected, 'status': 200, 'wav_bytes': len(audio)})
print(json.dumps({'audio_protocols': results, 'tls': 'verified'}))
