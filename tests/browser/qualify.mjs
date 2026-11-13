import assert from 'node:assert/strict';
import fs from 'node:fs';
import { stripVTControlCharacters } from 'node:util';
import { chromium } from 'playwright';

// Credentials are supplied in a private temporary file, never as command arguments or logs.
const base = process.env.LAB_ORIGIN;
const state = JSON.parse(fs.readFileSync(process.env.LAB_CREDENTIALS_FILE, 'utf8'));
assert(base?.startsWith('https://'));
const host = new URL(base).hostname;
const args = process.env.LAB_NODE_IP ? [`--host-resolver-rules=MAP ${host} ${process.env.LAB_NODE_IP}`] : [];
const browser = await chromium.launch({ headless: true, args });
const results = [];
let phase = 'startup';
try {
  for (const participant of ['a', 'b']) {
    const other = participant === 'a' ? 'b' : 'a';
    const context = await browser.newContext({ ignoreHTTPSErrors: true });
    const page = await context.newPage();
    phase = `${participant}/login`;
    const marker = `LAB_${participant.toUpperCase()}_OK`;
    let markerSeen = false;
    let terminalOutput = '';
    page.on('websocket', socket => {
      if (new URL(socket.url()).pathname.startsWith(`/terminal-${participant}/`)) {
        socket.on('framereceived', frame => {
          terminalOutput = (terminalOutput + Buffer.from(frame.payload).toString('utf8')).slice(-65536);
          if (stripVTControlCharacters(terminalOutput).includes(marker)) markerSeen = true;
        });
      }
    });
    await page.goto(`${base}/terminal-${participant}/`, { waitUntil: 'domcontentloaded' });
    const login = page.locator('input[name="login"]');
    if (!(await login.isVisible())) {
      const emailLink = page.getByText('Log in with Email', { exact: true });
      if (await emailLink.isVisible()) await emailLink.click();
    }
    await login.waitFor({ timeout: 30000 });
    await login.fill(state.accounts[participant].email);
    await page.locator('input[name="password"]').fill(state.accounts[participant].password);
    await page.locator('button[type="submit"]').click();
    const grant = page.getByRole('button', { name: 'Grant Access', exact: true });
    if (await grant.isVisible()) await grant.click();
    await page.waitForURL(url => url.origin === base && url.pathname.startsWith(`/terminal-${participant}/`), { timeout: 60000 });
    phase = `${participant}/terminal`;
    await page.locator('.xterm-helper-textarea').waitFor({ state: 'attached', timeout: 30000 });
    for (let attempt = 0; attempt < 200 && terminalOutput.length < 100; attempt++) await page.waitForTimeout(100);
    assert(terminalOutput.length >= 100, 'Terminal did not produce its initial screen');
    await page.waitForTimeout(1000);
    await page.locator('.xterm-helper-textarea').focus();
    // Dismiss first-use tips or a keybinding dialog before addressing the shell.
    const screen = stripVTControlCharacters(terminalOutput);
    if (/welcome to Zellij|Welcome to Zellij|Keybinding Preset/.test(screen)) {
      await page.keyboard.press('Control+p');
      await page.keyboard.press('x');
      await page.waitForTimeout(500);
    }
    await page.keyboard.type(`printf 'LAB_%s_OK\\n' ${participant.toUpperCase()}`);
    await page.keyboard.press('Enter');
    for (let attempt = 0; attempt < 100 && !markerSeen; attempt++) await page.waitForTimeout(100);
    assert(markerSeen, `Participant ${participant}: terminal command did not return its marker`);
    phase = `${participant}/isolation`;
    for (const path of [`/terminal-${other}/`, `/code-${other}/`]) {
      const response = await context.request.get(base + path, { maxRedirects: 0 });
      assert.equal(response.status(), 403, `Cross-user access to ${path}`);
      const spoof = await context.request.get(base + path, {
        maxRedirects: 0, headers: { 'X-Forwarded-Email': state.accounts[other].email },
      });
      assert.equal(spoof.status(), 403, 'Identity header spoofing was not rejected');
    }
    phase = `${participant}/editor`;
    await page.goto(`${base}/code-${participant}/`, { waitUntil: 'domcontentloaded' });
    await page.locator('.monaco-workbench').waitFor({ timeout: 90000 });
    assert.equal(await page.locator('input[type="password"]:visible').count(), 0, 'Editor requested another password');
    phase = `${participant}/headlamp`;
    await page.goto(`${base}/headlamp/`, { waitUntil: 'domcontentloaded' });
    await page.getByText('Namespaces', { exact: true }).first().waitFor({ timeout: 60000 });
    const apiWithoutKey = await context.request.post(`${base}/v1/chat/completions`, {
      data: { model: 'ai-inference-basics-chat', messages: [{ role: 'user', content: 'hello' }], max_tokens: 1 },
    });
    assert.equal(apiWithoutKey.status(), 401, 'Browser cookie unexpectedly authorized the model API');
    results.push({ participant, oidc: true, terminalCommand: true, editor: true, headlamp: true, crossUserDenied: true });
    await context.close();
  }
  console.log(JSON.stringify(results));
} catch (error) {
  // Playwright call logs can include fill values, cookies and OIDC codes.
  console.error(JSON.stringify({ phase, error: error.name, message: error.name === 'AssertionError' ? error.message : 'Browser interaction failed; inspect this phase privately.' }));
  process.exitCode = 1;
} finally {
  await browser.close();
}
