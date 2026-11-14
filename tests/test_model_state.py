"""Convergence must tolerate API defaulting while rejecting stale model settings."""
import copy
from pathlib import Path
import runpy
import unittest

state = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'platform/helmfile/scripts/model-state.py'))


class ModelState(unittest.TestCase):
    def test_rollout_waits_for_current_generation_and_all_new_replicas(self):
        deployment = {'metadata': {'generation': 3}, 'spec': {'replicas': 1},
                      'status': {'observedGeneration': 3, 'replicas': 1, 'updatedReplicas': 1,
                                 'readyReplicas': 1, 'availableReplicas': 1,
                                 'conditions': [{'type': 'Progressing', 'reason': 'ProgressDeadlineExceeded', 'status': 'False'}]}}
        self.assertTrue(state['rollout_ready'](deployment))
        for field, value in [('observedGeneration', 2), ('replicas', 2), ('updatedReplicas', 0),
                             ('readyReplicas', 0), ('availableReplicas', 0)]:
            pending = copy.deepcopy(deployment)
            pending['status'][field] = value
            self.assertFalse(state['rollout_ready'](pending), field)

    def test_defaulted_resources_and_equivalent_quantities(self):
        runtime = {'spec': {'containers': [{'name': 'kserve-container', 'image': 'pinned-image',
                                           'command': ['vllm'], 'args': ['serve'],
                                           'env': [{'name': 'MODEL_DEVICE', 'value': 'cuda'}]}]}}
        desired = {'spec': {'predictor': {'model': {'storageUri': 's3://models/revision',
                   'resources': {'requests': {'cpu': '1', 'memory': '1Gi'}, 'limits': {'nvidia.com/gpu': '1'}}}}}}
        container = copy.deepcopy(runtime['spec']['containers'][0])
        container['resources'] = {'requests': {'cpu': '1000m', 'memory': '1024Mi', 'nvidia.com/gpu': '1'},
                                  'limits': {'nvidia.com/gpu': '1'}}
        deployment = {'spec': {'template': {'metadata': {'annotations': {
            'internal.serving.kserve.io/storage-initializer-sourceuri': 's3://models/revision'}},
            'spec': {'containers': [container]}}}}
        self.assertTrue(state['matches'](deployment, desired, runtime))
        for key, value in [('image', 'old-image'), ('args', ['old']), ('env', []),
                           ('resources', {'requests': {'cpu': '500m', 'memory': '1Gi'}})]:
            stale = copy.deepcopy(deployment)
            stale['spec']['template']['spec']['containers'][0][key] = value
            self.assertFalse(state['matches'](stale, desired, runtime), key)


if __name__ == '__main__':
    unittest.main()
