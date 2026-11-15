"""Bounded OpenAI-style adapter for a pinned, local LFM3-Omni Transformers snapshot."""
import base64
from contextlib import asynccontextmanager
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from typing import Annotated, Literal

MODEL_NAME = 'lfm3-omni-2b'
MAX_CONTEXT_TOKENS = int(os.environ.get('MAX_CONTEXT_TOKENS', '128000'))
MAX_OUTPUT_TOKENS = int(os.environ.get('MAX_OUTPUT_TOKENS', '128'))
MAX_BODY_BYTES = 24 * 1024 * 1024
MAX_MEDIA_BYTES = 16 * 1024 * 1024
MAX_MEDIA_ITEMS = 4
MAX_TEXT_CHARS = max(32768, MAX_CONTEXT_TOKENS * 8)
MAX_IMAGE_PIXELS = 16 * 1024 * 1024
MAX_VIDEO_PIXELS = 1920 * 1080
MAX_VIDEO_FRAMES = 16
DEVICE = os.environ.get('MODEL_DEVICE', 'cpu')
gate = threading.Lock()
model = processor = None


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class TextPart(Input):
    type: Literal['text']
    text: str = Field(max_length=MAX_TEXT_CHARS)


class MediaURL(Input):
    url: str


class ImageURL(MediaURL):
    detail: Literal['auto', 'low', 'high'] = 'auto'


class ImagePart(Input):
    type: Literal['image_url']
    image_url: ImageURL


class Audio(Input):
    data: str
    format: Literal['wav']


class AudioPart(Input):
    type: Literal['input_audio']
    input_audio: Audio


class VideoPart(Input):
    type: Literal['video_url']
    video_url: MediaURL


Part = Annotated[TextPart | ImagePart | AudioPart | VideoPart, Field(discriminator='type')]


class Message(Input):
    role: Literal['system', 'user', 'assistant']
    content: Annotated[str, Field(max_length=MAX_TEXT_CHARS)] | Annotated[list[Part], Field(min_length=1, max_length=16)]


class OutputAudio(Input):
    format: Literal['wav'] = 'wav'


class Completion(Input):
    model: str
    messages: list[Message] = Field(min_length=1, max_length=32)
    max_tokens: StrictInt = Field(default=64, ge=1, le=MAX_OUTPUT_TOKENS)
    stream: Literal[False] = False
    modalities: list[Literal['text', 'audio']] = Field(default=['text'], min_length=1, max_length=2)
    audio: OutputAudio | None = None


