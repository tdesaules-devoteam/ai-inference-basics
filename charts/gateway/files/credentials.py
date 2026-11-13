"""Preserve the API key; publish only public CA bytes for client domains."""
import secrets
import sys
import time

import kube

if sys.argv[1] == 'key':
    existing = kube.read('lab-api-key')
    if existing:
        assert kube.data(existing)['lab'], 'Empty API key'
    else:
        kube.write('lab-api-key', {'lab': secrets.token_urlsafe(32)})
    print('Gateway API key ready.')
else:
    deadline = time.monotonic() + 300
    while True:
        ca = kube.read('lab-root-ca')
        if ca and ca.get('data', {}).get('tls.crt'):
            break
        if time.monotonic() > deadline:
            raise RuntimeError('CA issuance timed out')
        time.sleep(2)
    kube.write('lab-ca', {'ca.crt': kube.data(ca)['tls.crt']}, kind='configmaps')
    print('Public CA certificate ready for clients.')
