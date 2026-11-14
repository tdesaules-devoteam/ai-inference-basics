"""Own the single admin identity and the browser OIDC client in the Dex domain."""
import json
import os
import secrets
import uuid

import bcrypt
import kube

existing = kube.read('admin-access')
if existing:
    state = json.loads(kube.data(existing)['credentials.json'])
else:
    password = secrets.token_urlsafe(24)
    state = {'username': 'admin', 'email': 'ai-inference-basics@devoteam.com', 'password': password,
             'id': str(uuid.uuid4()), 'hash': bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
             'client_secret': secrets.token_urlsafe(32)}
    state = json.loads(kube.data(kube.write('admin-access', {'credentials.json': json.dumps(state)}))['credentials.json'])
override = kube.read('admin-login')
if override:
    login = kube.data(override)
    if not login.get('email') or not login.get('password'):
        raise RuntimeError('admin-login must contain nonempty email and password')
    if state['email'] != login['email'] or state['password'] != login['password']:
        state['email'] = login['email']
        state['password'] = login['password']
        state['hash'] = bcrypt.hashpw(login['password'].encode(), bcrypt.gensalt()).decode()
        kube.write('admin-access', {'credentials.json': json.dumps(state)})
origin = 'https://' + os.environ['LAB_HOSTNAME'] + ':30443'
config = {
    'issuer': origin + '/dex', 'storage': {'type': 'kubernetes', 'config': {'inCluster': True}},
    'web': {'http': '0.0.0.0:5556'}, 'telemetry': {'http': '0.0.0.0:5558'},
    'enablePasswordDB': True, 'oauth2': {'skipApprovalScreen': True},
    'staticClients': [{'id': 'lab-browser', 'name': 'AI Inference Basics',
                       'secret': state['client_secret'], 'redirectURIs': [origin + '/oauth2/callback']}],
    'staticPasswords': [{'email': state['email'], 'username': 'admin', 'userID': state['id'], 'hash': state['hash']}],
}
kube.write('dex-config', {'config.yaml': json.dumps(config)})
kube.write('oidc-client', {'client-id': 'lab-browser', 'client-secret': state['client_secret'],
                          'admin-email': state['email']})
print('Dex admin identity and OIDC client are ready.')
