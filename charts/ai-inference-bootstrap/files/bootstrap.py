"""Generate stable lab credentials and reconcile derived configs without logging secrets."""
import base64
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import bcrypt
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

os.umask(0o077)
settings = json.loads(Path('/scripts/settings.json').read_text())
account = Path('/var/run/secrets/kubernetes.io/serviceaccount')
token = (account / 'token').read_text().strip()
context = ssl.create_default_context(cafile=str(account / 'ca.crt'))


def api(method, path, payload=None):
    request = Request('https://kubernetes.default.svc' + path, method=method,
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
                      data=json.dumps(payload).encode() if payload is not None else None)
    with urlopen(request, context=context, timeout=15) as response:
        return json.load(response)


def read_secret(namespace, name):
    try:
        return api('GET', f'/api/v1/namespaces/{namespace}/secrets/{name}')
    except HTTPError as error:
        error.close()
        if error.code != 404:
            raise RuntimeError(f'Secret read failed: {namespace}/{name}, HTTP {error.code}') from None
        return None


def decode(secret):
    return {key: base64.b64decode(value).decode() for key, value in secret['data'].items()}


def put_secret(namespace, name, data, annotations=None):
    existing = read_secret(namespace, name)
    encoded = {key: base64.b64encode(value.encode()).decode() for key, value in data.items()}
    if existing and existing.get('data') == encoded and existing['metadata'].get('annotations', {}) == (annotations or {}):
        return existing
    if existing and existing['metadata'].get('labels', {}).get('app.kubernetes.io/managed-by') != 'lab-bootstrap':
        raise RuntimeError('Refusing to replace an unrelated Secret: ' + namespace + '/' + name)
    body = {'apiVersion': 'v1', 'kind': 'Secret', 'type': 'Opaque', 'data': encoded,
            'metadata': {'name': name, 'namespace': namespace, 'annotations': annotations or {},
                         'labels': {'app.kubernetes.io/managed-by': 'lab-bootstrap'}}}
    path = f'/api/v1/namespaces/{namespace}/secrets'
    if existing:
        body['metadata']['resourceVersion'] = existing['metadata']['resourceVersion']
        return api('PUT', path + '/' + name, body)
    return api('POST', path, body)


existing = read_secret('gateway', 'lab-access')
if existing:
    state = json.loads(decode(existing)['credentials.json'])
    assert {k: v['email'] for k, v in state['accounts'].items()} == settings['users'], 'Account identity change needs an explicit migration'
else:
    state = {'accounts': {}, 'client_secret': secrets.token_urlsafe(32),
             'cookie_secret': base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
             'api_key': secrets.token_urlsafe(32),
             'reader_key': secrets.token_urlsafe(32), 'writer_key': secrets.token_urlsafe(32)}
    for key, email in settings['users'].items():
        password = secrets.token_urlsafe(20)
        state['accounts'][key] = {'email': email, 'password': password, 'id': str(uuid.uuid4()),
                                  'hash': bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()}
    put_secret('gateway', 'lab-access', {'credentials.json': json.dumps(state)})

deadline = time.monotonic() + 300
while True:
    tls = read_secret('gateway', 'lab-tls')
    ca = read_secret('gateway', 'lab-root-ca')
    if tls and ca and ca.get('data', {}).get('tls.crt') and tls.get('data', {}).get('tls.crt'):
        break
    if time.monotonic() > deadline:
        raise RuntimeError('Lab certificate issuance timed out')
    time.sleep(2)
ca_data = decode(ca)['tls.crt']
origin = f'https://{settings["hostname"]}:{settings["nodePort"]}'
dex = {
    'issuer': origin + '/dex', 'storage': {'type': 'kubernetes', 'config': {'inCluster': True}},
    'web': {'http': '0.0.0.0:5556'}, 'telemetry': {'http': '0.0.0.0:5558'},
    'enablePasswordDB': True, 'oauth2': {'skipApprovalScreen': True},
    'staticClients': [{'id': 'lab-browser', 'name': 'AI Inference Basics', 'secret': state['client_secret'],
                       'redirectURIs': [origin + '/oauth2/callback']}],
    'staticPasswords': [{'email': a['email'], 'username': a['email'], 'userID': a['id'], 'hash': a['hash']}
                        for a in state['accounts'].values()],
}
put_secret('dex', 'dex-config', {'config.yaml': json.dumps(dex)})
# oauth2-proxy decodes URL-safe base64. Normalize legacy standard-base64 state
# without rotating the underlying key or changing the preserved credential Secret.
cookie_secret = base64.urlsafe_b64encode(base64.urlsafe_b64decode(state['cookie_secret'])).decode()
oauth = {
    'provider': 'oidc', 'provider_display_name': 'Lab Dex', 'oidc_issuer_url': origin + '/dex',
    'skip_oidc_discovery': True, 'login_url': origin + '/dex/auth',
    'redeem_url': 'http://dex.dex.svc.cluster.local:5556/dex/token',
    'oidc_jwks_url': 'http://dex.dex.svc.cluster.local:5556/dex/keys',
    'client_id': 'lab-browser', 'client_secret': state['client_secret'],
    'cookie_secret': cookie_secret, 'cookie_secure': True, 'cookie_httponly': True,
    'cookie_samesite': 'lax', 'cookie_expire': '8h', 'redirect_url': origin + '/oauth2/callback',
    'reverse_proxy': True, 'http_address': '0.0.0.0:4180', 'skip_provider_button': True,
    'scope': 'openid profile email', 'code_challenge_method': 'S256',
    'authenticated_emails_file': '/etc/oauth/allowed-emails', 'request_logging': False,
    'upstreams': ['http://127.0.0.1:4181/'], 'pass_access_token': False,
    'pass_authorization_header': False, 'pass_basic_auth': False,
    'set_authorization_header': False, 'pass_user_headers': True,
}
put_secret('oauth2-proxy', 'oauth-config', {'oauth2-proxy.cfg': '\n'.join(f'{k} = {json.dumps(v)}' for k, v in oauth.items()) + '\n',
                                         'allowed-emails': '\n'.join(settings['users'].values()) + '\n',
                                         'client-id': 'lab-browser', 'client-secret': state['client_secret'],
                                         'cookie-secret': cookie_secret})