class BodyLimit:
    """Bound actual ASGI bytes, including chunked requests, before JSON parsing."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                return await JSONResponse({'detail': 'Request exceeds 24 MiB'}, status_code=413)(scope, receive, send)
            body.extend(chunk)
            if not message.get('more_body', False):
                break
        async def bounded_receive():
            nonlocal body
            if body is not None:
                data, body = bytes(body), None
                return {'type': 'http.request', 'body': data, 'more_body': False}
            return await receive()
        await self.app(scope, bounded_receive, send)


@asynccontextmanager
async def lifespan(app):
    global model, processor
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    torch.set_num_threads(int(os.environ.get('OMP_NUM_THREADS', '8')))
    if DEVICE not in ('cpu', 'cuda'):
        raise RuntimeError('MODEL_DEVICE must be cpu or cuda')
    if DEVICE == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA was requested but is unavailable; refusing CPU fallback')
    path = os.environ.get('MODEL_PATH', '/mnt/models')
    model = AutoModelForImageTextToText.from_pretrained(
        path, trust_remote_code=True, local_files_only=True, device_map=DEVICE,
        dtype=torch.bfloat16 if DEVICE == 'cuda' else torch.float32).eval()
    processor = AutoProcessor.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(BodyLimit)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    # Pydantic's default response includes rejected inputs (potentially media/prompts).
    return JSONResponse({'detail': 'Invalid completion request'}, status_code=422)


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
    encoded = value.split(',', 1)[1]
    if len(encoded) > 4 * ((MAX_MEDIA_BYTES + 2) // 3):
        raise HTTPException(413, 'Media exceeds 16 MiB')
    try:
        data = base64.b64decode(encoded, validate=True)
    except ValueError:
        raise HTTPException(400, 'Invalid base64 media') from None
    if len(data) > MAX_MEDIA_BYTES:
        raise HTTPException(413, 'Media exceeds 16 MiB')
    return data


def check_video(path):
    """Inspect stream metadata before Transformers decodes sampled frames."""
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file', '-select_streams', 'v:0',
                                 '-show_entries', 'stream=width,height,duration:format=duration',
                                 '-of', 'json', str(path)], capture_output=True, timeout=10, check=True)
        info = json.loads(result.stdout)
        stream = info['streams'][0]
        duration = float(stream.get('duration', info.get('format', {}).get('duration', 'nan')))
        pixels = int(stream['width']) * int(stream['height'])
        if not math.isfinite(duration) or not 0 < duration <= 30 or not 0 < pixels <= MAX_VIDEO_PIXELS:
            raise ValueError('Video exceeds bounds')
    except (subprocess.SubprocessError, KeyError, IndexError, ValueError):
        raise HTTPException(400, 'Video must be at most 30 seconds and 1920x1080 pixels') from None


def conversation(messages, directory):
    if not isinstance(messages, list) or not messages:
        raise HTTPException(400, 'messages must be a nonempty array')
    text_size = sum(len(message['content']) if isinstance(message['content'], str)
                    else sum(len(item['text']) for item in message['content'] if item['type'] == 'text')
                    for message in messages)
    if text_size > MAX_TEXT_CHARS:
        raise HTTPException(413, f'Combined text exceeds {MAX_TEXT_CHARS} characters')
    media = [item for message in messages if isinstance(message['content'], list)
             for item in message['content'] if item['type'] != 'text']
    if len(media) > MAX_MEDIA_ITEMS:
        raise HTTPException(413, 'At most four media items per request')
    # Check the cumulative decoded size before allocating or preprocessing media.
    total = 0
    for item in media:
        encoded = (item['input_audio']['data'] if item['type'] == 'input_audio'
                   else item[item['type']]['url'].split(',', 1)[-1])
        total += len(encoded) // 4 * 3 - min(2, len(encoded) - len(encoded.rstrip('=')))
    if total > MAX_MEDIA_BYTES:
        raise HTTPException(413, 'Combined media exceeds 16 MiB')
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
                with Image.open(io.BytesIO(data)) as source:
                    if source.width * source.height > MAX_IMAGE_PIXELS:
                        raise HTTPException(400, 'Image exceeds 16 megapixels')
                    source.thumbnail((512, 512))
                    image = source.convert('RGB')
                parts.append({'type': 'image', 'image': image})
            elif kind == 'input_audio':
                audio = item['input_audio']
                if audio.get('format') != 'wav':
                    raise HTTPException(400, 'Input audio must be WAV')
                data = decode_data('data:audio/wav;base64,' + audio['data'], 'audio')
                import soundfile as sf
                try:
                    with sf.SoundFile(io.BytesIO(data)) as sound:
                        if sound.format != 'WAV' or not 0 < sound.frames / sound.samplerate <= 30 or sound.channels > 2 or sound.samplerate > 48000:
                            raise HTTPException(400, 'Audio must be WAV, at most 30 seconds, stereo and 48 kHz')
                except sf.LibsndfileError:
                    raise HTTPException(400, 'Invalid WAV audio') from None
                path = directory / (str(len(result)) + '-' + str(index) + '.wav')
                path.write_bytes(data)
                parts.append({'type': 'audio', 'audio': str(path)})
            elif kind == 'video_url':
                data = decode_data(item['video_url']['url'], 'video')
                if data[4:8] != b'ftyp':
                    raise HTTPException(400, 'Input video must be an inline MP4 file')
                path = directory / (str(len(result)) + '-' + str(index) + '.mp4')
                path.write_bytes(data)
                check_video(path)
                parts.append({'type': 'video', 'video': str(path)})
            else:
                raise HTTPException(400, 'Supported parts: text, image_url, input_audio, video_url')
        result.append({'role': role, 'content': parts})
    return result


@app.post('/v1/chat/completions')
def completions(request: Completion):
    body = request.model_dump()
    if body.get('model') != MODEL_NAME:
        raise HTTPException(404, 'Unknown model')
    if body.get('stream'):
        raise HTTPException(400, 'This Transformers adapter returns complete responses; streaming is not implemented')
    modalities = body.get('modalities', ['text'])
    if modalities not in (['text'], ['audio'], ['text', 'audio']):
        raise HTTPException(400, 'Supported modalities: text, audio, or text+audio')
    if 'audio' in modalities and (body.get('audio') or {}).get('format', 'wav') != 'wav':
        raise HTTPException(400, 'Output audio must use WAV')
    try:
        maximum = int(body.get('max_tokens', 64))
    except (TypeError, ValueError):
        raise HTTPException(400, 'Invalid max_tokens') from None
    if not 1 <= maximum <= MAX_OUTPUT_TOKENS:
        raise HTTPException(400, f'max_tokens must be between 1 and {MAX_OUTPUT_TOKENS}')
    if not gate.acquire(blocking=False):
        raise HTTPException(429, 'This model processes one request at a time')
    try:
        import torch
        with tempfile.TemporaryDirectory(prefix='omni-') as temporary:
            messages = conversation(body.get('messages'), Path(temporary))
            inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                                    return_dict=True, return_tensors='pt',
                                                    processor_kwargs={'videos_kwargs': {
                                                        'num_frames': MAX_VIDEO_FRAMES, 'fps': None,
                                                        'size': {'shortest_edge': 4096, 'longest_edge': 256 * 256 * MAX_VIDEO_FRAMES}}}).to(model.device)
            prompt_tokens = int(inputs['input_ids'].shape[1])
            if prompt_tokens + maximum > MAX_CONTEXT_TOKENS:
                raise HTTPException(400, 'Input plus requested output exceeds the lab context limit')
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
    except (KeyError, ValueError, OSError, Image.DecompressionBombError) as error:
        raise HTTPException(400, 'Invalid or unsupported model input: ' + type(error).__name__) from None
    finally:
        gate.release()
