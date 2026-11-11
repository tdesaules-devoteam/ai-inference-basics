#!/usr/bin/env python3
"""Guest-only provisioning. k0s owns all Helm release installation and upgrades."""
import base64
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
import secrets

import bcrypt
import yaml

NS = 'ai-inference-basics'
K0S = '/usr/local/bin/k0s'


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def wait(check, description, seconds=1200):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        time.sleep(3)
    raise RuntimeError(f'Timed out waiting for {description}')


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
    ]


def prepare_config(template, hostname, artifacts):
    assert re.fullmatch(r'[a-z0-9.-]+', hostname), 'Invalid VM hostname'
    assert re.fullmatch(r'localhost/ai-inference-basics-bastion@sha256:[a-f0-9]{64}', artifacts['image'])
    config = yaml.safe_load(template)
    config['spec']['api']['sans'].append(hostname)
    for chart in config['spec']['extensions']['helm']['charts']:
        assert chart['version'] == artifacts['version'], 'Chart version differs from k0s.yaml'
        chart['values'] = chart['values'].replace('__LAB_HOSTNAME__', hostname).replace('__BASTION_IMAGE__', artifacts['image'])
    return yaml.safe_dump(config, sort_keys=False)


def charts_ready(items, chart_file):
    ours = [c for c in items if c['spec'].get('chartName') == str(chart_file)]
    # k0s 1.37.2 does not populate Chart.status.status. Its successful reconciler
    # records the release name, version and positive revision, and clears error.
    return len(ours) == 4 and all(
        c.get('status', {}).get('releaseName') == c['spec'].get('releaseName')
        and bool(c.get('status', {}).get('releaseName'))
        and c['status'].get('version') == c['spec']['version']
        and c['status'].get('revision', 0) > 0
        and not c['status'].get('error')
        for c in ours)


def main():
    os.umask(0o077)
    workspace = Path(sys.argv[1]).resolve()
    state = Path('/var/lib/ai-inference-basics')
    state.mkdir(parents=True, exist_ok=True)
    artifacts = json.loads(Path('/etc/ai-inference-basics/artifacts.json').read_text())
    for name, expected in ((artifacts['chart_file'], artifacts['chart_sha256']),
                           (artifacts['image_archive'], artifacts['image_archive_sha256'])):
        assert Path(name).name == name, 'Artifact filename must not contain a path'
        with (workspace / '.local/build' / name).open('rb') as source:
            assert hashlib.file_digest(source, 'sha256').hexdigest() == expected, f'Artifact integrity failure: {name}'
    chart_file = Path('/var/lib/k0s/charts/ai-inference-basics.tgz')
    chart_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(workspace / '.local/build' / artifacts['chart_file'], chart_file)
    hostname = socket.gethostname().rstrip('.')
    config = prepare_config(Path('/etc/ai-inference-basics/k0s.yaml').read_text(), hostname, artifacts)
    Path('/etc/k0s').mkdir(exist_ok=True)
    Path('/etc/k0s/k0s.yaml').write_text(config)
    manifests = Path('/var/lib/k0s/manifests/ai-inference-basics')
    manifests.mkdir(parents=True, exist_ok=True)
    (manifests / 'credentials.yaml').write_text(yaml.safe_dump_all(credentials(state, hostname)))
    if subprocess.run(['systemctl', 'cat', 'k0scontroller.service'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        run(K0S, 'install', 'controller', '--single', '--enable-worker', '--no-taints', '--config', '/etc/k0s/k0s.yaml')
    run('systemctl', 'enable', '--now', 'k0scontroller')
    wait(lambda: subprocess.run([K0S, 'ctr', 'version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10).returncode == 0,
         'embedded containerd', 180)
    run(K0S, 'ctr', 'images', 'import', '--digests', str(workspace / '.local/build' / artifacts['image_archive']))
    run(K0S, 'ctr', 'images', 'tag', '--force', 'localhost/ai-inference-basics-bastion:dev', artifacts['image'])
    wait(lambda: subprocess.run([K0S, 'kubectl', 'get', '--raw=/readyz', '--request-timeout=5s'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
         'Kubernetes API', 180)
    run(K0S, 'kubectl', 'wait', 'node', '--all', '--for=condition=Ready', '--timeout=180s')
    def releases_ready():
        charts = json.loads(subprocess.check_output([K0S, 'kubectl', 'get', 'charts.helm.k0sproject.io', '-n', 'kube-system', '-o', 'json', '--request-timeout=5s']))
        return charts_ready(charts['items'], chart_file)
    wait(releases_ready, 'four ordered releases managed by the k0s Helm deployer')
    run(K0S, 'kubectl', '-n', NS, 'wait', 'llmisvc/' + NS + '-chat', 'isvc/' + NS + '-embeddings',
        'isvc/' + NS + '-rerank', '--for=condition=Ready', '--timeout=900s')
    user = pwd.getpwnam(workspace.parent.name)
    kube_dir = Path(user.pw_dir) / '.kube'
    kube_dir.mkdir(mode=0o700, exist_ok=True)
    kubeconfig = kube_dir / 'config'
    kubeconfig.write_bytes(subprocess.check_output([K0S, 'kubeconfig', 'admin']))
    os.chown(kube_dir, user.pw_uid, user.pw_gid)
    os.chown(kubeconfig, user.pw_uid, user.pw_gid)
    for participant in ('a', 'b'):
        raw = subprocess.check_output([K0S, 'kubectl', '-n', NS, 'exec', f'deployment/workspace-{participant}',
                                       '-c', 'terminal', '--', 'cat', '/workspace/.local/share/ai-inference-basics/web-login.txt']).decode()
        tokens = re.findall(r'^.+: (\S+)$', raw, re.M)
        assert len(tokens) == 1, 'Unexpected Zellij token output'
        (state / f'zellij-{participant}.token').write_text(tokens[0] + '\n')
    (state / 'ready').write_text('Native k0s and four Helm deployer releases ready.\n')
    print(f'Lab ready at https://{hostname}:30443/headlamp/; credentials remain in {state}.')


if __name__ == '__main__':
    main()
