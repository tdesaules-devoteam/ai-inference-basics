import assert from 'node:assert/strict';

// Exercise Scalar's actual Send button, including the browser's CORS preflight.
export async function qualifyRequester(page, base, apiOrigin) {
  const loaded = page.waitForResponse(r => r.url() === `${apiOrigin}/openapi.json` && r.status() === 200);
  const session = page.waitForResponse(r => r.url() === `${base}/scalar/session-token`);
  await page.goto(`${base}/scalar/`, { waitUntil: 'domcontentloaded' });
  assert((await (await loaded).json()).paths['/score']);
  const credential = await session;
  assert.equal(credential.status(), 200);
  assert.match(credential.headers()['cache-control'] ?? '', /no-store/);
  await page.getByText('Generate embeddings', { exact: true }).first().click();
  const test = page.getByRole('button', { name: /Test Request.*\/v1\/embeddings/i });
  assert.equal(await test.evaluate(e => getComputedStyle(e).backgroundColor), 'rgb(136, 192, 208)');
  await test.click();
  assert(await page.evaluate(async () => (await document.fonts.load('14px "Geist Mono"')).length > 0));
  const send = page.getByRole('button', { name: /Send post request to .*\/v1\/embeddings/i });
  async function submit() {
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === `${apiOrigin}/v1/embeddings` && r.request().method() === 'POST'),
      send.click(),
    ]);
    return response;
  }
  const response = await submit();
  assert.equal(response.status(), 200, 'Scalar could not send an authenticated request');
  const payload = await response.json();
  assert.equal(payload.data.length, 2);
  assert.equal(payload.data[0].embedding.length, 1024);

  // Zen can request both cache headers when the developer tools disable caching.
  const chat = await page.evaluate(async origin => {
    const token = await (await fetch('/scalar/session-token', { cache: 'no-store' })).text();
    const r = await fetch(`${origin}/v1/chat/completions`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
        'Cache-Control': 'no-cache', Pragma: 'no-cache' },
      body: JSON.stringify({ model: 'qwen3-0-6b', messages: [{ role: 'user', content: 'Say OK.' }],
        max_tokens: 16, chat_template_kwargs: { enable_thinking: false } }),
    });
    return { status: r.status, choices: (await r.json()).choices?.length };
  }, apiOrigin);
  assert.deepEqual(chat, { status: 200, choices: 1 });
}
