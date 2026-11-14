"""Import one pinned Hugging Face snapshot into its immutable S3 prefix."""
import hashlib
import json
import os
from pathlib import Path

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import ClientError
from huggingface_hub import hf_hub_download

model = json.loads(Path('/scripts/model.lock.json').read_text())
name = os.environ['MODEL_NAME']
bucket = os.environ['S3_BUCKET']
s3 = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT'], region_name='us-east-1',
                  config=Config(s3={'addressing_style': 'path'}, retries={'mode': 'adaptive', 'max_attempts': 10},
                                request_checksum_calculation='when_required', response_checksum_validation='when_required'))
prefix = name + '/' + model['revision'] + '/'
for entry in model['files']:
    key = prefix + entry['path']
    try:
        existing = s3.head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if error.response['ResponseMetadata']['HTTPStatusCode'] != 404:
            raise
    else:
        if existing['ContentLength'] != entry['size'] or existing.get('Metadata', {}).get('sha256') != entry['sha256']:
            raise RuntimeError('Immutable S3 object differs: ' + key)
        print('Already imported: ' + entry['path'], flush=True)
        continue
    target = Path(hf_hub_download(repo_id=model['repository'], revision=model['revision'],
                                  filename=entry['path'], local_dir='/cache', token=False))
    with target.open('rb') as source:
        checksum = hashlib.file_digest(source, 'sha256').hexdigest()
    if checksum != entry['sha256'] or target.stat().st_size != entry['size']:
        raise RuntimeError('Model checksum/size mismatch: ' + key)
    s3.upload_file(str(target), bucket, key, ExtraArgs={'Metadata': {'sha256': checksum, 'revision': model['revision']}},
                   Config=TransferConfig(max_concurrency=2, multipart_chunksize=32 * 1024 * 1024))
    uploaded = s3.head_object(Bucket=bucket, Key=key)
    assert uploaded['ContentLength'] == entry['size'] and uploaded['Metadata']['sha256'] == checksum
    target.unlink()
    print('Verified and uploaded: ' + entry['path'], flush=True)
s3.put_object(Bucket=bucket, Key=prefix + 'snapshot-manifest.json', Body=json.dumps(model, sort_keys=True).encode())
print('Pinned model snapshot available: ' + name, flush=True)
