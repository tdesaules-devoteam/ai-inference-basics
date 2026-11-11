#!/usr/bin/env python3
"""Exercise the real local Dex login and Headlamp browser flow."""
import json
import pathlib
import subprocess
import uuid
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parent.parent
credentials = json.loads((root / '.local/secrets/credentials.json').read_text())
report = root / 'reports/local-cpu/G1'
report.mkdir(parents=True, exist_ok=True)
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=['--host-resolver-rules=MAP lab.ai-inference-basics.test 127.0.0.1'])
    for index, account in enumerate(credentials['accounts']):
        # TLS is separately checked with curl against the local CA. Browser trust
        # is scoped to this test context and does not alter workstation trust.
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto('https://lab.ai-inference-basics.test:30443/headlamp/')
        page.locator('input[name="login"]').fill('unauthorized@example.test')
        page.locator('input[name="password"]').fill('intentionally-invalid')
        page.locator('button[type="submit"]').click()
        page.get_by_text('Invalid Email Address and password.').wait_for(timeout=15000)
        page.locator('input[name="login"]').fill(account['email'])
        page.locator('input[name="password"]').fill('intentionally-invalid')
        page.locator('button[type="submit"]').click()
        page.get_by_text('Invalid Email Address and password.').wait_for(timeout=15000)
        page.locator('input[name="login"]').fill(account['email'])
        page.locator('input[name="password"]').fill(account['password'])
        page.locator('button[type="submit"]').click()
        page.get_by_role('button', name='Grant Access', exact=True).click()
        try:
            page.wait_for_url('**/headlamp/**', timeout=15000)
        except Exception:
            print(page.locator('body').inner_text()[:1000])
            raise
        page.wait_for_load_state('networkidle', timeout=30000)
        assert 'Headlamp' in page.title(), page.title()
        cookies = context.cookies()
        session = next(c for c in cookies if c['name'] == '_oauth2_proxy')
        assert session['secure'] and session['httpOnly'] and session['sameSite'] == 'Lax'
        page.screenshot(path=str(report / f'headlamp-account-{index + 1}.png'), mask=[page.locator('table')])
        participant = 'ab'[index]
        session_name = 'qa-' + uuid.uuid4().hex[:10]
        frames = []
        page.on('websocket', lambda ws: ws.on('framereceived', lambda frame: frames.append(frame)))
        page.goto(f'https://lab.ai-inference-basics.test:30443/terminal-{participant}/{session_name}')
        page.locator('#token').wait_for(timeout=30000)
        other_token = (root / f'.local/secrets/zellij-{"ba"[index]}.token').read_text().strip()
        rejected = page.evaluate('''async ({path, token}) => (await fetch(path, {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({auth_token: token, remember_me: false})
        })).status''', {'path': f'/terminal-{participant}/command/login', 'token': other_token})
        assert rejected == 401
        native_token = (root / f'.local/secrets/zellij-{participant}.token').read_text().strip()
        page.locator('#token').fill(native_token)
        page.get_by_role('button', name='Authenticate', exact=True).click()
        page.locator('.xterm-screen').click()
        native_session = next(c for c in context.cookies() if c['name'] == 'session_token')
        assert native_session['path'] == f'/terminal-{participant}/'
        assert native_session['secure'] and native_session['httpOnly']
        page.keyboard.type("printf 'AI_INFERENCE_BASICS_%s\\n' 'TERMINAL_READY'; kubectl -n demo get services -o custom-columns=NAME:.metadata.name,TYPE:.spec.type --no-headers; helm version --short; task --version")
        page.keyboard.press('Enter')
        for _ in range(100):
            text = ''.join(f.decode(errors='replace') if isinstance(f, bytes) else f for f in frames)
            if 'AI_INFERENCE_BASICS_TERMINAL_READY' in text and 'ClusterIP' in text:
                break
            page.wait_for_timeout(100)
        else:
            raise AssertionError('Terminal WebSocket did not return command output')
        page.screenshot(path=str(report / f'terminal-account-{index + 1}.png'))
        frames.clear()
        page.keyboard.type('k9s --readonly -c pods')
        page.keyboard.press('Enter')
        for _ in range(150):
            text = ''.join(f.decode(errors='replace') if isinstance(f, bytes) else f for f in frames)
            if '0.51.0' in text:
                break
            page.wait_for_timeout(100)
        else:
            raise AssertionError('k9s did not render its live interface in the browser terminal')
        page.keyboard.press('Control+c')
        preview = context.new_page()
        response = preview.goto(f'https://lab.ai-inference-basics.test:30443/preview-{participant}/')
        assert response.status == 502, response.status
        page.keyboard.type('kubectl -n demo port-forward --address 127.0.0.1 svc/whoami 18080:80')
        page.keyboard.press('Enter')
        for _ in range(30):
            response = preview.reload()
            if response.status == 200:
                break
            page.wait_for_timeout(200)
        assert response.status == 200
        assert 'AI Inference Basics preview is working' in preview.locator('body').inner_text()
        page.keyboard.press('Control+c')
        preview.close()
        page.goto('https://lab.ai-inference-basics.test:30443/oauth2/sign_out')
        assert not any(c['name'] == '_oauth2_proxy' for c in context.cookies())
        results.append({'account': index + 1, 'invalid_password_rejected': True, 'unknown_account_rejected': True,
                        'login': True, 'secure_cookie': True, 'logout': True,
                        'terminal_websocket': True, 'k9s_live_ui': True, 'preview_without_forward': 502,
                        'preview_with_forward': 200, 'terminal': 'Zellij 0.46.0',
                        'native_token_rejection': 401, 'native_cookie_path_isolated': True})
        context.close()
        subprocess.run(['bash', str(root / 'scripts/guest.sh'),
            f'sudo /usr/local/bin/k0s kubectl -n ai-inference-basics exec deployment/workspace-{participant} -c terminal -- zellij delete-session --force {session_name}'],
            check=True, stdout=subprocess.DEVNULL)
    browser.close()
(report / 'browser.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results))
