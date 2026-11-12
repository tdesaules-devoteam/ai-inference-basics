#!/usr/bin/env python3
"""Exercise the exact inline credential hook against simulated Kubernetes API results."""
import base64
import copy
from pathlib import Path
import unittest
from urllib.error import HTTPError

import yaml

VALUES = Path(__file__).resolve().parent.parent / 'platform/helm/values/rustfs.yaml'
job = next(obj for obj in yaml.safe_load(VALUES.read_text())['extraManifests']
           if obj['kind'] == 'Job' and obj['metadata']['name'] == 'rustfs-credentials')
hook = {'__name__': 'credential_hook_test'}
exec(compile(job['spec']['template']['spec']['containers'][0]['args'][0], '<credential-hook>', 'exec'), hook)


def http_error(code):
    return HTTPError('https://kubernetes.default.svc', code, 'fixture', {}, None)


class CredentialHook(unittest.TestCase):
    def setUp(self):
        self.secret = {'data': {key: base64.b64encode(b'existing-value').decode()
                               for key in ('RUSTFS_ACCESS_KEY', 'RUSTFS_SECRET_KEY')}}

    def test_existing_secret_is_read_without_mutation(self):
        before = copy.deepcopy(self.secret)
        calls = []
        def api(method, path, payload=None):
            calls.append(method)
            return self.secret
        self.assertFalse(hook['ensure_secret'](api, 'fixture'))
        self.assertEqual(calls, ['GET'])
        self.assertEqual(self.secret, before)

    def test_first_install_creates_valid_credentials_in_target_namespace(self):
        calls = []
        def api(method, path, payload=None):
            calls.append((method, path))
            if method == 'GET':
                raise http_error(404)
            self.assertEqual(payload['metadata']['name'], 'rustfs-root')
            self.assertEqual(payload['metadata']['namespace'], 'fixture')
            self.assertEqual(len(base64.b64decode(payload['data']['RUSTFS_ACCESS_KEY'])), 24)
            self.assertEqual(len(base64.b64decode(payload['data']['RUSTFS_SECRET_KEY'])), 64)
            return payload
        self.assertTrue(hook['ensure_secret'](api, 'fixture'))
        self.assertEqual(calls, [('GET', '/api/v1/namespaces/fixture/secrets/rustfs-root'),
                                 ('POST', '/api/v1/namespaces/fixture/secrets')])

    def test_authorization_and_server_errors_do_not_create_credentials(self):
        for status in (401, 403, 429, 500, 503):
            with self.subTest(status=status):
                calls = []
                def api(method, path, payload=None):
                    calls.append(method)
                    raise http_error(status)
                with self.assertRaises(HTTPError):
                    hook['ensure_secret'](api, 'fixture')
                self.assertEqual(calls, ['GET'])

    def test_conflict_reuses_the_concurrently_created_secret(self):
        calls = []
        def api(method, path, payload=None):
            calls.append(method)
            if len(calls) == 1:
                raise http_error(404)
            if method == 'POST':
                raise http_error(409)
            return self.secret
        self.assertFalse(hook['ensure_secret'](api, 'fixture'))
        self.assertEqual(calls, ['GET', 'POST', 'GET'])

    def test_malformed_existing_secret_fails_without_replacing_it(self):
        for data in (None, {}, {'RUSTFS_ACCESS_KEY': '!invalid!'},
                     {'RUSTFS_ACCESS_KEY': '', 'RUSTFS_SECRET_KEY': ''}):
            with self.subTest(data=data):
                calls = []
                def api(method, path, payload=None):
                    calls.append(method)
                    return {'data': data}
                with self.assertRaises(ValueError):
                    hook['ensure_secret'](api, 'fixture')
                self.assertEqual(calls, ['GET'])


if __name__ == '__main__':
    unittest.main()
