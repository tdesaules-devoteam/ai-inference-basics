"""Initialize the persistent repository and editor defaults without resetting user work."""
import json
import os
from pathlib import Path
import subprocess

os.umask(0o077)
settings = Path('/workspace/.local/share/code-server/User/settings.json')
settings.parent.mkdir(parents=True, exist_ok=True)
if not settings.exists():
    with settings.open('x') as output:
        json.dump({'workbench.colorTheme': os.environ['EDITOR_THEME'],
                   'window.autoDetectColorScheme': False}, output, indent=2)
        output.write('\n')
repository = Path(os.environ['REPOSITORY_DIRECTORY'])
if not (repository / '.git').exists():
    if repository.exists() and any(repository.iterdir()):
        raise RuntimeError('Refusing to replace a nonempty repository directory')
    subprocess.run(['git', 'clone', '--recurse-submodules', '--', os.environ['REPOSITORY_URL'], str(repository)], check=True)
print('Persistent repository and editor defaults are ready.')
