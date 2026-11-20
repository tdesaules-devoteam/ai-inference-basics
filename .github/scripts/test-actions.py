#!/usr/bin/env python3
"""Exercise the local fixed-operation binaries against disposable Git and OCI fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GITHUB_OUTPUT=str(root/'output'), GITHUB_EVENT_PATH=str(root/'event.json'),
               GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REF='refs/heads/main')

    def run(*cmd, ok=True):
        result = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True)
        assert (result.returncode == 0) == ok, (cmd, result.stderr)
        return result.stdout.strip()

    for name in ('check', 'record-qualification', 'tag-images'):
        run('go', 'build', '-o', str(root/name), str(ROOT/'.github/actions'/name/'main.go'))
    run('git', 'init', '-qb', 'main'); run('git', 'config', 'user.name', 'Fixture'); run('git', 'config', 'user.email', 'fixture@example.org')
    run('git', 'commit', '--allow-empty', '-qm', 'initial'); before = run('git', 'rev-parse', 'HEAD')
    (root/'oci/provision').mkdir(parents=True); (root/'oci/provision/Containerfile').touch()
    run('git', 'add', 'oci'); run('git', 'commit', '-qm', 'fix: change provision')
    (root/'event.json').write_text(json.dumps({'before':before})); env.update(GITHUB_EVENT_NAME='push', GITHUB_SHA=run('git','rev-parse','HEAD'))
    (root/'output').touch(); run('./check'); assert 'images=["provision"]' in (root/'output').read_text()
    env.update(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REF='refs/heads/topic'); run('./check',ok=False)
    env['GITHUB_REF']='refs/heads/main'; rev=env['GITHUB_SHA']; dist=root/'dist'; dist.mkdir(); digest='sha256:'+'a'*64
    for name in ('bastion','provision'):
        env.update(COMPONENT=name,CANDIDATE_DIGEST=digest); archive=dist/'image.oci.tar'; archive.write_bytes(b'fixture')
        (dist/'build.json').write_text(json.dumps(dict(image=name,arch='amd64',version=rev,revision=rev,tested=False,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))
        archive.write_bytes(b'corrupt'); run('./record-qualification', ok=False); archive.write_bytes(b'fixture'); run('./record-qualification'); (dist/name).mkdir(); (dist/'qualified.json').rename(dist/name/'qualified.json')
    run('git','init','--bare','-q','remote');run('git','remote','add','origin',str(root/'remote'));run('git','push','origin','main');env.update(VERSION='1.0.0',BASTION_DIGEST=digest,PROVISION_DIGEST='wrong');run('./tag-images',ok=False)
    env['PROVISION_DIGEST']=digest;run('./tag-images');env.update(GITHUB_REF='refs/tags/1.0.0',GITHUB_EVENT_NAME='push');run('./check');assert f'"bastion":"{digest}"' in (root/'output').read_text()
print('CI fixtures passed: changed-image plan, dispatch policy, corruption, digest mismatch and annotated tag round trip.')