for namespace in ('oauth2-proxy', 'bastion'):
    put_secret(namespace, 'lab-ca', {'ca.crt': ca_data})
for namespace in ('gateway', 'bastion'):
    put_secret(namespace, 'lab-api-key', {'lab': state['api_key']})

root = decode(read_secret('rustfs', 'rustfs-root'))
endpoint = 'http://rustfs-svc.rustfs.svc.cluster.local:9000'


def rc(*args):
    result = subprocess.run(['rc', '--quiet', *args], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('RustFS administrative operation failed: ' + '/'.join(args[:2]))


rc('alias', 'set', 'lab', endpoint, root['RUSTFS_ACCESS_KEY'], root['RUSTFS_SECRET_KEY'], '--bucket-lookup', 'path')
for role in ('reader', 'writer'):
    user = 'lab-model-' + role
    key = state[role + '_key']
    actions = ['s3:GetObject']
    bucket_actions = ['s3:ListBucket', 's3:GetBucketLocation']
    if role == 'writer':
        actions += ['s3:PutObject', 's3:AbortMultipartUpload', 's3:ListMultipartUploadParts']
        bucket_actions += ['s3:ListBucketMultipartUploads']
    policy = {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': bucket_actions, 'Resource': ['arn:aws:s3:::models']},
        {'Effect': 'Allow', 'Action': actions, 'Resource': ['arn:aws:s3:::models/*']},
    ]}
    policy_file = Path('/tmp') / (role + '.json')
    policy_file.write_text(json.dumps(policy))
    rc('admin', 'user', 'add', 'lab', user, key)
    rc('admin', 'policy', 'create', 'lab', user, str(policy_file))
    rc('admin', 'policy', 'attach', 'lab', user, '--user', user)
    annotations = {'serving.kserve.io/s3-endpoint': 'rustfs-svc.rustfs.svc.cluster.local:9000',
                   'serving.kserve.io/s3-usehttps': '0', 'serving.kserve.io/s3-region': 'us-east-1',
                   'serving.kserve.io/s3-usevirtualbucket': 'false'} if role == 'reader' else {}
    put_secret('inference-service', 'model-' + role, {'AWS_ACCESS_KEY_ID': user, 'AWS_SECRET_ACCESS_KEY': key}, annotations)

reader = boto3.client('s3', endpoint_url=endpoint, region_name='us-east-1',
                      aws_access_key_id='lab-model-reader', aws_secret_access_key=state['reader_key'],
                      config=Config(s3={'addressing_style': 'path'}))
reader.list_objects_v2(Bucket='models', MaxKeys=1)
try:
    check_key = '_qualification/reader-' + uuid.uuid4().hex
    reader.put_object(Bucket='models', Key=check_key, Body=b'forbidden')
except ClientError as error:
    if error.response['ResponseMetadata']['HTTPStatusCode'] != 403:
        raise
else:
    root_client = boto3.client('s3', endpoint_url=endpoint, region_name='us-east-1',
                              aws_access_key_id=root['RUSTFS_ACCESS_KEY'], aws_secret_access_key=root['RUSTFS_SECRET_KEY'],
                              config=Config(s3={'addressing_style': 'path'}))
    root_client.delete_object(Bucket='models', Key=check_key)
    raise RuntimeError('Model reader unexpectedly has write access')
try:
    reader.list_objects_v2(Bucket='loki', MaxKeys=1)
except ClientError as error:
    if error.response['ResponseMetadata']['HTTPStatusCode'] != 403:
        raise
else:
    raise RuntimeError('Model reader unexpectedly has access to another bucket')
print('Lab identities, browser configuration, TLS trust and scoped model credentials are ready.')
