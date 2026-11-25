import assert from 'node:assert/strict';
import fs from 'node:fs';
import { stripVTControlCharacters } from 'node:util';
import { chromium } from 'playwright';
import { qualifyTelemetry } from './telemetry.mjs';
import { qualifyRequester } from './requester.mjs';

const base = process.env.LAB_ORIGIN;
const state = JSON.parse(fs.readFileSync(process.env.LAB_CREDENTIALS_FILE, 'utf8'));
assert(base?.startsWith('https://'));
const host = new URL(base).hostname;
const args = process.env.LAB_NODE_IP ? [`--host-resolver-rules=MAP ${host} ${process.env.LAB_NODE_IP}`] : [];
const browser = await chromium.launch({ headless: true, args });
let phase = 'startup';
try {
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  phase = 'anonymous-access';
  for (const path of ['/terminal/', '/code/', '/headlamp/', '/grafana/', '/requester/', '/requester/openapi/models.yaml']) {
    const response = await context.request.get(base + path, {
      maxRedirects: 0, headers: { 'X-Forwarded-Email': state.email },
    });
    assert.equal(response.status(), 302, 'Anonymous identity-header spoof bypassed authentication');
  }
  const page = await context.newPage();
  let output = '';
  let markerSeen = false;
  let terminalPreferences = {};
  page.on('websocket', socket => {
    if (new URL(socket.url()).pathname.startsWith('/terminal/')) {
      socket.on('framereceived', frame => {
        const text = Buffer.from(frame.payload).toString('utf8');
        if (text.startsWith('2{')) terminalPreferences = JSON.parse(text.slice(1));
        output = (output + text).slice(-131072);
        if (stripVTControlCharacters(output).includes('LAB_ADMIN_OK')) markerSeen = true;
      });
    }
  });
  phase = 'admin-login';
  await page.goto(`${base}/terminal/`, { waitUntil: 'domcontentloaded' });
  const login = page.locator('input[name="login"]');
  if (!(await login.isVisible())) {
    const emailLink = page.getByText('Log in with Email', { exact: true });
    if (await emailLink.isVisible()) await emailLink.click();
  }
  await login.waitFor({ timeout: 30000 });
  await login.fill(state.email);
  await page.locator('input[name="password"]').fill(state.password);
  await page.locator('button[type="submit"]').click();
  const grant = page.getByRole('button', { name: 'Grant Access', exact: true });
  if (await grant.isVisible()) await grant.click();
  await page.waitForURL(url => url.origin === base && url.pathname === '/terminal/', { timeout: 60000 });
  phase = 'terminal-command';
  await page.locator('.xterm-helper-textarea').waitFor({ state: 'attached', timeout: 30000 });
  for (let attempt = 0; attempt < 200 && output.length < 100; attempt++) await page.waitForTimeout(100);
  assert(output.length >= 100, 'Terminal did not produce its initial screen');
  assert(terminalPreferences.fontFamily?.includes('Geist Mono'), 'ttyd font configuration missing');
  assert.equal(terminalPreferences.theme?.background, '#2e3440', 'ttyd Nord theme missing');
  assert(await page.evaluate(async () => (await document.fonts.load('14px "Geist Mono"')).length > 0),
    'ttyd Geist webfont did not load');
  // A shared session may already run k9s or another user application.
  if (process.env.LAB_SKIP_TERMINAL_COMMAND !== '1') {
    await page.waitForTimeout(1000);
    await page.locator('.xterm-helper-textarea').focus();
    if (/welcome to Zellij|Welcome to Zellij|Keybinding Preset/.test(stripVTControlCharacters(output))) {
      await page.keyboard.press('Control+p');
      await page.keyboard.press('x');
      await page.waitForTimeout(500);
    }
    await page.keyboard.type("printf 'LAB_%s_OK\\n' ADMIN");
    await page.keyboard.press('Enter');
    for (let attempt = 0; attempt < 100 && !markerSeen; attempt++) await page.waitForTimeout(100);
    assert(markerSeen, 'Terminal command did not return its marker');
  }
  phase = 'editor';
  await page.goto(`${base}/code/`, { waitUntil: 'domcontentloaded' });
  await page.locator('.monaco-workbench').waitFor({ timeout: 90000 });
  await page.locator('.monaco-workbench.vs-dark').waitFor({ timeout: 30000 });
  assert(await page.evaluate(async () => (await document.fonts.load('14px "Geist Mono"')).length > 0),
    'Editor Geist webfont did not load');
  assert.equal(await page.locator('.monaco-workbench').evaluate(e =>
    getComputedStyle(e).getPropertyValue('--vscode-editor-background').trim().toLowerCase()), '#2e3440',
    'Editor Nord theme missing');
  assert.equal(new URL(page.url()).searchParams.get('folder'), '/workspace/ai-inference-basics',
    'Editor did not open the repository by default');
  assert.equal(await page.locator('input[type="password"]:visible').count(), 0);
  phase = 'headlamp';
  await page.goto(`${base}/headlamp/`, { waitUntil: 'domcontentloaded' });
  await page.getByText('Namespaces', { exact: true }).first().waitFor({ timeout: 60000 });
  phase = 'requester';
  await qualifyRequester(page, base, process.env.LAB_API_ORIGIN, state.api_key);
  phase = 'grafana-telemetry';
  await qualifyTelemetry(context.request, base, state);
  phase = 'api-cookie-rejection';
  const api = await context.request.post(`${process.env.LAB_API_ORIGIN}/v1/chat/completions`, {
    data: { model: 'qwen3-0-6b', messages: [{ role: 'user', content: 'hello' }], max_tokens: 1 },
  });
  assert.equal(api.status(), 401, 'Browser cookie unexpectedly authorized the model API');
  console.log(JSON.stringify({ adminLogin: true, terminalRendered: true, terminalCommand: markerSeen, editor: true,
    editorNord: true, geistWebfonts: true, terminalNord: true, repositoryDefault: true, headlamp: true,
    requester: true, anonymousSpoofDenied: true, apiCookieDenied: true }));
  await context.close();
} catch (error) {
  console.error(JSON.stringify({ phase, error: error.name,
    message: error.name === 'AssertionError' ? error.message : 'Browser interaction failed; inspect this phase privately.' }));
  process.exitCode = 1;
} finally {
  await browser.close();
}
