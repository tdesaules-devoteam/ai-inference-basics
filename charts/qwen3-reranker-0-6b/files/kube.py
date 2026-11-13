"""Small in-cluster API client for domain-local credential Jobs."""
import base64
import json
import os
from pathlib import Path
import ssl
from urllib.error import HTTPError
from urllib.request import Request, urlopen

os.umask(0o077)
account = Path('/var/run/secrets/kubernetes.io/serviceaccount')
namespace = (account / 'namespace').read_text().strip()
context = ssl.create_default_context(cafile=str(account / 'ca.crt'))
token = (account / 'token').read_text().strip()


def api(method, path, body=None):
    request = Request('https://kubernetes.default.svc' + path, method=method,
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
                      data=json.dumps(body).encode() if body is not None else None)
    with urlopen(request, context=context, timeout=20) as response:
        return json.load(response)


def read(name, ns=namespace, kind='secrets'):
    try:
        return api('GET', f'/api/v1/namespaces/{ns}/{kind}/{name}')
    except HTTPError as error:
        error.close()
        if error.code == 404:
            return None
        raise RuntimeError(f'Cannot read {kind}/{ns}/{name}: HTTP {error.code}') from None


def data(resource):
    if resource is None:
        raise RuntimeError('Required domain dependency is missing')
    if resource['kind'] == 'Secret':
        return {k: base64.b64decode(v).decode() for k, v in resource['data'].items()}
    return resource['data']


def write(name, values, kind='secrets', annotations=None):
    existing = read(name, kind=kind)
    encoded = {k: base64.b64encode(v.encode()).decode() for k, v in values.items()} if kind == 'secrets' else values
    if existing and existing.get('data') == encoded and existing['metadata'].get('annotations', {}) == (annotations or {}):
        return existing
    resource = {'apiVersion': 'v1', 'kind': 'Secret' if kind == 'secrets' else 'ConfigMap',
                'metadata': {'name': name, 'namespace': namespace,
                             'labels': {'app.kubernetes.io/managed-by': 'domain-credentials'},
                             'annotations': annotations or {}}, 'data': encoded}
    if kind == 'secrets':
        resource['type'] = 'Opaque'
    collection = f'/api/v1/namespaces/{namespace}/{kind}'
    if existing:
        resource['metadata']['resourceVersion'] = existing['metadata']['resourceVersion']
        return api('PUT', collection + '/' + name, resource)
    try:
        return api('POST', collection, resource)
    except HTTPError as error:
        error.close()
        if error.code != 409:
            raise
        return read(name, kind=kind)
