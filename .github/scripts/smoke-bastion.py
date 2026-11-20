"""Execute inside the native candidate; check real CLI runtimes and packaged UI."""
from pathlib import Path
import subprocess
import json5

for command in ('kubectl version --client', 'k9s version', 'ttyd --version', 'zellij --version',
                'starship --version', 'hx --version', 'code-server --version', 'curl --version',
                'jq --version', 'vllm bench serve --help'):
    subprocess.run(command.split(), stdout=subprocess.DEVNULL, check=True)
assert Path('/usr/share/ai-inference-basics/ttyd.html').stat().st_size > 0
assert json5.loads('{editor:"hx"}')['editor'] == 'hx'
