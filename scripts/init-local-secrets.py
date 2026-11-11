#!/usr/bin/env python3
"""Initialize disposable local credentials without printing or overwriting them."""
import base64
import json
import os
import pathlib
import secrets
import subprocess
import uuid

import bcrypt
import yaml

root = pathlib.Path(__file__).resolve().parent.parent
os.chdir(root)
os.umask(0o077)
directory = root / '.local/secrets'
directory.mkdir(parents=True, exist_ok=True)
credentials = directory / 'credentials.json'
if not credentials.exists():
    accounts = [
        {'email': os.environ.get('LAB_EMAIL_A', 'alice@example.test'), 'id': str(uuid.uuid4()), 'password': secrets.token_urlsafe(20)},
        {'email': os.environ.get('LAB_EMAIL_B', 'bob@example.test'), 'id': str(uuid.uuid4()), 'password': secrets.token_urlsafe(20)},
    ]
    credentials.write_text(json.dumps({
        'accounts': accounts, 'client_secret': secrets.token_urlsafe(32),
        'cookie_secret': base64.b64encode(secrets.token_bytes(32)).decode(),
        'api_key': secrets.token_urlsafe(32),
    }, indent=2) + '\n')
data = json.loads(credentials.read_text())
assert len({a['email'] for a in data['accounts']}) == 2, 'Two distinct account emails are required'
host = 'lab.ai-inference-basics.test'
origin = f'https://{host}:30443'
if not (directory / 'tls.crt').exists():
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-days', '30',
        '-subj', '/CN=AI Inference Basics local lab', '-addext', f'subjectAltName=DNS:{host}',
        '-addext', 'basicConstraints=critical,CA:TRUE',
        '-keyout', str(directory / 'tls.key'), '-out', str(directory / 'tls.crt'),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
dex = {
    'issuer': origin + '/dex', 'storage': {'type': 'kubernetes', 'config': {'inCluster': True}},
    'web': {'http': '0.0.0.0:5556'}, 'telemetry': {'http': '0.0.0.0:5558'},
    'enablePasswordDB': True, 'oauth2': {'skipApprovalScreen': True},
    'staticClients': [{'id': 'ai-inference-basics-browser', 'name': 'AI Inference Basics', 'secret': data['client_secret'],
                       'redirectURIs': [origin + '/oauth2/callback']}],
    'staticPasswords': [{'email': a['email'], 'username': a['email'], 'userID': a['id'],
                         'hash': bcrypt.hashpw(a['password'].encode(), bcrypt.gensalt()).decode()}
                        for a in data['accounts']],
}
# Discovery is skipped so private back-channel endpoints need no host DNS override.
# The issuer and public authorization URL remain exact and are still validated.
oauth = {
    'provider': 'oidc', 'provider_display_name': 'AI Inference Basics Dex',
    'oidc_issuer_url': origin + '/dex', 'skip_oidc_discovery': True,
    'login_url': origin + '/dex/auth', 'redeem_url': 'http://dex:5556/dex/token',
    'oidc_jwks_url': 'http://dex:5556/dex/keys',
    'client_id': 'ai-inference-basics-browser', 'client_secret': data['client_secret'],
    'cookie_secret': data['cookie_secret'], 'cookie_secure': True,
    'cookie_httponly': True, 'cookie_samesite': 'lax', 'cookie_expire': '8h',
    'redirect_url': origin + '/oauth2/callback', 'reverse_proxy': True,
    'http_address': '0.0.0.0:4180', 'skip_provider_button': True,
    'scope': 'openid profile email', 'code_challenge_method': 'S256',
    'authenticated_emails_file': '/etc/oauth/allowed-emails',
    'upstreams': ['http://headlamp:80/headlamp/',
                  'http://workspace-a:7681/terminal-a/', 'http://workspace-b:7681/terminal-b/',
                  'http://workspace-a:8080/preview-a/', 'http://workspace-b:8080/preview-b/',
                  'http://telemetry:3000/grafana/'],
    'trusted_ips': [],
    'request_logging': False,
    'pass_access_token': False, 'pass_authorization_header': False,
    'pass_basic_auth': False, 'set_authorization_header': False,
}
def toml_value(value):
    return json.dumps(value)
oauth_config = '\n'.join(f'{k} = {toml_value(v)}' for k, v in oauth.items()) + '\n'
def secret(name, values, kind='Opaque'):
    return {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': name, 'namespace': 'ai-inference-basics'},
            'type': kind, 'stringData': values}
objects = [
    secret('ai-inference-basics-dex', {'config.yaml': yaml.safe_dump(dex)}),
    secret('ai-inference-basics-oauth', {'oauth2-proxy.cfg': oauth_config,
                        'allowed-emails': '\n'.join(a['email'] for a in data['accounts']) + '\n'}),
    secret('ai-inference-basics-api-key', {'lab': data['api_key']}),
    secret('ai-inference-basics-ca', {'ca.crt': (directory / 'tls.crt').read_text()}),
    secret('ai-inference-basics-tls', {'tls.crt': (directory / 'tls.crt').read_text(),
                       'tls.key': (directory / 'tls.key').read_text()}, 'kubernetes.io/tls'),
]
subprocess.run(['bash', 'scripts/guest.sh', 'sudo /usr/local/bin/k0s kubectl create namespace ai-inference-basics --dry-run=client -o yaml | sudo /usr/local/bin/k0s kubectl apply -f -'], check=True)
subprocess.run(['bash', 'scripts/guest.sh', 'sudo /usr/local/bin/k0s kubectl apply --server-side --field-manager=ai-inference-basics-secrets -f -'],
               input=yaml.safe_dump_all(objects).encode(), check=True)
print('Local secrets installed. Credentials remain in .local/secrets/credentials.json (0600).')
