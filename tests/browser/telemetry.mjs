import assert from 'node:assert/strict';
import { randomBytes, randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';

// Query through Grafana using the existing Dex session, including datasource proxy access.
export async function qualifyTelemetry(http, base, state) {
  const get = async (path, params) => {
    const r = await http.get(`${base}/grafana/api/${path}`, { params, timeout: 15000 });
    assert.equal(r.status(), 200, `${path}: ${r.status()}`);
    return r.json();
  };
  const proxy = (uid, path, params) => get(`datasources/proxy/uid/${uid}/${path}`, params);
  assert.equal((await get('user')).email, state.email);
  for (const uid of ['mimir', 'loki', 'tempo'])
    assert.equal((await get(`datasources/uid/${uid}`)).uid, uid);
  const trace = randomBytes(16).toString('hex'), marker = randomUUID();
  const model = 'qwen3-0-6b';
  const metric = async () => {
    const data = await proxy('mimir', 'api/v1/query', {
      query: `sum({__name__=~"vllm[:_]generation_tokens_total",model="${model}"})`,
    });
    assert.equal(data.status, 'success');
    return Number(data.data.result[0]?.value[1] ?? 0);
  };
  const before = await metric();
  const start = Date.now() - 30000;
  const result = await http.post(`${base}/v1/chat/completions`, {
    headers: { Authorization: `Bearer ${state.api_key}`, 'X-Request-ID': marker,
      traceparent: `00-${trace}-${randomBytes(8).toString('hex')}-01` },
    data: { model, messages: [{ role: 'user', content: 'Reply OK.' }], max_tokens: 8 },
    timeout: 180000,
  });
  assert.equal(result.status(), 200);
  const { usage } = await result.json();
  assert(usage.completion_tokens > 0);
  let metrics = false, logs = false, traces = false, loggedRequestId;
  for (const end = Date.now() + 150000; Date.now() < end;) {
    metrics ||= await metric() >= before + usage.completion_tokens;
    const loki = await proxy('loki', 'loki/api/v1/query_range', {
      query: `{k8s_namespace_name="gateway"} |= "${trace}"`, start: `${start}000000`,
      end: `${Date.now()}000000`, limit: '50',
    });
    logs ||= loki.data.result.some(stream => stream.values.some(([, line]) => {
      try {
        const entry = JSON.parse(line);
        if (entry.traceparent?.split('-')[1] !== trace || entry.total_tokens !== usage.total_tokens) return false;
        // Envoy may encode its sampling decision into UUID request IDs.
        loggedRequestId = entry.request_id;
        return Boolean(loggedRequestId);
      } catch { return false; }
    }));
    const tempo = await proxy('tempo', 'api/search', {
      q: `{ resource.service.name = "lab-gateway" && span.request_id = "${loggedRequestId ?? marker}" }`,
    });
    traces ||= tempo.traces?.some(entry => entry.traceID.padStart(32, '0') === trace);
    if (metrics && logs && traces) {
      console.log(JSON.stringify({ grafana: true, metrics, logs, traces }));
      return;
    }
    await delay(3000);
  }
  assert.fail(`Missing correlated telemetry: metrics=${metrics}, logs=${logs}, traces=${traces}`);
}
