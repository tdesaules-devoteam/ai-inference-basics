"""Validate environment contracts and the Dex Job's credential-preservation behavior."""
import base64
import copy
import json
import os
from pathlib import Path
import runpy
import subprocess
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = json.loads((ROOT / 'infra/infra-definition.sample.json').read_text())
SCHEMA = json.loads((ROOT / 'infra/infra-definition.schema.json').read_text())


class InfrastructureContract(unittest.TestCase):
    def test_sample_and_invalid_deployment_inputs(self):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        validator.validate(SAMPLE)
        for field, value in [('enabled', False), ('replicas', 2), ('import', 'true')]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(SAMPLE)
                invalid['models']['qwen3-0-6b'][field] = value
                self.assertFalse(validator.is_valid(invalid))
        invalid = copy.deepcopy(SAMPLE)
        invalid['images']['provision'] = 'localhost/provision:latest'
        self.assertFalse(validator.is_valid(invalid))
        invalid = copy.deepcopy(SAMPLE)
        invalid['models']['unknown-model'] = {'enabled': True, 'replicas': 1, 'import': True}
        self.assertFalse(validator.is_valid(invalid))

    def test_validation_errors_do_not_print_credentials(self):
        import tempfile
        invalid = copy.deepcopy(SAMPLE)
        invalid['access']['adminPassword'] = 'private-marker-' * 10
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.json'
            path.write_text(json.dumps(invalid))
            result = subprocess.run([os.sys.executable, str(ROOT / 'platform/helmfile/scripts/validate-infra.py'), str(path)],
                                    capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('private-marker', result.stdout + result.stderr)
        self.assertIn('adminPassword', result.stderr)


class DexConfiguration(unittest.TestCase):
    def test_preserves_identity_and_rehashes_only_password_changes(self):
        import bcrypt
        store = {}

        def get(command, **kwargs):
            name = command[5]
            return json.dumps(store[name]) if name in store else ''

        def write(command, input, **kwargs):
            document = json.loads(input)
            store[document['metadata']['name']] = document
            return subprocess.CompletedProcess(command, 0)

        def state():
            return json.loads(base64.b64decode(store['admin-access']['data']['credentials.json']))

        env = {'ADMIN_EMAIL': 'admin@example.test', 'ADMIN_PASSWORD': 'initial-fixture', 'LAB_ORIGIN': 'https://fixture.local:30443'}
        with patch.dict(os.environ, env), patch('subprocess.check_output', side_effect=get), patch('subprocess.run', side_effect=write):
            runpy.run_path(str(ROOT / 'charts/dex-config/files/configure.py'))
            initial = state()
            with patch('bcrypt.gensalt', side_effect=AssertionError('Unexpected password rotation')):
                runpy.run_path(str(ROOT / 'charts/dex-config/files/configure.py'))
            self.assertEqual(initial, state())
            with patch.dict(os.environ, {'ADMIN_PASSWORD': 'updated-fixture'}):
                runpy.run_path(str(ROOT / 'charts/dex-config/files/configure.py'))
            updated = state()
            self.assertEqual(initial['id'], updated['id'])
            self.assertEqual(initial['client_secret'], updated['client_secret'])
            self.assertTrue(bcrypt.checkpw(b'updated-fixture', updated['hash'].encode()))


if __name__ == '__main__':
    unittest.main()
