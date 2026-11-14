"""Embed verified Nord/Geist assets so browsers need no external font service."""
import base64
import hashlib
from pathlib import Path
import ssl
import subprocess
import time
from urllib.request import urlopen
import zipfile

root = Path('/usr/share/ai-inference-basics')
assets = root / 'ui-assets'
assets.mkdir(exist_ok=True)
context = ssl.create_default_context(cafile='/etc/ssl/certs/ca-certificates.crt')
for line in (root / 'ui-assets.lock').read_text().splitlines():
    checksum, name, url = line.split()
    with urlopen(url, context=context, timeout=120) as response:
        content = response.read()
    assert hashlib.sha256(content).hexdigest() == checksum, name
    (assets / name).write_bytes(content)
with zipfile.ZipFile(assets / 'geist.zip') as archive:
    mono = archive.read('geist-font/GeistMono/webfonts/GeistMono[wght].woff2')
    sans = archive.read('geist-font/Geist/webfonts/Geist[wght].woff2')
with zipfile.ZipFile(assets / 'symbols.zip') as archive:
    symbols = archive.read('SymbolsNerdFontMono-Regular.ttf')
css = ''
local_css = ''
workbench = Path('/opt/code-server/lib/vscode/out/vs/code/browser/workbench/workbench.css')
fonts = workbench.parent / 'lab-fonts'
fonts.mkdir(exist_ok=True)
for family, content, mime, fmt in [('Geist Mono', mono, 'font/woff2', 'woff2'),
                                   ('Geist', sans, 'font/woff2', 'woff2'),
                                   ('Symbols Nerd Font Mono', symbols, 'font/ttf', 'truetype')]:
    encoded = base64.b64encode(content).decode()
    css += f'@font-face{{font-family:"{family}";src:url(data:{mime};base64,{encoded}) format("{fmt}");font-weight:100 900;font-display:swap;}}\n'
    filename = family.lower().replace(' ', '-') + '-' + hashlib.sha256(content).hexdigest()[:12] + ('.woff2' if fmt == 'woff2' else '.ttf')
    (fonts / filename).write_bytes(content)
    local_css += f'@font-face{{font-family:"{family}";src:url("./lab-fonts/{filename}") format("{fmt}");font-weight:100 900;font-display:swap;}}\n'
with workbench.open('a') as output:
    # code-server intentionally excludes data: from font-src; serve these as
    # same-origin static assets instead of weakening its Content Security Policy.
    output.write('\n' + local_css + '\n.monaco-workbench{font-family:"Geist",sans-serif;}\n')
html_path = workbench.with_name('workbench.html')
html_path.write_text(html_path.read_text().replace('workbench.css"',
    'workbench.css?lab-ui=' + hashlib.sha256(workbench.read_bytes()).hexdigest()[:12] + '"'))
process = subprocess.Popen(['ttyd', '--interface', '127.0.0.1', '--port', '17682', 'bash'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for attempt in range(100):
        try:
            with urlopen('http://127.0.0.1:17682/', timeout=2) as response:
                html = response.read().decode()
            break
        except OSError:
            if attempt == 99:
                raise
            time.sleep(0.1)
    assert '</head>' in html
    (root / 'ttyd.html').write_text(html.replace('</head>', '<style>' + css + '</style></head>', 1))
finally:
    process.terminate()
    process.wait(timeout=10)
