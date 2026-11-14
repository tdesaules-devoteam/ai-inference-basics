"""Own the browser session configuration; read only Dex's published client secret."""
import base64
import json
import os
import secrets

import kube

client = kube.data(kube.read('oidc-client', ns='dex'))
previous = kube.read('browser-session')
cookie = kube.data(previous)['cookie-secret'] if previous else base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
cookie = kube.data(kube.write('browser-session', {'cookie-secret': cookie}))['cookie-secret']
origin = 'https://' + os.environ['LAB_HOSTNAME'] + ':30443'
config = {
    'provider': 'oidc', 'provider_display_name': 'Lab admin', 'oidc_issuer_url': origin + '/dex',
    'skip_oidc_discovery': True, 'login_url': origin + '/dex/auth',
    'redeem_url': 'http://dex.dex.svc.cluster.local:5556/dex/token',
    'oidc_jwks_url': 'http://dex.dex.svc.cluster.local:5556/dex/keys',
    'client_id': client['client-id'], 'client_secret': client['client-secret'],
    'cookie_secret': cookie, 'cookie_secure': True, 'cookie_httponly': True,
    'cookie_samesite': 'lax', 'cookie_expire': '8h', 'redirect_url': origin + '/oauth2/callback',
    'reverse_proxy': True, 'http_address': '0.0.0.0:4180', 'skip_provider_button': True,
    'scope': 'openid profile email', 'code_challenge_method': 'S256',
    'authenticated_emails_file': '/etc/oauth/allowed-emails', 'request_logging': False,
    'upstreams': ['http://127.0.0.1:4181/'], 'pass_access_token': False,
    'pass_authorization_header': False, 'pass_basic_auth': False,
    'set_authorization_header': False, 'pass_user_headers': True,
}
kube.write('oauth-config', {'oauth2-proxy.cfg': '\n'.join(f'{k} = {json.dumps(v)}' for k, v in config.items()) + '\n',
                           'allowed-emails': client['admin-email'] + '\n'})
print('Admin browser session configuration is ready.')
