"""Provision prefix-scoped model identities inside the RustFS domain."""
import hashlib
import json
from pathlib import Path
import secrets
import subprocess

import kube

endpoint = 'http://rustfs-svc.rustfs.svc.cluster.local:9000'
root = kube.data(kube.read('rustfs-root'))


def rc(*args):
    result = subprocess.run(['rc', '--quiet', *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError('RustFS IAM operation failed: ' + '/'.join(args[:2]))


rc('alias', 'set', 'lab', endpoint, root['RUSTFS_ACCESS_KEY'], root['RUSTFS_SECRET_KEY'], '--bucket-lookup', 'path')
for model in ('qwen3-0-6b', 'qwen3-embedding-0-6b', 'qwen3-reranker-0-6b'):
    name = 's3-' + model
    existing = kube.read(name)
    if existing:
        credentials = kube.data(existing)
    else:
        stem = 'model-' + hashlib.sha256(model.encode()).hexdigest()[:8]
        credentials = {'reader-access': stem + '-ro', 'reader-secret': secrets.token_urlsafe(32),
                       'writer-access': stem + '-rw', 'writer-secret': secrets.token_urlsafe(32)}
        credentials = kube.data(kube.write(name, credentials))
    for role in ('reader', 'writer'):
        user = credentials[role + '-access']
        actions = ['s3:GetObject']
        if role == 'writer':
            actions += ['s3:PutObject', 's3:AbortMultipartUpload', 's3:ListMultipartUploadParts']
        policy = {'Version': '2012-10-17', 'Statement': [
            {'Effect': 'Allow', 'Action': ['s3:GetBucketLocation'], 'Resource': ['arn:aws:s3:::models']},
            {'Effect': 'Allow', 'Action': ['s3:ListBucket'], 'Resource': ['arn:aws:s3:::models'],
             # KServe calls HeadBucket before listing its prefix. HeadBucket has
             # no s3:prefix; object reads remain restricted by the ARN below.
             'Condition': {'StringLikeIfExists': {'s3:prefix': [model, model + '/', model + '/*']}}},
            {'Effect': 'Allow', 'Action': actions, 'Resource': ['arn:aws:s3:::models/' + model + '/*']},
        ]}
        path = Path('/tmp/policy.json')
        path.write_text(json.dumps(policy))
        rc('admin', 'user', 'add', 'lab', user, credentials[role + '-secret'])
        rc('admin', 'policy', 'create', 'lab', user, str(path))
        rc('admin', 'policy', 'attach', 'lab', user, '--user', user)
print('Three prefix-scoped reader/writer identities are ready.')
