#!/usr/bin/env python3
"""Opt-in TLS/Bearer qualification of every Omni modality on a deployed lab."""
import argparse
import base64
import json
import os
from pathlib import Path
import ssl
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image', required=True, type=Path, help='Small PNG fixture')
parser.add_argument('--audio', required=True, type=Path, help='Short WAV fixture')
parser.add_argument('--video', required=True, type=Path, help='Short MP4 fixture')
args = parser.parse_args()
origin = os.environ['LAB_ORIGIN']
key = json.loads(Path(os.environ['LAB_CREDENTIALS_FILE']).read_text())['api_key']
context = ssl.create_default_context(cafile=os.environ['LAB_CA_FILE'])


def encoded(path):
    if not 0 < path.stat().st_size <= 16 * 1024 * 1024:
        raise ValueError('Fixture must contain at most 16 MiB')
    return base64.b64encode(path.read_bytes()).decode()


def complete(content, audio=False):
    body = {'model': 'lfm3-omni-2b', 'messages': [{'role': 'user', 'content': content}], 'max_tokens': 64}
    if audio:
        body.update(modalities=['text', 'audio'], audio={'format': 'wav'})
    request = Request(origin + '/v1/chat/completions', data=json.dumps(body).encode(),
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urlopen(request, context=context, timeout=600) as response:
        result = json.load(response)
    assert result['model'] == 'lfm3-omni-2b'
    message = result['choices'][0]['message']
    assert message['content'] or message.get('audio')
    if audio:
        wav = base64.b64decode(message['audio']['data'], validate=True)
        assert len(wav) > 44 and wav[:4] == b'RIFF' and wav[8:12] == b'WAVE'
    assert result['usage']['prompt_tokens'] > 0


complete('Say hello.')
complete([{'type': 'text', 'text': 'Describe this image.'},
          {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + encoded(args.image)}}])
complete([{'type': 'text', 'text': 'Describe this audio.'},
          {'type': 'input_audio', 'input_audio': {'format': 'wav', 'data': encoded(args.audio)}}])
complete([{'type': 'text', 'text': 'Describe this video.'},
          {'type': 'video_url', 'video_url': {'url': 'data:video/mp4;base64,' + encoded(args.video)}}])
complete('Say hello aloud.', audio=True)
print(json.dumps({'model': 'lfm3-omni-2b', 'tls': 'verified',
                  'text': 'passed', 'image': 'passed', 'audio_input': 'passed',
                  'video': 'passed', 'audio_output': 'passed'}))
