#!/usr/bin/env python3
"""Wait for the installed lab; no installation, restart or Helm CLI calls."""
import json
from pathlib import Path
import subprocess
import time

NS = 'ai-inference-basics'
K0S = 'sudo /usr/local/bin/k0s'


def charts_ready(items):
    ours = [c for c in items if c['spec'].get('chartName') == '/var/lib/k0s/charts/ai-inference-basics.tgz']
    return len(ours) == 4 and all(
        c.get('status', {}).get('releaseName') == c['spec'].get('releaseName')
        and bool(c.get('status', {}).get('releaseName'))
        and c['status'].get('version') == c['spec']['version']
        and c['status'].get('revision', 0) > 0
        and not c['status'].get('error') for c in ours)


def main():
    root = Path(__file__).resolve().parent.parent
    host = (root / '.devenv/.uuid').read_text().strip() + '.local'
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o', 'StrictHostKeyChecking=no',
           '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ProxyCommand=none', host]
    deadline = time.monotonic() + 1800
    while time.monotonic() < deadline:
        try:
            failed = subprocess.run(ssh + ['systemctl is-failed --quiet ai-inference-basics-bootstrap.service'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            if failed.returncode == 0:
                raise RuntimeError('Guest initialization failed; use task ssh and inspect its systemd journal.')
            data = subprocess.check_output(ssh + [
                'sudo test -f /var/lib/ai-inference-basics/initialized && '
                + K0S + ' kubectl get charts.helm.k0sproject.io -n kube-system -o json --request-timeout=5s'],
                stderr=subprocess.DEVNULL, timeout=15)
            if charts_ready(json.loads(data)['items']):
                break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        time.sleep(3)
    else:
        raise RuntimeError('The k0s Helm deployer did not converge within 30 minutes.')
    subprocess.run(ssh + [K0S + ' kubectl wait node --all --for=condition=Ready --timeout=180s'], check=True)
    subprocess.run(ssh + [K0S + f' kubectl -n {NS} wait llmisvc/{NS}-chat isvc/{NS}-embeddings isvc/{NS}-rerank --for=condition=Ready --timeout=900s'], check=True)
    print(f'Lab ready: https://{host}:30443/headlamp/\nConnect with: task ssh')


if __name__ == '__main__':
    main()
