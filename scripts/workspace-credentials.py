#!/usr/bin/env python3
"""Copy native Zellij tokens to protected instructor files without printing them."""
import os
import pathlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent
os.umask(0o077)
directory = root / '.local/secrets'
directory.mkdir(parents=True, exist_ok=True)
for participant in ('a', 'b'):
    command = f'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics exec deployment/workspace-{participant} -c terminal -- cat /workspace/.local/share/ai-inference-basics/web-login.txt'
    raw = subprocess.check_output(['bash', str(root / 'scripts/guest.sh'), command]).decode()
    tokens = re.findall(r'^.+: (\S+)$', raw, re.M)
    assert len(tokens) == 1, 'Unexpected Zellij token output format'
    path = directory / f'zellij-{participant}.token'
    path.write_text(tokens[0] + '\n')
    path.chmod(0o600)
print('Zellij login tokens saved in .local/secrets/zellij-{a,b}.token (0600).')
