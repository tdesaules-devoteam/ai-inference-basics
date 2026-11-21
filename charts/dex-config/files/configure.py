"""Own the single admin identity and the browser OIDC client in the Dex domain."""
import base64
import json
import os
import secrets
import uuid
import subprocess

import bcrypt
def read(name):
    raw = subprocess.check_output(['kubectl', '-n', 'dex', 'get', 'secret', name,
                                   '--ignore-not-found', '-o', 'json'], text=True)
    return json.loads(raw) if raw.strip() else None


def data(secret):
    return {key: base64.b64decode(value).decode() for key, value in secret['data'].items()}


def publish(name, values):
    previous = read(name)
    document = {'apiVersion': 'v1', 'kind': 'Secret', 'type': 'Opaque',
                'metadata': {'name': name, 'namespace': 'dex'},
                'data': {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}}
    if previous:
        if previous['data'] == document['data']:
            return
        document['metadata'] = previous['metadata']
    subprocess.run(['kubectl', 'replace' if previous else 'create', '-f', '-'],
                   input=json.dumps(document), text=True, check=True, stdout=subprocess.DEVNULL)


# Keep the OIDC client secret and user ID stable across Helm upgrades, even if the login changes.
existing = read('admin-access')
if existing:
    state = json.loads(data(existing)['credentials.json'])
else:
    password = os.environ['ADMIN_PASSWORD']
    state = {'username': 'cluster-admin', 'email': os.environ['ADMIN_EMAIL'], 'password': password,
             'id': str(uuid.uuid4()), 'hash': bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
             'client_secret': secrets.token_urlsafe(32)}
    publish('admin-access', {'credentials.json': json.dumps(state)})
login = {'email': os.environ['ADMIN_EMAIL'], 'password': os.environ['ADMIN_PASSWORD']}
publish('admin-login', login)
if login:
    if not login.get('email') or not login.get('password'):
        raise RuntimeError('admin-login must contain nonempty email and password')
    if state['email'] != login['email'] or state['password'] != login['password'] or state['username'] != 'cluster-admin':
        state['username'] = 'cluster-admin'
        state['email'] = login['email']
        state['password'] = login['password']
        state['hash'] = bcrypt.hashpw(login['password'].encode(), bcrypt.gensalt()).decode()
        publish('admin-access', {'credentials.json': json.dumps(state)})
origin = os.environ['LAB_ORIGIN']
config = {
    'issuer': origin + '/dex', 'storage': {'type': 'kubernetes', 'config': {'inCluster': True}},
    'web': {'http': '0.0.0.0:5556'}, 'telemetry': {'http': '0.0.0.0:5558'},
    'enablePasswordDB': True, 'oauth2': {'skipApprovalScreen': True},
    'staticClients': [{'id': 'lab-browser', 'name': 'AI Inference Basics',
                       'secret': state['client_secret'], 'redirectURIs': [origin + '/oauth2/callback']}],
    'staticPasswords': [{'email': state['email'], 'username': state['username'], 'userID': state['id'], 'hash': state['hash']}],
}
publish('dex-config', {'config.yaml': json.dumps(config)})
publish('oidc-client', {'client-id': 'lab-browser', 'client-secret': state['client_secret'],
                          'admin-email': state['email']})
print('Dex admin identity and OIDC client are ready.')
