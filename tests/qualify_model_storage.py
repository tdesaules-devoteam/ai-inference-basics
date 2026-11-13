#!/usr/bin/env python3
"""Run inside the admin bastion; receive the three model locks as a JSON map."""
import base64
import json
import subprocess
import sys
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

locks = json.load(sys.stdin)
endpoint = 'http://rustfs-svc.rustfs.svc.cluster.local:9000'


def secret(namespace, name):
    obj = json.loads(subprocess.check_output(['kubectl', '-n', namespace, 'get', 'secret', name, '-o', 'json']))
    return {k: base64.b64decode(v).decode() for k, v in obj['data'].items()}


def client(key, password):
    return boto3.client('s3', endpoint_url=endpoint, region_name='us-east-1',
                        aws_access_key_id=key, aws_secret_access_key=password,
                        config=Config(s3={'addressing_style': 'path'}))


def denied(operation, **kwargs):
    try:
        operation(**kwargs)
    except ClientError as error:
        assert error.response['ResponseMetadata']['HTTPStatusCode'] == 403
        return
    raise AssertionError('Unexpected S3 permission')


identities = set()
for name, lock in locks.items():
    credentials = secret(name, 'model-reader')
    identities.add(credentials['AWS_ACCESS_KEY_ID'])
    reader = client(credentials['AWS_ACCESS_KEY_ID'], credentials['AWS_SECRET_ACCESS_KEY'])
    prefix = name + '/' + lock['revision'] + '/'
    reader.head_bucket(Bucket='models')
    reader.list_objects_v2(Bucket='models', Prefix=prefix, MaxKeys=1)
    result = reader.get_object(Bucket='models', Key=prefix + 'snapshot-manifest.json')
    assert json.loads(result['Body'].read()) == lock
    other = next(n for n in locks if n != name)
    denied(reader.list_objects_v2, Bucket='models', Prefix=other + '/', MaxKeys=1)
    denied(reader.get_object, Bucket='models', Key=other + '/' + locks[other]['revision'] + '/snapshot-manifest.json')
    denied(reader.list_objects_v2, Bucket='loki', MaxKeys=1)
    key = prefix + '_qualification-' + uuid.uuid4().hex
    try:
        denied(reader.put_object, Bucket='models', Key=key, Body=b'forbidden')
    except AssertionError:
        root = secret('rustfs', 'rustfs-root')
        client(root['RUSTFS_ACCESS_KEY'], root['RUSTFS_SECRET_KEY']).delete_object(Bucket='models', Key=key)
        raise
assert len(identities) == 3
print('Three distinct model readers: own-prefix read allowed; writes, other prefixes and Loki denied.')
