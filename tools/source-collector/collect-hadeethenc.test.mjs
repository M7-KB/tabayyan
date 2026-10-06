import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { apiUrl, Api, collectHadeethEnc, Limiter } from './collect-hadeethenc.mjs';

// Synthetic fake API: plumbing only; the Arabic strings are placeholders, not source text.
const range = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => from + i);
const CATEGORY_ITEMS = { 1: range(11, 31), 2: range(30, 33) }; // 21 + 4 items, one overlap
const json = (body, status = 200) => new Response(JSON.stringify(body),
  { status, headers: { 'Content-Type': 'application/json' } });
const oneRecord = id => ({ id, title: `عنوان ${id}`, hadeeth: `نص عينة ${id}  `,
  attribution: 'مصدر عينة', grade: 'درجة عينة', reference: 'مرجع عينة', explanation: 'شرح عينة' });

function fakeFetch(overrides = {}) {
  const calls = [];
  const fetchFn = async url => {
    calls.push(url);
    const parsed = new URL(url);
    const name = parsed.pathname.replace('/api/v1/', '');
    const params = Object.fromEntries(parsed.searchParams);
    if (overrides[name]) {
      const response = await overrides[name](params);
      if (response) return response;
    }
    if (name === 'categories/roots/') return json({ data: [{ id: 1, title: 'جذر' }] });
    if (name === 'categories/list/') return json([{ id: 1, title: 'أ' }, { id: 2, title: 'ب' }]);
    if (name === 'hadeeths/list/') {
      const items = CATEGORY_ITEMS[params.category_id].map(id => ({ id, title: `عنوان ${id}` }));
      const page = Number(params.page);
      return json({ data: items.slice((page - 1) * 20, page * 20),
        total: items.length, last_page: Math.ceil(items.length / 20) });
    }
    if (name === 'hadeeths/one/') return json(oneRecord(Number(params.id)));
    return new Response('', { status: 404 });
  };
  return { fetchFn, calls };
}
const fastApi = fetchFn => new Api({ fetchFn, retryDelay: 0, sleep: async () => {},
  limiter: new Limiter({ spacing: 0, now: () => 0, sleep: async () => {} }) });
const countCalls = (calls, pattern) => calls.filter(url => pattern.test(url)).length;

test('API URLs carry only allowlisted endpoints, Arabic language and numeric parameters', () => {
  assert.equal(apiUrl('one', { language: 'ar', id: '12' }),
    'https://hadeethenc.com/api/v1/hadeeths/one/?language=ar&id=12');
  for (const [name, params] of [['one', { language: 'en', id: '1' }], ['one', { language: 'ar', id: '0' }],
    ['one', { language: 'ar', id: '1; drop' }], ['one', { language: 'ar', id: '1', page: '1' }],
    ['search', {}]]) {
    assert.throws(() => apiUrl(name, params));
  }
});

