#!/usr/bin/env python3
"""Prepare final configuration and credential manifests on the workstation."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
import secrets

import bcrypt
import yaml

NS = 'ai-inference-basics'


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def secret(name, data, kind='Opaque'):
    return {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': name, 'namespace': NS},
            'type': kind, 'stringData': data}


def credentials(state, hostname):
    path = state / 'credentials.json'
    if not path.exists():
        data = {'accounts': [{'email': email, 'id': str(uuid.uuid4()), 'password': secrets.token_urlsafe(20)}
                             for email in ('alice@example.test', 'bob@example.test')],
                'client_secret': secrets.token_urlsafe(32),
                'cookie_secret': base64.b64encode(secrets.token_bytes(32)).decode(),
                'api_key': secrets.token_urlsafe(32)}
        for account in data['accounts']:
            account['hash'] = bcrypt.hashpw(account['password'].encode(), bcrypt.gensalt()).decode()
        path.write_text(json.dumps(data, indent=2) + '\n')
    data = json.loads(path.read_text())
    if not (state / 'tls.crt').exists():
        run('openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-days', '30',
            '-subj', '/CN=AI Inference Basics local lab', '-addext', f'subjectAltName=DNS:{hostname}',
            '-addext', 'basicConstraints=critical,CA:TRUE', '-keyout', str(state / 'tls.key'),
            '-out', str(state / 'tls.crt'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    origin = f'https://{hostname}:30443'
    dex = {
        'issuer': origin + '/dex', 'storage': {'type': 'kubernetes', 'config': {'inCluster': True}},
        'web': {'http': '0.0.0.0:5556'}, 'telemetry': {'http': '0.0.0.0:5558'},
        'enablePasswordDB': True, 'oauth2': {'skipApprovalScreen': True},
        'staticClients': [{'id': NS + '-browser', 'name': 'AI Inference Basics',
                           'secret': data['client_secret'], 'redirectURIs': [origin + '/oauth2/callback']}],
        'staticPasswords': [{'email': a['email'], 'username': a['email'], 'userID': a['id'], 'hash': a['hash']}
                            for a in data['accounts']],
    }
    oauth = {
        'provider': 'oidc', 'provider_display_name': 'AI Inference Basics Dex',
        'oidc_issuer_url': origin + '/dex', 'skip_oidc_discovery': True,
        'login_url': origin + '/dex/auth', 'redeem_url': 'http://dex:5556/dex/token',
        'oidc_jwks_url': 'http://dex:5556/dex/keys', 'client_id': NS + '-browser',
        'client_secret': data['client_secret'], 'cookie_secret': data['cookie_secret'],
        'cookie_secure': True, 'cookie_httponly': True, 'cookie_samesite': 'lax', 'cookie_expire': '8h',
        'redirect_url': origin + '/oauth2/callback', 'reverse_proxy': True,
        'http_address': '0.0.0.0:4180', 'skip_provider_button': True,
        'scope': 'openid profile email', 'code_challenge_method': 'S256',
        'authenticated_emails_file': '/etc/oauth/allowed-emails', 'request_logging': False,
        'upstreams': ['http://headlamp:80/headlamp/', 'http://telemetry:3000/grafana/',
                      *[f'http://workspace-{p}:7681/terminal-{p}/' for p in ('a', 'b')],
                      *[f'http://workspace-{p}:8080/preview-{p}/' for p in ('a', 'b')]],
        'pass_access_token': False, 'pass_authorization_header': False,
        'pass_basic_auth': False, 'set_authorization_header': False,
    }
    return [
        {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': NS}},
        secret(NS + '-dex', {'config.yaml': yaml.safe_dump(dex)}),
        secret(NS + '-oauth', {'oauth2-proxy.cfg': '\n'.join(f'{k} = {json.dumps(v)}' for k, v in oauth.items()) + '\n',
                               'allowed-emails': '\n'.join(a['email'] for a in data['accounts']) + '\n'}),
        secret(NS + '-api-key', {'lab': data['api_key']}),
        secret(NS + '-ca', {'ca.crt': (state / 'tls.crt').read_text()}),
        secret(NS + '-tls', {'tls.crt': (state / 'tls.crt').read_text(), 'tls.key': (state / 'tls.key').read_text()}, 'kubernetes.io/tls'),
        secret(NS + '-access', {'credentials.json': json.dumps(data)}),
    ]


def prepare_config(template, hostname, version, image):
    assert re.fullmatch(r'[a-z0-9.-]+', hostname), 'Invalid VM hostname'
    assert re.fullmatch(r'localhost/ai-inference-basics-bastion@sha256:[a-f0-9]{64}', image)
    config = yaml.safe_load(template)
    config['spec']['api']['sans'].append(hostname)
    for chart in config['spec']['extensions']['helm']['charts']:
        assert chart['version'] == version, 'Chart version differs from k0s.yaml'
        chart['values'] = chart['values'].replace('__LAB_HOSTNAME__', hostname).replace('__BASTION_IMAGE__', image)
    return yaml.safe_dump(config, sort_keys=False)


def main():
    os.umask(0o077)
    root = Path(__file__).resolve().parent.parent
    identity = (root / '.devenv/.uuid').read_text().strip()
    assert str(uuid.UUID(identity)) == identity, 'Invalid persisted VM identity'
    build = root / '.local/build'
    state = build / 'runtime'
    marker = state / '.generated'
    if state.exists() and any(state.iterdir()) and not marker.exists():
        raise RuntimeError('Existing runtime preparation directory is not marked as generated; inspect it before continuing.')
    state.mkdir(parents=True, exist_ok=True)
    marker.touch()
    hostname = identity + '.local'
    version = str(yaml.safe_load((root / 'charts/ai-inference-basics/Chart.yaml').read_text())['version'])
    image = (build / 'bastion.ref').read_text().strip()
    config = prepare_config((root / 'infra/k0s/k0s.yaml').read_text(), hostname, version, image)
    (state / 'k0s.yaml').write_text(config)
    (state / 'credentials.yaml').write_text(yaml.safe_dump_all(credentials(state, hostname)))
    print('Prepared the final k0s.yaml and private credential manifests for direct Ignition copies.')


if __name__ == '__main__':
    main()
