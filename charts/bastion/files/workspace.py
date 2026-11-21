"""Initialize the persistent repository and editor defaults without resetting user work."""
import json
import os
from pathlib import Path
import subprocess
import json5

os.umask(0o077)
settings = Path('/workspace/.local/share/code-server/User/settings.json')
settings.parent.mkdir(parents=True, exist_ok=True)
preferences = json5.loads(settings.read_text()) if settings.exists() else {}
desired = {'workbench.colorTheme': os.environ['EDITOR_THEME'], 'window.autoDetectColorScheme': False,
           'editor.fontFamily': 'Geist Mono, Symbols Nerd Font Mono, monospace',
           'terminal.integrated.fontFamily': 'Geist Mono, Symbols Nerd Font Mono, monospace'}
if any(preferences.get(key) != value for key, value in desired.items()):
    # Keep the original JSONC once; later pod restarts must not replace that backup.
    backup = settings.with_name('settings.before-lab-theme.jsonc')
    if settings.exists() and not backup.exists():
        backup.write_text(settings.read_text())
    preferences.update(desired)
    settings.write_text(json.dumps(preferences, indent=2) + '\n')
extension = Path('/workspace/.local/share/code-server/extensions/arcticicestudio.nord-visual-studio-code-0.19.0')
if not extension.exists():
    subprocess.run(['code-server', '--install-extension', '/usr/share/ai-inference-basics/ui-assets/nord.vsix'], check=True)
repository = Path(os.environ['REPOSITORY_DIRECTORY'])
if not (repository / '.git').exists():
    if repository.exists() and any(repository.iterdir()):
        raise RuntimeError('Refusing to replace a nonempty repository directory')
    subprocess.run(['git', 'clone', '--recurse-submodules', '--', os.environ['REPOSITORY_URL'], str(repository)], check=True)
print('Persistent repository and editor defaults are ready.')
