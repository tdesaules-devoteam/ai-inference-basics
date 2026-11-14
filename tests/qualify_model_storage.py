#!/usr/bin/env python3
"""Run in the provision image with the bastion service account; read model locks from stdin."""
import base64
import json
from pathlib import Path
import ssl
import sys
import uuid
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

locks = json.load(sys.stdin)
endpoint = 'http://rustfs-svc.rustfs.svc.cluster.local:9000'


def secret(namespace, name):
    account = Path('/var/run/secrets/kubernetes.io/serviceaccount')
    request = Request(f'https://kubernetes.default.svc/api/v1/namespaces/{namespace}/secrets/{name}',
                      headers={'Authorization': 'Bearer ' + (account / 'token').read_text().strip()})
    with urlopen(request, context=ssl.create_default_context(cafile=str(account / 'ca.crt')), timeout=30) as response:
        obj = json.load(response)
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
    reader.list_objects_v2(Bucket='models', Prefix=other + '/', MaxKeys=1)
    result = reader.get_object(Bucket='models', Key=other + '/' + locks[other]['revision'] + '/snapshot-manifest.json')
    assert json.loads(result['Body'].read()) == locks[other]
    denied(reader.list_objects_v2, Bucket='loki', MaxKeys=1)
    key = prefix + '_qualification-' + uuid.uuid4().hex
    try:
        reader.put_object(Bucket='models', Key=key, Body=b'qualification')
        assert reader.get_object(Bucket='models', Key=key)['Body'].read() == b'qualification'
    finally:
        root = secret('rustfs', 'rustfs-root')
        client(root['RUSTFS_ACCESS_KEY'], root['RUSTFS_SECRET_KEY']).delete_object(Bucket='models', Key=key)
assert len(identities) == 1
print(f'{len(locks)} models share one bucket account: reads/writes across model prefixes allowed; Loki denied.')
