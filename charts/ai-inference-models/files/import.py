"""Import immutable, SHA-256-verified public model snapshots into the models bucket."""
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import requests

manifest = json.loads(Path('/scripts/models.lock.json').read_text())
s3 = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT'], region_name='us-east-1',
                  config=Config(s3={'addressing_style': 'path'}, retries={'max_attempts': 5},
                                request_checksum_calculation='when_required', response_checksum_validation='when_required'))
bucket = os.environ['S3_BUCKET']
cache = Path('/cache')
cache.mkdir(exist_ok=True)
for name, model in manifest.items():
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
                raise RuntimeError('Existing immutable model object differs: ' + key)
            print(name + ': already verified ' + entry['path'], flush=True)
            continue
        target = cache / entry['sha256']
        url = 'https://huggingface.co/' + model['repository'] + '/resolve/' + model['revision'] + '/' + quote(entry['path'])
        for attempt in range(5):
            offset = target.stat().st_size if target.exists() else 0
            try:
                with requests.get(url, headers={'Range': f'bytes={offset}-'} if offset else {},
                                  stream=True, timeout=(20, 120)) as response:
                    response.raise_for_status()
                    with target.open('ab' if offset and response.status_code == 206 else 'wb') as output:
                        for chunk in response.iter_content(8 * 1024 * 1024):
                            output.write(chunk)
                break
            except requests.RequestException:
                if attempt == 4:
                    raise RuntimeError('Model download failed: ' + key) from None
                time.sleep(3 * (attempt + 1))
        with target.open('rb') as source:
            checksum = hashlib.file_digest(source, 'sha256').hexdigest()
        if checksum != entry['sha256'] or target.stat().st_size != entry['size']:
            raise RuntimeError('Model checksum/size mismatch: ' + key)
        s3.upload_file(str(target), bucket, key, ExtraArgs={'Metadata': {'sha256': checksum, 'revision': model['revision']}})
        uploaded = s3.head_object(Bucket=bucket, Key=key)
        assert uploaded['ContentLength'] == entry['size'] and uploaded['Metadata']['sha256'] == checksum
        target.unlink()
        print(name + ': verified and uploaded ' + entry['path'], flush=True)
    s3.put_object(Bucket=bucket, Key=prefix + 'snapshot-manifest.json', Body=json.dumps(model, sort_keys=True).encode())
print('All pinned model snapshots are available in S3.', flush=True)
