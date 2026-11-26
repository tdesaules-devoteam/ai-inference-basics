#!/usr/bin/env python3
"""Extract the lab operations from predictor specs, or assemble them for Helmfile."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'openapi'
# Route type and a short request usable in Scalar's Test Request client.
OPERATIONS = {
    'chat': {
        '/v1/chat/completions': ('completions', {
            'messages': [{'role': 'user', 'content': 'Explain embeddings in one sentence.'}],
            'max_tokens': 64, 'chat_template_kwargs': {'enable_thinking': False}}),
        '/v1/responses': ('responses', {'input': 'Say hello.', 'max_output_tokens': 64, 'store': False}),
    },
    'embeddings': {'/v1/embeddings': ('embeddings', {'input': ['Paris is in France.', 'Berlin is in Germany.']})},
    'rerank': {
        '/v2/rerank': ('rerank', {'query': 'Capital of France?', 'documents': ['Paris', 'Berlin'], 'top_n': 2}),
        '/score': ('http', {'text_1': 'Capital of France?', 'text_2': 'Paris'}),
    },
}


def extract(task, source):
    """Namespace schema refs, including discriminator mappings, and retain their transitive closure."""
    schemas = {}
    def visit(value):
        if isinstance(value, str) and value.startswith('#/components/schemas/'):
            name = value.removeprefix('#/components/schemas/')
            key = task + '_' + name
            if key not in schemas:
                schemas[key] = None  # recursive schemas can reference themselves
                schemas[key] = visit(source['components']['schemas'][name])
            return '#/components/schemas/' + key
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, dict):
            return {k: visit(v) for k, v in value.items()}
        return value
    paths = {path: {'post': visit(source['paths'][path]['post'])} for path in OPERATIONS[task]}
    return {'openapi': source['openapi'], 'paths': paths, 'schemas': schemas}


def render(origin, models):
    catalog = {'object': 'list', 'data': []}
    spec = {'openapi': '3.1.0', 'info': {'title': 'Lab model API', 'version': '0.34.0'},
            'servers': [{'url': origin}], 'security': [{'modelKey': []}], 'paths': {}, 'components': {
                'securitySchemes': {'modelKey': {'type': 'http', 'scheme': 'bearer'}}, 'schemas': {}}}
    operations = []
    for model, settings in sorted(models.items()):
        task = settings['task']
        fragment = json.loads((ROOT / (task + '.json')).read_text())
        assert fragment['openapi'] == spec['openapi']
        spec['components']['schemas'].update(fragment['schemas'])
        if settings['replicas']:
            catalog['data'].append({'id': model, 'object': 'model', 'owned_by': 'lab', 'created': 0})
        for path, (fmt, example) in OPERATIONS[task].items():
            if path in spec['paths']:
                raise ValueError(f'Multiple enabled predictors for {path}')
            op = fragment['paths'][path]['post']
            op['summary'] = path
            content = op['requestBody']['content']['application/json']
            content['schema'] = {'allOf': [content['schema'], {'type': 'object', 'required': ['model'],
                                'properties': {'model': {'type': 'string', 'enum': [model]}}}]}
            content['examples'] = {'default': {'summary': model, 'value': {'model': model, **example}}}
            if fmt in ('completions', 'responses'):
                content['examples']['streaming'] = {'value': dict(content['examples']['default']['value'], stream=True)}
                op['responses']['200'].setdefault('content', {})['text/event-stream'] = {'schema': {'type': 'string'}}
            spec['paths'][path] = {'post': op}
            operations.append({'name': model + '-' + path.strip('/').replace('/', '-'), 'model': model, 'path': path, 'format': fmt})
    entry = {'type': 'object', 'required': ['id', 'object', 'created', 'owned_by'], 'properties': {
        'id': {'type': 'string'}, 'object': {'const': 'model'}, 'created': {'type': 'integer'}, 'owned_by': {'type': 'string'}}}
    spec['paths']['/v1/models'] = {'get': {'operationId': 'listModels', 'summary': '/v1/models', 'responses': {
        '200': {'description': 'Configured active models', 'content': {'application/json': {'schema': {'type': 'object',
        'properties': {'object': {'const': 'list'}, 'data': {'type': 'array', 'items': entry}}}}}}}}}
    spec['paths']['/openapi.json'] = {'get': {'operationId': 'getContract', 'summary': '/openapi.json',
        'security': [], 'responses': {'200': {'description': 'Public OpenAPI document',
        'content': {'application/json': {'schema': {'type': 'object'}}}}}}}
    return {'spec': spec, 'catalog': catalog, 'operations': operations}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    snapshot = commands.add_parser('extract')
    snapshot.add_argument('task', choices=OPERATIONS)
    snapshot.add_argument('source', type=Path)
    assemble = commands.add_parser('render')
    assemble.add_argument('origin')
    assemble.add_argument('models')
    args = parser.parse_args()
    if args.command == 'extract':
        (ROOT / (args.task + '.json')).write_text(json.dumps(extract(args.task, json.loads(args.source.read_text())), indent=2) + '\n')
    else:
        print(json.dumps(render(args.origin, json.loads(args.models)), separators=(',', ':')))
