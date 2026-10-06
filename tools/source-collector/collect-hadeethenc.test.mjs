import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
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
      return json({ data: items.slice((page - 1) * 20, page * 20) });
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
