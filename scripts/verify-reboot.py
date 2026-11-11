#!/usr/bin/env python3
"""Reboot the owned VM and verify a new boot plus native k0s readiness."""
import json
import pathlib
import subprocess
import time

root = pathlib.Path(__file__).resolve().parent.parent
guest = ['bash', str(root / 'scripts/guest.sh')]
old = subprocess.check_output(guest + ['cat /proc/sys/kernel/random/boot_id'], timeout=15).strip()
subprocess.run(guest + ['sudo systemctl reboot'], timeout=15, check=True)
deadline = time.monotonic() + 180
while True:
    try:
        result = subprocess.run(guest + ['cat /proc/sys/kernel/random/boot_id'], capture_output=True, timeout=8)
        if result.returncode == 0 and result.stdout.strip() != old:
            break
    except subprocess.TimeoutExpired:
        pass
    if time.monotonic() > deadline:
        raise RuntimeError('VM did not return with a new boot ID')
    time.sleep(3)
deadline = time.monotonic() + 180
while True:
    try:
        ready = subprocess.run(guest + ['sudo /usr/local/bin/k0s kubectl get --raw=/readyz --request-timeout=5s'], capture_output=True, timeout=10)
        if ready.returncode == 0:
            break
    except subprocess.TimeoutExpired:
        pass
    if time.monotonic() >= deadline:
        raise RuntimeError('Kubernetes API did not become ready after reboot')
    time.sleep(3)
subprocess.run(['bash', str(root / 'scripts/verify-k0s.sh')], check=True, timeout=300)
subprocess.run(guest + ['sudo /usr/local/bin/k0s kubectl -n ai-inference-basics wait llmisvc/ai-inference-basics-chat isvc/ai-inference-basics-embeddings isvc/ai-inference-basics-rerank --for=condition=Ready --timeout=600s'], check=True, timeout=620)
report = root / 'reports/local-cpu/G1'
report.mkdir(parents=True, exist_ok=True)
(report / 'reboot.json').write_text(json.dumps({'new_boot_id': True, 'native_k0s_ready': True,
                                             'model_resources_ready': True}, indent=2) + '\n')
print('Reboot persistence passed; reopen the browser tunnel with task access:tunnel.')
