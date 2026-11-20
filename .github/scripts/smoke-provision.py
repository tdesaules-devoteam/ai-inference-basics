"""Exercise the clients needed by credential, bucket and model import jobs."""
import subprocess
import bcrypt
import boto3
import huggingface_hub
import yaml

assert bcrypt.checkpw(b'fixture', bcrypt.hashpw(b'fixture', bcrypt.gensalt(4)))
assert 's3' in boto3.Session().get_available_services()
assert callable(huggingface_hub.snapshot_download) and yaml.safe_load('ok: true')['ok']
for command in (['rc', '--version'], ['kubectl', 'version', '--client']):
    subprocess.run(command, check=True)
