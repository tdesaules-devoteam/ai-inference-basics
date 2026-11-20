"""Execute inside the native candidate; check real CLI runtimes and packaged UI."""
from pathlib import Path
import os
import subprocess
import tempfile
import json5

with tempfile.TemporaryDirectory(prefix='bastion-home-') as home:
    # Docker actions receive a runner-owned HOME, unlike the lab's writable PVC.
    env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=f'{home}/config', XDG_CACHE_HOME=f'{home}/cache',
               XDG_DATA_HOME=f'{home}/data', XDG_RUNTIME_DIR=home)
    for command in ('kubectl version --client', 'k9s version', 'ttyd --version', 'zellij --version',
                    'starship --version', 'hx --version', 'code-server --version', 'curl --version',
                    'jq --version', 'vllm bench serve --help'):
        subprocess.run(command.split(), env=env, stdout=subprocess.DEVNULL, check=True)
assert Path('/usr/share/ai-inference-basics/ttyd.html').stat().st_size > 0
assert json5.loads('{editor:"hx"}')['editor'] == 'hx'
