"""A deliberately stopped model retains its API route, but is not advertised as active."""
import runpy
import unittest
from pathlib import Path


class ModelCatalog(unittest.TestCase):
    def test_stopped_model_is_not_listed_or_confused_with_missing_operation(self):
        render = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                                    'platform/helmfile/scripts/model-contract.py'))['render']
        contract = render('http://lab.test:30444', {
            'chat-model': {'task': 'chat', 'replicas': 0},
            'embedding-model': {'task': 'embeddings', 'replicas': 1},
        })
        self.assertEqual([m['id'] for m in contract['catalog']['data']], ['embedding-model'])
        paths = contract['spec']['paths']
        self.assertIn('/v1/responses', paths)
        self.assertNotIn('/score', paths)
        self.assertNotIn('/v1/completions', paths)
