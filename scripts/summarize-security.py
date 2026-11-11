#!/usr/bin/env python3
"""Record advisory findings bound to the current administration OCI archive."""
import collections
import hashlib
import json
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent
report = root / '.local/admin-grype.json'
data = json.loads(report.read_text())
matches = data.get('matches', [])
manifest = subprocess.check_output(['skopeo', 'inspect', '--raw', 'oci-archive:' + str(root / '.local/admin.oci.tar')])
image_digest = 'sha256:' + hashlib.sha256(manifest).hexdigest()
sbom = json.loads((root / '.local/admin-sbom.json').read_text())
assert sbom['source']['metadata']['manifestDigest'] == image_digest, 'SBOM is for a different image'
workspace = json.loads((root / '.local/workspace-image.json').read_text())
assert workspace['image'].endswith('@' + image_digest)
result = {
    'scope': 'AMD64 Fedora Minimal administration image', 'image_digest': image_digest,
    'advisory_only': True,
    'findings_by_severity': dict(collections.Counter(x['vulnerability']['severity'] for x in matches)),
    'high_critical': [{'id': x['vulnerability']['id'], 'severity': x['vulnerability']['severity'],
                       'package': x['artifact']['name'], 'installed': x['artifact']['version'],
                       'fix': x['vulnerability'].get('fix', {})}
                      for x in matches if x['vulnerability']['severity'] in ('High', 'Critical')],
    'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest(),
    'local_report': '.local/admin-grype.json', 'local_sbom': '.local/admin-sbom.json',
    'database': data.get('descriptor', {}).get('db', {}),
}
output = root / 'reports/local-cpu/G0/security.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2) + '\n')
print('Advisory findings: ' + json.dumps(result['findings_by_severity']))
