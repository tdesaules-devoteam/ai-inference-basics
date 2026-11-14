#!/usr/bin/env python3
"""Validate the infrastructure input before Helmfile evaluates releases.

Only --emit outputs the input, for Helmfile's internal template evaluation.
Validation errors report paths and constraints, never credential values.
"""
import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('definition', type=Path)
parser.add_argument('--emit', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
try:
    definition = json.loads(args.definition.read_text())
    schema = json.loads((root / 'infra/infra-definition.schema.json').read_text())
except (OSError, ValueError):
    sys.exit('Cannot read infrastructure definition or schema as JSON.')
errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(definition))
if errors:
    for error in errors:
        print('Invalid infrastructure field: ' + '.'.join(map(str, error.absolute_path)) +
              ' (' + str(error.validator) + ')', file=sys.stderr)
    sys.exit(1)
if len(definition['access']['adminPassword'].encode()) > 72:
    sys.exit('adminPassword exceeds bcrypt\'s 72-byte limit.')
if definition['environment'] == 'devenv' and (len(definition['machines']) != 1 or definition['machines'][0]['count'] != 1):
    sys.exit('devenv supports exactly one machine.')
if len({machine['name'] for machine in definition['machines']}) != len(definition['machines']):
    sys.exit('Machine names must be unique.')
if args.emit:
    print(json.dumps(definition))
else:
    print('Infrastructure definition is valid.')
