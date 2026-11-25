import assert from 'node:assert/strict';

// Exercise Scalar's actual Send button, including the browser's CORS preflight.
export async function qualifyRequester(page, base, apiOrigin, apiKey) {
  await page.goto(`${base}/requester/`, { waitUntil: 'domcontentloaded' });
  await page.getByText('Generate embeddings', { exact: true }).first().click();
  await page.getByRole('button', { name: /Test Request.*\/v1\/embeddings/i }).click();
  const send = page.getByRole('button', { name: /Send post request to .*\/v1\/embeddings/i });
  async function submit() {
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === `${apiOrigin}/v1/embeddings` && r.request().method() === 'POST'),
      send.click(),
    ]);
    return response;
  }
  assert.equal((await submit()).status(), 401, 'Dex login must not grant model access');
  await page.getByPlaceholder('Token', { exact: true }).last().fill(apiKey);
  const response = await submit();
  assert.equal(response.status(), 200, 'Scalar could not send an authenticated request');
  const payload = await response.json();
  assert.equal(payload.data.length, 2);
  assert.equal(payload.data[0].embedding.length, 1024);
}
