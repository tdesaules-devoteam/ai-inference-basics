"""Validate the HTTP/media boundary without loading weights or requiring a GPU."""
import asyncio
import base64
from contextlib import nullcontext
import importlib.util
import io
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

spec = importlib.util.spec_from_file_location('omni', Path(__file__).resolve().parents[1] / 'oci/lfm3-omni-2b-transformers/server.py')
omni = importlib.util.module_from_spec(spec)
spec.loader.exec_module(omni)


class OmniBoundary(unittest.TestCase):
    def test_invalid_messages_are_client_errors_without_echoing_input(self):
        client = TestClient(omni.app)  # No lifespan: boundary tests do not load the model.
        for messages in ([None], [{'role': 'user', 'content': [None]}],
                         [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': None}]}],
                         [{'role': 'user', 'content': {'private-marker': 'prompt'}}]):
            result = client.post('/v1/chat/completions', json={'model': omni.MODEL_NAME, 'messages': messages})
            self.assertEqual(result.status_code, 422)
            self.assertNotIn('private-marker', result.text)

    def test_chunked_body_limit_precedes_json_parsing(self):
        async def exercise():
            events = iter([{'type': 'http.request', 'body': b'a' * 8, 'more_body': True},
                           {'type': 'http.request', 'body': b'b' * 9, 'more_body': False}])
            sent = []
            async def receive(): return next(events)
            async def send(event): sent.append(event)
            async def app(*args): self.fail('Oversized body reached application')
            with patch.object(omni, 'MAX_BODY_BYTES', 16):
                await omni.BodyLimit(app)({'type': 'http', 'method': 'POST'}, receive, send)
            self.assertEqual(sent[0]['status'], 413)
        asyncio.run(exercise())

    def test_media_count_and_total_size_checked_before_decoding(self):
        part = {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(b'x' * 12).decode()}}
        for parts, limit in [([part] * 5, 100), ([part] * 2, 16)]:
            with patch.object(omni, 'MAX_MEDIA_BYTES', limit), patch.object(omni, 'decode_data', side_effect=AssertionError('Decoded too early')):
                with self.assertRaises(omni.HTTPException) as error:
                    omni.conversation([{'role': 'user', 'content': parts}], Path('/unused'))
                self.assertEqual(error.exception.status_code, 413)

    def test_combined_text_is_bounded_before_tokenization(self):
        messages = [{'role': 'user', 'content': 'a' * 20000},
                    {'role': 'user', 'content': [{'type': 'text', 'text': 'b' * 20000}]}]
        with patch.object(omni, 'MAX_TEXT_CHARS', 32768), self.assertRaises(omni.HTTPException) as error:
            omni.conversation(messages, Path('/unused'))
        self.assertEqual(error.exception.status_code, 413)

    def test_image_dimensions_are_checked_before_conversion(self):
        image = Image.new('RGB', (20, 20))
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        part = {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()}}
        with patch.object(omni, 'MAX_IMAGE_PIXELS', 100), self.assertRaises(omni.HTTPException):
            omni.conversation([{'role': 'user', 'content': [part]}], Path('/unused'))
        result = omni.conversation([{'role': 'user', 'content': [part]}], Path('/unused'))
        self.assertEqual(result[0]['content'][0]['image'].size, (20, 20))

    def test_video_metadata_bounds(self):
        for duration, width in [('31', 1920), ('nan', 1920), ('1', 4096)]:
            result = subprocess.CompletedProcess([], 0, stdout=json.dumps({'streams': [{'width': width, 'height': 1080, 'duration': duration}]}).encode())
            with patch('subprocess.run', return_value=result), self.assertRaises(omni.HTTPException):
                omni.check_video(Path('/unused'))

    def test_unknown_model_and_busy_requests_need_no_torch(self):
        client = TestClient(omni.app)
        body = {'model': 'unknown', 'messages': [{'role': 'user', 'content': 'hello'}]}
        self.assertEqual(client.post('/v1/chat/completions', json=body).status_code, 404)
        body['model'] = omni.MODEL_NAME
        omni.gate.acquire()
        try:
            self.assertEqual(client.post('/v1/chat/completions', json=body).status_code, 429)
        finally:
            omni.gate.release()

    def test_valid_completion_passes_bounded_video_options_and_releases_gate(self):
        class Tokens:
            shape = (1, 3)

        class Inputs(dict):
            def to(self, device):
                return self

        class Sequence:
            def __getitem__(self, key):
                return [1]

        calls = []
        def prepare(messages, **kwargs):
            calls.append(kwargs)
            return Inputs(input_ids=Tokens())

        processor = SimpleNamespace(apply_chat_template=prepare, decode=lambda *a, **kw: 'Hello')
        model = SimpleNamespace(device='cpu', generate=lambda **kw: SimpleNamespace(sequence_lengths=[4], sequences=Sequence()))
        body = {'model': omni.MODEL_NAME, 'messages': [{'role': 'user', 'content': 'hello'}]}
        with patch.object(omni, 'processor', processor), patch.object(omni, 'model', model), \
                patch.dict('sys.modules', {'torch': SimpleNamespace(inference_mode=nullcontext)}):
            response = TestClient(omni.app).post('/v1/chat/completions', json=body)
            with patch.object(omni, 'MAX_CONTEXT_TOKENS', 66):
                limited = TestClient(omni.app).post('/v1/chat/completions', json=body)
                self.assertEqual(limited.status_code, 400)
                self.assertFalse(omni.gate.locked())
            with patch.object(omni, 'MAX_CONTEXT_TOKENS', 67):
                exact = TestClient(omni.app).post('/v1/chat/completions', json=body)
                self.assertEqual(exact.status_code, 200)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['choices'][0]['message']['content'], 'Hello')
        self.assertEqual(response.json()['usage']['completion_tokens'], 1)
        self.assertEqual(calls[0]['processor_kwargs']['videos_kwargs']['num_frames'], 16)
        self.assertFalse(omni.gate.locked())


if __name__ == '__main__':
    unittest.main()
