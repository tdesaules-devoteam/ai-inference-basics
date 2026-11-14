"""Bounded OpenAI-style adapter for a pinned, local LFM3-Omni Transformers snapshot."""
import base64
from contextlib import asynccontextmanager
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from PIL import Image

MODEL_NAME = 'lfm3-omni-2b'
MAX_INPUT_TOKENS = int(os.environ.get('MAX_INPUT_TOKENS', '2048'))
MAX_OUTPUT_TOKENS = int(os.environ.get('MAX_OUTPUT_TOKENS', '128'))
gate = threading.Lock()
model = processor = None


@asynccontextmanager
async def lifespan(app):
    global model, processor
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    torch.set_num_threads(int(os.environ.get('OMP_NUM_THREADS', '8')))
    path = os.environ.get('MODEL_PATH', '/mnt/models')
    model = AutoModelForImageTextToText.from_pretrained(
        path, trust_remote_code=True, local_files_only=True, device_map='auto',
        dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32).eval()
    processor = AutoProcessor.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    yield


app = FastAPI(lifespan=lifespan)


@app.get('/health')
def health():
    if model is None:
        raise HTTPException(503, 'Model is loading')
    return {'status': 'ready', 'model': MODEL_NAME}


@app.get('/v1/models')
def models():
    return {'object': 'list', 'data': [{'id': MODEL_NAME, 'object': 'model', 'owned_by': 'LiquidAI'}]}


def decode_data(value, media):
    if not isinstance(value, str) or not value.startswith('data:' + media + '/') or ';base64,' not in value:
        raise HTTPException(400, f'Use an inline base64 data:{media}/ URI')
    try:
        data = base64.b64decode(value.split(',', 1)[1], validate=True)
    except ValueError:
        raise HTTPException(400, 'Invalid base64 media') from None
    if len(data) > 16 * 1024 * 1024:
        raise HTTPException(413, 'Media exceeds 16 MiB')
    return data


def conversation(messages, directory):
    if not isinstance(messages, list) or not messages:
        raise HTTPException(400, 'messages must be a nonempty array')
    result = []
    for message in messages:
        role = message.get('role')
        if role not in ('system', 'user', 'assistant'):
            raise HTTPException(400, 'Supported roles: system, user, assistant')
        content = message.get('content')
        if isinstance(content, str):
            result.append({'role': role, 'content': content})
            continue
        if not isinstance(content, list):
            raise HTTPException(400, 'content must be text or a list of media parts')
        parts = []
        for index, item in enumerate(content):
            kind = item.get('type')
            if kind == 'text':
                parts.append({'type': 'text', 'text': item['text']})
            elif kind == 'image_url':
                data = decode_data(item['image_url']['url'], 'image')
                image = Image.open(io.BytesIO(data)).convert('RGB')
                image.thumbnail((512, 512))
                parts.append({'type': 'image', 'image': image})
            elif kind == 'input_audio':
                audio = item['input_audio']
                if audio.get('format') != 'wav':
                    raise HTTPException(400, 'Input audio must be WAV')
                data = decode_data('data:audio/wav;base64,' + audio['data'], 'audio')
                import soundfile as sf
                samples, rate = sf.read(io.BytesIO(data))
                if len(samples) / rate > 30:
                    raise HTTPException(400, 'Input audio is limited to 30 seconds')
                path = directory / (str(len(result)) + '-' + str(index) + '.wav')
                path.write_bytes(data)
                parts.append({'type': 'audio', 'audio': str(path)})
            elif kind == 'video_url':
                data = decode_data(item['video_url']['url'], 'video')
                path = directory / (str(len(result)) + '-' + str(index) + '.mp4')
                path.write_bytes(data)
                parts.append({'type': 'video', 'video': str(path)})
            else:
                raise HTTPException(400, 'Supported parts: text, image_url, input_audio, video_url')
        result.append({'role': role, 'content': parts})
    return result


@app.post('/v1/chat/completions')
def completions(body: dict):
    import torch
    if body.get('model') != MODEL_NAME:
        raise HTTPException(404, 'Unknown model')
    if body.get('stream'):
        raise HTTPException(400, 'This Transformers adapter returns complete responses; streaming is not implemented')
    modalities = body.get('modalities', ['text'])
    if modalities not in (['text'], ['audio'], ['text', 'audio']):
        raise HTTPException(400, 'Supported modalities: text, audio, or text+audio')
    if 'audio' in modalities and body.get('audio', {}).get('format', 'wav') != 'wav':
        raise HTTPException(400, 'Output audio must use WAV')
    try:
        maximum = int(body.get('max_tokens', 64))
    except (TypeError, ValueError):
        raise HTTPException(400, 'Invalid max_tokens') from None
    if not 1 <= maximum <= MAX_OUTPUT_TOKENS:
        raise HTTPException(400, f'max_tokens must be between 1 and {MAX_OUTPUT_TOKENS}')
    if not gate.acquire(blocking=False):
        raise HTTPException(429, 'This CPU model processes one request at a time')
    try:
        with tempfile.TemporaryDirectory(prefix='omni-') as temporary:
            messages = conversation(body.get('messages'), Path(temporary))
            inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                                    return_dict=True, return_tensors='pt').to(model.device)
            prompt_tokens = int(inputs['input_ids'].shape[1])
            if prompt_tokens > MAX_INPUT_TOKENS:
                raise HTTPException(400, 'Input exceeds the lab context limit')
            mode = 'interleaved' if modalities == ['text', 'audio'] else modalities[0]
            with torch.inference_mode():
                output = model.generate(**inputs, max_new_tokens=maximum, generation_mode=mode,
                                         do_sample=False, audio_temperature=0.4, audio_repetition_penalty=1.2)
            length = int(output.sequence_lengths[0])
            text = processor.decode(output.sequences[0, prompt_tokens:length], skip_special_tokens=True)
            message = {'role': 'assistant', 'content': text}
            if 'audio' in modalities:
                import soundfile as sf
                codec = processor.audio_tokenizer.to(device=model.device).eval()
                with torch.inference_mode():
                    audio = codec.decode(output.audio_codes[:1, :, :int(output.audio_lengths[0])]).audio_values[0]
                buffer = io.BytesIO()
                sf.write(buffer, audio.squeeze(0).float().cpu().numpy(), 24000, format='WAV')
                message['audio'] = {'id': 'audio-' + uuid.uuid4().hex, 'data': base64.b64encode(buffer.getvalue()).decode(),
                                    'expires_at': int(time.time()) + 3600, 'transcript': text}
            completion_tokens = max(0, length - prompt_tokens)
            return {'id': 'chatcmpl-' + uuid.uuid4().hex, 'object': 'chat.completion', 'created': int(time.time()),
                    'model': MODEL_NAME, 'choices': [{'index': 0, 'message': message, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens,
                              'total_tokens': prompt_tokens + completion_tokens}}
    except HTTPException:
        raise
    except (KeyError, ValueError, OSError) as error:
        raise HTTPException(400, 'Invalid or unsupported model input: ' + type(error).__name__) from None
    finally:
        gate.release()
