#!/usr/bin/env python3
"""Run the current Helmfile render contracts (no cluster operations)."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
if len(sys.argv) != 1:
    sys.exit('Validate the Helmfile platform with no arguments; the former umbrella archive is unsupported.')
for script in ('validate_storage.py', 'validate_lab.py'):
    subprocess.run([sys.executable, str(root / 'tests' / script)], cwd=root, check=True)
