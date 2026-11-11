#!/usr/bin/env python3
"""Place the exact local chart package and participant tasks in both workspaces."""
import hashlib
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent
target = root / '.local/chart'
target.mkdir(parents=True, exist_ok=True)
subprocess.run(['bash', str(root / 'scripts/helm.sh'), 'package', 'charts/ai-inference-basics', '--destination', str(target)], check=True)
archives = list(target.glob('ai-inference-basics-*.tgz'))
assert len(archives) == 1, 'Keep exactly the current chart version in .local/chart'
payloads = {
    'platform.tgz': archives[0].read_bytes(),
    'taskfile.yml': (root / 'images/admin-workspace/taskfile.yml').read_bytes(),
}
for participant in ('a', 'b'):
    for filename, data in payloads.items():
        write = f'cat > /workspace/{filename}'
        if filename == 'taskfile.yml':
            write = 'if [ -e /workspace/taskfile.yml ]; then cat > /dev/null; else cat > /workspace/taskfile.yml; fi'
        command = f"sudo /usr/local/bin/k0s kubectl -n ai-inference-basics exec -i deployment/workspace-{participant} -c terminal -- sh -c '{write}'"
        subprocess.run(['bash', str(root / 'scripts/guest.sh'), command], input=data, check=True)
print('Seeded participant tasks and chart SHA256 ' + hashlib.sha256(payloads['platform.tgz']).hexdigest())