test('full run: flat categories, paged item lists, verbatim copy, sorted sha256 manifest', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-hadeethenc-'));
  try {
    const output = path.join(directory, 'out');
    const { fetchFn } = fakeFetch();
    const manifest = await collectHadeethEnc({ output, api: fastApi(fetchFn) });
    assert.equal(manifest.complete, true);
    assert.equal(manifest.status, 'complete');
    assert.equal(manifest.count, 23);
    assert.equal(manifest.discovery, undefined);
    const bytes = await readFile(path.join(output, 'hadeethenc.jsonl'));
    assert.equal(createHash('sha256').update(bytes).digest('hex'), manifest.sha256);
    assert.equal(bytes.length, manifest.bytes);
    const records = bytes.toString('utf8').trim().split('\n').map(line => JSON.parse(line));
    assert.deepEqual(records.map(r => Number(r.id)), range(11, 33));
    const first = records[0];
    assert.equal(first.hadeeth, 'نص عينة 11  ');
    assert.equal(first.url, 'https://hadeethenc.com/ar/browse/hadith/11');
    assert.deepEqual(first.categories, ['1']);
    assert.deepEqual(records.find(r => r.id === '30').categories, ['1', '2']);
    assert.deepEqual(Object.keys(first).sort(),
      ['attribution', 'categories', 'explanation', 'grade', 'hadeeth', 'id', 'reference', 'title', 'url']);
    assert.equal(JSON.parse(await readFile(path.join(output, 'manifest.json'), 'utf8')).count, 23);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('one retry for a 5xx or network error; 4xx is reported without retry', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-hadeethenc-'));
  try {
    const base = fakeFetch();
    const attempts = {};
    const fetchFn = async (url, opts) => {
      const id = new URL(url).searchParams.get('id');
      if (id) attempts[id] = (attempts[id] ?? 0) + 1;
      if (id === '11' && attempts[id] === 1) return new Response('', { status: 500 });
      if (id === '14' && attempts[id] === 1) throw new TypeError('network down');
      if (id === '12') return new Response('', { status: 404 });
      return base.fetchFn(url, opts);
    };
    const manifest = await collectHadeethEnc({ output: path.join(directory, 'out'), api: fastApi(fetchFn) });
    assert.equal(attempts['11'], 2); // 5xx retried once and collected
    assert.equal(attempts['14'], 2); // network error retried once and collected
    assert.equal(attempts['12'], 1); // 4xx never retried
    assert.equal(manifest.complete, false);
    assert.equal(manifest.count, 22);
    const report = JSON.parse(await readFile(path.join(directory, 'out/report.json'), 'utf8'));
    assert.deepEqual(report.map(row => [row.id, row.reason]), [['12', 'http_404']]);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('a missing hadeeth text is reported and never written', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-hadeethenc-'));
  try {
    const { fetchFn } = fakeFetch({ 'hadeeths/one/': params => params.id === '13'
      ? json({ ...oneRecord(13), hadeeth: '   ' }) : null });
    const manifest = await collectHadeethEnc({ output: path.join(directory, 'out'), api: fastApi(fetchFn) });
    assert.equal(manifest.complete, false);
    assert.equal(manifest.count, 22);
    const written = await readFile(path.join(directory, 'out/hadeethenc.jsonl'), 'utf8');
    assert.ok(!written.includes('"id":"13"'));
    const report = JSON.parse(await readFile(path.join(directory, 'out/report.json'), 'utf8'));
    assert.equal(report[0].reason, 'missing_hadeeth');
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('resume continues from the manifest without repeating listing calls or duplicating IDs', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-hadeethenc-'));
  try {
    const output = path.join(directory, 'out');
    const broken = fakeFetch({ 'hadeeths/one/': params => params.id === '20' ? new Response('', { status: 404 }) : null });
    const partial = await collectHadeethEnc({ output, api: fastApi(broken.fetchFn) });
    assert.equal(partial.status, 'partial');
    assert.equal(partial.count, 22);
    assert.ok(partial.discovery, 'discovery is kept while the run is unfinished');

    const healthy = fakeFetch();
    const resumed = await collectHadeethEnc({ output, api: fastApi(healthy.fetchFn), resume: true });
    assert.equal(resumed.complete, true);
    assert.equal(resumed.count, 23);
    assert.equal(countCalls(healthy.calls, /hadeeths\/list|categories\/list|categories\/roots/), 0);
    assert.equal(countCalls(healthy.calls, /hadeeths\/one/), 1);
    const ids = (await readFile(path.join(output, 'hadeethenc.jsonl'), 'utf8'))
      .trim().split('\n').map(line => JSON.parse(line).id);
    assert.equal(new Set(ids).size, ids.length);
    await assert.rejects(collectHadeethEnc({ output, api: fastApi(healthy.fetchFn), resume: true }),
      /already_complete/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('no overwrite of an existing output directory; unexpected category shape fails startup', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-hadeethenc-'));
  try {
    const output = path.join(directory, 'out');
    const { fetchFn } = fakeFetch();
    await collectHadeethEnc({ output, api: fastApi(fetchFn) });
    await assert.rejects(collectHadeethEnc({ output, api: fastApi(fetchFn) }), /EEXIST/);
    const broken = fakeFetch({ 'categories/roots/': () => json({ error: 'x' }) });
    await assert.rejects(collectHadeethEnc({ output: path.join(directory, 'bad'),
      api: fastApi(broken.fetchFn) }), /unexpected_shape/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('the shared limiter reserves request starts at least 250 ms apart across workers', async () => {
  const sleeps = [];
  const limiter = new Limiter({ now: () => 0, sleep: async ms => { sleeps.push(ms); } });
  await Promise.all([1, 2, 3, 4].map(() => limiter.slot()));
  assert.deepEqual(sleeps, [250, 500, 750]);
});

async function withOutput(work) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-hadeethenc-'));
  try { await work(path.join(directory, 'out')); }
  finally { await rm(directory, { recursive: true, force: true }); }
}

for (const scenario of ['short', 'repeated', 'last_count_mismatch', 'unknown_short']) {
  test(`incomplete pagination is reported instead of complete: ${scenario}`, async () => {
    await withOutput(async output => {
      const broken = fakeFetch({ 'hadeeths/list/': params => {
        if (params.category_id !== '1') return null;
        const page = Number(params.page);
        const ids = scenario === 'short' || scenario === 'unknown_short' ? range(1, 15)
          : scenario === 'last_count_mismatch' && page === 2 ? range(21, 35) : range(1, 20);
        const data = ids.map(id => ({ id, title: `Sample ${id}` }));
        return json(scenario === 'unknown_short' ? data : { data, total: 40, last_page: 2 });
      } });
      const manifest = await collectHadeethEnc({ output, api: fastApi(broken.fetchFn) });
      assert.equal(manifest.complete, false);
      assert.equal(manifest.status, 'partial');
      const report = JSON.parse(await readFile(path.join(output, 'report.json'), 'utf8'));
      assert.deepEqual(report.filter(row => row.kind === 'category'), [{ kind: 'category', category: '1',
        reason: scenario === 'repeated' ? 'page_repeated'
          : scenario === 'last_count_mismatch' ? 'pagination_mismatch' : 'page_short' }]);
    });
  });
}

test('resume discards an interrupted final append and fetches its ID again', async () => {
  await withOutput(async output => {
    const broken = fakeFetch({ 'hadeeths/one/': params => params.id === '20'
      ? new Response('', { status: 404 }) : null });
    await collectHadeethEnc({ output, api: fastApi(broken.fetchFn) });
    const jsonlPath = path.join(output, 'hadeethenc.jsonl');
    const text = await readFile(jsonlPath, 'utf8');
    const lines = text.trimEnd().split('\n');
    const truncatedId = JSON.parse(lines.at(-1)).id;
    lines[lines.length - 1] = lines.at(-1).slice(0, -10);
    await writeFile(jsonlPath, lines.join('\n'));
    const healthy = fakeFetch();
    const resumed = await collectHadeethEnc({ output, api: fastApi(healthy.fetchFn), resume: true });
    assert.equal(resumed.complete, true);
    assert.equal(resumed.count, 23);
    assert.equal(countCalls(healthy.calls, /hadeeths\/list|categories\/list|categories\/roots/), 0);
    assert.equal(countCalls(healthy.calls, /hadeeths\/one/), 2);
    assert.ok(healthy.calls.some(url => new URL(url).searchParams.get('id') === truncatedId));
    const bytes = await readFile(jsonlPath);
    const records = bytes.toString('utf8').trimEnd().split('\n').map(line => JSON.parse(line));
    assert.equal(new Set(records.map(row => row.id)).size, 23);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), resumed.sha256);
  });
});

test('resume refuses malformed interior lines without changing the file', async () => {
  await withOutput(async output => {
    const broken = fakeFetch({ 'hadeeths/one/': params => params.id === '20'
      ? new Response('', { status: 404 }) : null });
    await collectHadeethEnc({ output, api: fastApi(broken.fetchFn) });
    const jsonlPath = path.join(output, 'hadeethenc.jsonl');
    const lines = (await readFile(jsonlPath, 'utf8')).split('\n');
    lines[1] = '{"id":';
    const corrupt = lines.join('\n');
    await writeFile(jsonlPath, corrupt);
    const healthy = fakeFetch();
    await assert.rejects(collectHadeethEnc({ output, api: fastApi(healthy.fetchFn), resume: true }),
      /resume_invalid_jsonl/);
    assert.equal(await readFile(jsonlPath, 'utf8'), corrupt);
    assert.equal(healthy.calls.length, 0);
  });
});

for (const field of ['attribution', 'grade', 'reference', 'explanation']) {
  test(`null optional ${field} is empty and counted without discarding the item`, async () => {
    await withOutput(async output => {
      const source = oneRecord(13);
      const { fetchFn } = fakeFetch({ 'hadeeths/one/': params => params.id === '13'
        ? json({ ...source, [field]: null }) : null });
      const manifest = await collectHadeethEnc({ output, api: fastApi(fetchFn) });
      assert.equal(manifest.complete, true);
      assert.equal(manifest.count, 23);
      assert.equal(manifest.emptyFields[field], 1);
      const records = (await readFile(path.join(output, 'hadeethenc.jsonl'), 'utf8'))
        .trimEnd().split('\n').map(line => JSON.parse(line));
      const record = records.find(row => row.id === '13');
      assert.ok(record);
      assert.equal(record[field], '');
      for (const key of ['title', 'hadeeth', 'attribution', 'grade', 'reference', 'explanation']) {
        if (key !== field) assert.equal(record[key], source[key]);
      }
      assert.deepEqual(JSON.parse(await readFile(path.join(output, 'report.json'), 'utf8')), []);
    });
  });
}

for (const field of ['title', 'hadeeth', 'attribution', 'grade', 'reference', 'explanation']) {
  test(`a non-string ${field} is reported by name and the item is refused`, async () => {
    await withOutput(async output => {
      const broken = fakeFetch({ 'hadeeths/one/': params => params.id === '13'
        ? json({ ...oneRecord(13), [field]: 42 }) : null });
      const manifest = await collectHadeethEnc({ output, api: fastApi(broken.fetchFn) });
      assert.equal(manifest.complete, false);
      assert.equal(manifest.count, 22);
      const report = JSON.parse(await readFile(path.join(output, 'report.json'), 'utf8'));
      assert.deepEqual(report, [{ kind: 'item', id: '13', reason: `non_string_${field}` }]);
      assert.ok(!(await readFile(path.join(output, 'hadeethenc.jsonl'), 'utf8')).includes('"id":"13"'));
    });
  });
}

test('a redirect is refused with its own reason and is never followed or retried', async () => {
  const calls = [];
  const api = fastApi(async (url, options) => {
    calls.push(url);
    assert.equal(options.redirect, 'manual');
    return new Response('', { status: 302, headers: { Location: 'https://example.invalid/' } });
  });
  await assert.rejects(api.get('one', { language: 'ar', id: '12' }),
    error => error.reason === 'redirect_refused' && error.retryable === false);
  assert.equal(calls.length, 1);
});
