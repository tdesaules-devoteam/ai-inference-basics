"""Evaluate the actual reload patches with Kyverno's offline target-resource engine."""
import copy
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('kyverno') and shutil.which('helm'), 'Helm and Kyverno CLI are required')
class CredentialReload(unittest.TestCase):
    def test_changed_credentials_patch_only_the_named_deployment(self):
        policies = []
        for chart in ('bastion', 'dex-config'):
            namespace = 'dex' if chart == 'dex-config' else chart
            rendered = subprocess.check_output(['helm', 'template', chart, str(ROOT / 'charts' / chart),
                '-n', namespace, '--set', 'bastionImage=fixture@sha256:' + 'a' * 64,
                '--set', 'provisionImage=fixture@sha256:' + 'b' * 64,
                '--set', 'access.adminEmail=fixture@example.test', '--set', 'access.adminPassword=fixture',
                '--set', 'origin=https://fixture.local:30443'], text=True)
            policies.extend(o for o in yaml.safe_load_all(rendered) if o and o['kind'] == 'MutatingPolicy')
        values = yaml.safe_load((ROOT / 'platform/helmfile/values/oauth2-proxy.yaml').read_text())
        policies.extend(o for o in values['extraObjects'] if o['kind'] == 'MutatingPolicy')
        for policy in policies:
            with self.subTest(policy=policy['metadata']['name']), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                constraints = policy['spec']['matchConstraints']
                namespace = constraints['namespaceSelector']['matchLabels']['kubernetes.io/metadata.name']
                secret = constraints['resourceRules'][0]['resourceNames'][0]
                self.assertEqual(constraints['resourceRules'][0]['operations'], ['UPDATE'])
                self.assertEqual(policy['spec']['matchConditions'][0]['expression'], 'request.object.data != request.oldObject.data')
                # CLI UPDATE simulation copies object to oldObject. Supply a literal previous
                # data fixture in that one operand; target selection and patch stay unchanged.
                policy['spec']['matchConditions'][0]['expression'] = 'request.object.data != {"fixture": "b2xk"}'
                changed = next(v for v in policy['spec']['variables'] if v['name'] == 'dataChanged')
                changed['expression'] = policy['spec']['matchConditions'][0]['expression']
                target = {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': namespace, 'namespace': namespace},
                          'spec': {'selector': {'matchLabels': {'app': namespace}}, 'template': {
                              'metadata': {'labels': {'app': namespace}, 'annotations': {'keep': 'existing'}},
                              'spec': {'containers': [{'name': 'application', 'image': 'fixture'}]}}}}
                expected = copy.deepcopy(target)
                expected['spec']['template']['metadata']['annotations']['lab.ai/credential-' + secret] = '123'
                documents = {
                    'policy.yaml': policy,
                    'trigger.yaml': {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {
                        'name': secret, 'namespace': namespace, 'resourceVersion': '123'}, 'data': {'fixture': 'bmV3'}},
                    'target.yaml': target, 'expected.yaml': expected,
                    'cluster.yaml': {'apiVersion': 'cli.kyverno.io/v1alpha1', 'kind': 'ClusterResource',
                        'metadata': {'name': 'fixture'}, 'spec': {'resources': [{'apiVersion': 'v1', 'kind': 'Namespace',
                        'metadata': {'name': namespace, 'labels': {'kubernetes.io/metadata.name': namespace}}}]}},
                    'kyverno-test.yaml': {'apiVersion': 'cli.kyverno.io/v1alpha1', 'kind': 'Test',
                        'metadata': {'name': 'reload'}, 'policies': ['policy.yaml'], 'resources': ['trigger.yaml'],
                        'targetResources': ['target.yaml'], 'clusterResources': ['cluster.yaml'],
                        'values': {'globalValues': {'request.operation': 'UPDATE'}},
                        'results': [{'isMutatingPolicy': True, 'policy': policy['metadata']['name'], 'kind': 'Deployment',
                                     'resources': [namespace + '/' + namespace], 'patchedResources': 'expected.yaml', 'result': 'pass'}]},
                }
                for name, document in documents.items():
                    (root / name).write_text(yaml.safe_dump(document))
                result = subprocess.run(['kyverno', 'test', str(root), '--require-tests'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                # In the target phase the mutation itself must be a no-op for equal data.
                policy['spec']['matchConditions'][0]['expression'] = 'request.object.data != request.oldObject.data'
                changed['expression'] = policy['spec']['matchConditions'][0]['expression']
                (root / 'policy.yaml').write_text(yaml.safe_dump(policy))
                (root / 'expected.yaml').write_text(yaml.safe_dump(target))
                result = subprocess.run(['kyverno', 'test', str(root), '--require-tests'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
