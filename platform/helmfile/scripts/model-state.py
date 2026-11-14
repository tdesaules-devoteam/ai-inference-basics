#!/usr/bin/env python3
"""Compare desired model settings with a defaulted KServe Deployment."""
from decimal import Decimal
import json
import re
import sys


def quantity(value):
    match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([numkKMGTEP]|[KMGTPE]i)?', str(value))
    if not match:
        raise ValueError('Invalid Kubernetes quantity')
    amount, suffix = match.groups()
    powers = {'n': -9, 'u': -6, 'm': -3, 'k': 3, 'K': 3, 'M': 6, 'G': 9, 'T': 12, 'P': 15, 'E': 18}
    factor = (Decimal(1024) ** ('KMGTPE'.index(suffix[0]) + 1) if suffix and suffix.endswith('i')
              else Decimal(10) ** powers.get(suffix, 0))
    return Decimal(amount) * factor


def matches(deployment, desired, runtime):
    template = deployment['spec']['template']
    model = desired['spec']['predictor']['model']
    if template['metadata'].get('annotations', {}).get('internal.serving.kserve.io/storage-initializer-sourceuri') != model['storageUri']:
        return False
    expected = runtime['spec']['containers'][0]
    actual = next((c for c in template['spec']['containers'] if c['name'] == 'kserve-container'), None)
    if not actual or any(actual.get(key) != expected.get(key) for key in ('image', 'command', 'args')):
        return False
    if any(env not in actual.get('env', []) for env in expected.get('env', [])):
        return False
    # Admission may add requests for limits-only extended resources and normalize quantities.
    resources = actual.get('resources', {})
    return all(key in resources.get(kind, {}) and quantity(value) == quantity(resources[kind][key])
               for kind, values in model.get('resources', {}).items() for key, value in values.items())


def rollout_ready(deployment):
    """Wait for current replicas without treating a cold-start deadline as final."""
    spec, status = deployment['spec'], deployment.get('status', {})
    desired = spec.get('replicas', 1)
    return (status.get('observedGeneration', 0) >= deployment['metadata']['generation']
            and all(status.get(field, 0) == desired for field in
                    ('replicas', 'updatedReplicas', 'readyReplicas', 'availableReplicas')))


if __name__ == '__main__':
    try:
        deployment = json.load(sys.stdin)
        ready = (rollout_ready(deployment) if sys.argv[1:] == ['--rollout-ready'] else
                 matches(deployment, json.loads(sys.argv[1]), json.loads(sys.argv[2])))
        sys.exit(0 if ready else 1)
    except (KeyError, ValueError, TypeError):
        sys.exit(1)
