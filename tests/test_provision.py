import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import yaml

spec = importlib.util.spec_from_file_location('provision', 'cluster/provision.py')
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


class ProvisionContract(unittest.TestCase):
    def setUp(self):
        self.template = Path('infra/k0s/k0s.yaml').read_text()
        self.artifacts = {'version': '0.3.0-alpha.1',
                          'image': 'localhost/ai-inference-basics-bastion@sha256:' + 'a' * 64}

    def test_guest_config_uses_native_hostname_and_local_artifact(self):
        result = provision.prepare_config(self.template, 'fixture-vm.local', self.artifacts)
        self.assertNotIn('__LAB_HOSTNAME__', result)
        self.assertNotIn('__BASTION_IMAGE__', result)
        config = yaml.safe_load(result)
        entries = config['spec']['extensions']['helm']['charts']
        self.assertEqual([entry['order'] for entry in entries], [1, 2, 3, 4])
        app = yaml.safe_load(entries[-1]['values'])
        self.assertEqual(app['gateway']['hostname'], 'fixture-vm.local')
        self.assertEqual(app['workspaces']['image'], self.artifacts['image'])

    def test_wrong_version_and_mutable_image_are_rejected(self):
        for change in ({'version': '0.0.0'}, {'image': 'localhost/bastion:latest'}):
            with self.assertRaises(AssertionError):
                provision.prepare_config(self.template, 'fixture-vm.local', self.artifacts | change)

    def test_credentials_persist_only_within_one_guest_state(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a, b = Path(first), Path(second)
            provision.credentials(a, 'fixture-vm.local')
            initial = (a / 'credentials.json').read_bytes()
            provision.credentials(a, 'fixture-vm.local')
            self.assertEqual(initial, (a / 'credentials.json').read_bytes())
            provision.credentials(b, 'another-vm.local')
            one, two = json.loads(initial), json.loads((b / 'credentials.json').read_text())
            self.assertEqual(len(one['accounts']), 2)
            self.assertNotEqual(one['api_key'], two['api_key'])

    def test_real_k0s_status_contract_rejects_partial_or_failed_releases(self):
        path = '/var/lib/k0s/charts/ai-inference-basics.tgz'
        charts = [{'spec': {'chartName': path, 'releaseName': f'release-{i}', 'version': '0.3.0-alpha.1'},
                   'status': {'releaseName': f'release-{i}', 'version': '0.3.0-alpha.1', 'revision': 1}}
                  for i in range(4)]
        self.assertTrue(provision.charts_ready(charts, path))
        self.assertFalse(provision.charts_ready(charts[:3], path))
        charts[0]['status']['error'] = 'installation failed'
        self.assertFalse(provision.charts_ready(charts, path))


if __name__ == '__main__':
    unittest.main()
