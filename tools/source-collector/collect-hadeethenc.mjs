/** Owner-run HadeethEnc collection only. Never imported by the API or run at build/startup. */
import { createHash } from 'node:crypto';
import { appendFile, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const HOST = 'hadeethenc.com';
const BASE = `https://${HOST}/api/v1/`;
const ENDPOINTS = {
  roots: { path: 'categories/roots/', params: ['language'] },
  categories: { path: 'categories/list/', params: ['language'] },
  lists: { path: 'hadeeths/list/', params: ['language', 'category_id', 'page', 'per_page'] },
  one: { path: 'hadeeths/one/', params: ['language', 'id'] },
};
const WORKERS = 4;
const SPACING_MS = 250;
const RETRIES = 1;
const RETRY_DELAY_MS = 2000;
const TIMEOUT_MS = 30000;
const MAX_BODY_BYTES = 2 * 1024 * 1024;
const PER_PAGE = 20;
const MAX_LIST_PAGES = 5000;
const MAX_CATEGORIES = 5000;
const OUTPUT_FILE = 'hadeethenc.jsonl';
const NUMBER = /^[1-9][0-9]{0,7}$/;
const sha = value => createHash('sha256').update(value).digest('hex');
const numeric = (a, b) => Number(a) - Number(b);
const str = value => (typeof value === 'string' ? value : '');
const coded = (reason, retryable) => Object.assign(new Error(reason), { reason, retryable });
const REPORTED = /^(network_error|redirect_refused|not_json|bad_json|page_too_large|unexpected_shape|id_mismatch|missing_hadeeth|page_limit|page_short|page_repeated|pagination_mismatch|too_many_categories|non_string_(title|hadeeth|attribution|grade|reference|explanation)|http_\d{3})$/;
const reasonOf = error => (REPORTED.test(error.reason ?? '') ? error.reason : 'fetch_or_parse_failure');

/** Only allowlisted endpoints, Arabic language and numeric parameters reach the network. */
export function apiUrl(name, params = {}) {
  const endpoint = ENDPOINTS[name];
  if (!endpoint) throw new Error('unknown_endpoint');
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (!endpoint.params.includes(key)) throw new Error('unknown_param');
    const valid = key === 'language' ? value === 'ar' : NUMBER.test(String(value));
    if (!valid) throw new Error('invalid_param');
    search.set(key, String(value));
  }
  return `${BASE}${endpoint.path}?${search}`;
}

/** One request start at least `spacing` ms after the previous one, shared by all workers. */
export class Limiter {
  constructor({ spacing = SPACING_MS, now = Date.now, sleep = ms =>
    new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
    Object.assign(this, { spacing, now, sleep, next: 0 });
  }
  async slot() {
    // Reserve synchronously before waiting, so concurrent callers queue in order.
    const start = Math.max(this.now(), this.next);
    this.next = start + this.spacing;
    const wait = start - this.now();
    if (wait > 0) await this.sleep(wait);
  }
}

async function readBounded(response) {
  const chunks = []; let length = 0;
  for await (const chunk of response.body) {
    length += chunk.length;
    if (length > MAX_BODY_BYTES) throw coded('page_too_large', false);
    chunks.push(chunk);
  }
  return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
}

export class Api {
  constructor({ fetchFn = fetch, limiter = new Limiter(), retries = RETRIES,
    retryDelay = RETRY_DELAY_MS, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
    Object.assign(this, { fetchFn, limiter, retries, retryDelay, sleep });
  }
  async get(name, params) {
    const url = apiUrl(name, params);
    for (let attempt = 0; ; attempt += 1) {
      await this.limiter.slot();
      try { return await this.once(url); }
      catch (error) {
        if (!error.retryable || attempt >= this.retries) throw error;
        await this.sleep(this.retryDelay);
      }
    }
  }
  async once(url) {
    let response;
    try {
      response = await this.fetchFn(url, { redirect: 'manual', signal: AbortSignal.timeout(TIMEOUT_MS),
        headers: { Accept: 'application/json', 'User-Agent': 'TabayyanOwnerCollector/1.0' } });
    } catch { throw coded('network_error', true); }
    if (response.status >= 300 && response.status < 400) throw coded('redirect_refused', false);
    if (!response.ok) throw coded(`http_${response.status}`, response.status === 429 || response.status >= 500);
    if (!/application\/json/i.test(response.headers.get('content-type') ?? '')) throw coded('not_json', false);
    const body = await readBounded(response);
    try { return JSON.parse(body); } catch { throw coded('bad_json', false); }
  }
}

// Accepts a bare list or a {data: [...]} wrapper; anything else fails closed.
const rows = payload => {
  const list = Array.isArray(payload) ? payload : payload?.data;
  if (!Array.isArray(list)) throw coded('unexpected_shape', false);
  return list;
};
const idOf = row => {
  const value = typeof row?.id === 'number' ? String(row.id) : row?.id;
  return typeof value === 'string' && NUMBER.test(value) ? value : null;
};

async function listCategory(api, category, items) {
  const seenPages = new Set();
  const listedIds = new Set();
  let expectedTotal = null; let expectedLast = null;
  for (let page = 1; page <= MAX_LIST_PAGES; page += 1) {
    const payload = await api.get('lists', { language: 'ar', category_id: category,
      page: String(page), per_page: String(PER_PAGE) });
    const list = rows(payload);
    const ids = [];
    for (const row of list) {
      const id = idOf(row);
      if (!id) throw coded('unexpected_shape', false);
      ids.push(id);
      if (!items[id]) items[id] = { title: str(row.title), categories: [] };
      if (!items[id].categories.includes(category)) items[id].categories.push(category);
    }
    const key = ids.join(',');
    if (ids.length && (seenPages.has(key) || ids.some(id => listedIds.has(id)) ||
      new Set(ids).size !== ids.length)) throw coded('page_repeated', false);
    seenPages.add(key);
    ids.forEach(id => listedIds.add(id));
    const total = payload?.total ?? payload?.meta?.total;
    const last = payload?.last_page ?? payload?.meta?.last_page;
    for (const value of [total, last]) {
      if (value !== undefined && (!Number.isSafeInteger(value) || value < 0)) {
        throw coded('pagination_mismatch', false);
      }
    }
    if (total !== undefined) {
      if (expectedTotal !== null && expectedTotal !== total) throw coded('pagination_mismatch', false);
      expectedTotal = total;
    }
    if (last !== undefined) {
      if (last < 1 || (expectedLast !== null && expectedLast !== last)) throw coded('pagination_mismatch', false);
      expectedLast = last;
    }
    if (expectedTotal !== null && listedIds.size > expectedTotal) throw coded('pagination_mismatch', false);
    const atLast = expectedLast !== null && page === expectedLast;
    const atTotal = expectedTotal !== null && listedIds.size === expectedTotal;
    if (atLast || atTotal) {
      if ((expectedTotal !== null && !atTotal) || (expectedLast !== null && !atLast)) {
        throw coded('pagination_mismatch', false);
      }
      return;
    }
    if (list.length < PER_PAGE) {
      // A nonempty short page is not proof of exhaustion; servers may cap page size.
      if (list.length === 0 && expectedTotal === null && expectedLast === null) return;
      throw coded('page_short', false);
    }
  }
  throw coded('page_limit', false);
}

/**
 * Categories from roots and the flat list, then every item page per category.
 * Titles from listings only select IDs for the item call; they are not evidence.
 */
export async function discover(api) {
  const roots = rows(await api.get('roots', { language: 'ar' })).map(idOf);
  const listed = rows(await api.get('categories', { language: 'ar' }));
  if (listed.length > MAX_CATEGORIES) throw coded('too_many_categories', false);
  const categories = [...new Set([...roots, ...listed.map(idOf)].filter(Boolean))].sort(numeric);
  const items = {}; const categoryFailures = [];
  for (const category of categories) {
    try { await listCategory(api, category, items); }
    catch (error) { categoryFailures.push({ category, reason: reasonOf(error) }); }
  }
  return { categories, items, category_failures: categoryFailures };
}

/** One item call. Fields are copied as returned; nothing is trimmed, translated or inferred. */
export async function fetchItem(api, id, entry) {
  const payload = await api.get('one', { language: 'ar', id });
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw coded('unexpected_shape', false);
  if (String(payload.id) !== id) throw coded('id_mismatch', false);
  for (const field of ['title', 'hadeeth', 'attribution', 'grade', 'reference', 'explanation']) {
    if (payload[field] !== undefined && typeof payload[field] !== 'string') {
      throw coded(`non_string_${field}`, false);
    }
  }
  if (!str(payload.hadeeth).trim()) throw coded('missing_hadeeth', false);
  return {
    id,
    title: str(payload.title),
    hadeeth: payload.hadeeth,
    attribution: str(payload.attribution),
    grade: str(payload.grade),
    reference: str(payload.reference),
    explanation: str(payload.explanation),
    categories: [...entry.categories].sort(numeric),
    url: `https://${HOST}/ar/browse/hadith/${id}`,
  };
}

async function runPool(ids, work) {
  let next = 0;
  await Promise.all(Array.from({ length: WORKERS }, async () => {
    while (next < ids.length) {
      const id = ids[next];
      next += 1;
      await work(id);
    }
  }));
}

async function completedIds(jsonlPath) {
  let text;
  try { text = await readFile(jsonlPath, 'utf8'); }
  catch (error) { if (error.code === 'ENOENT') return new Set(); throw error; }
  const lines = text.split('\n');
  const records = [];
  for (let index = 0; index < lines.length; index += 1) {
    if (!lines[index]) continue;
    let record;
    try { record = JSON.parse(lines[index]); }
    catch {
      // Only an unterminated final append is recoverable; earlier corruption is refused.
      if (index !== lines.length - 1 || text.endsWith('\n')) throw new Error('resume_invalid_jsonl');
      break;
    }
    if (!record || typeof record.id !== 'string' || !NUMBER.test(record.id)) throw new Error('resume_invalid_record');
    records.push(record);
  }
  // Normalize the tail before appending, retaining every valid record and its field values.
  const temporary = `${jsonlPath}.resume.tmp`;
  await writeFile(temporary, records.map(record => JSON.stringify(record) + '\n').join(''));
  await rename(temporary, jsonlPath);
  return new Set(records.map(record => record.id));
}

async function finalizeOutput(jsonlPath) {
  const lines = (await readFile(jsonlPath, 'utf8')).split('\n').filter(Boolean);
  const byId = new Map();
  for (const line of lines) {
    const record = JSON.parse(line);
    if (!byId.has(record.id)) byId.set(record.id, record);
  }
  const records = [...byId.values()].sort((a, b) => numeric(a.id, b.id));
  const value = records.map(record => JSON.stringify(record) + '\n').join('');
  const temporary = `${jsonlPath}.tmp`;
  await writeFile(temporary, value);
  await rename(temporary, jsonlPath);
  const bytes = Buffer.from(value, 'utf8');
  const emptyFields = {};
  for (const key of ['title', 'attribution', 'grade', 'reference', 'explanation']) {
    emptyFields[key] = records.filter(record => !record[key]).length;
  }
  return { count: records.length, bytes: bytes.length, sha256: sha(bytes), emptyFields };
}

const writeManifest = (output, data) => writeFile(path.join(output, 'manifest.json'),
  JSON.stringify({ format_version: 1, ...data }, null, 2));

/**
 * New directory, or --resume of an in_progress/partial run. Discovery is stored in the
 * manifest so a resume does not repeat listing calls; the JSONL file is the source of
 * completed IDs. Existing output is never overwritten.
 */
export async function collectHadeethEnc({ output, api = new Api(), resume = false }) {
  const manifestPath = path.join(output, 'manifest.json');
  const jsonlPath = path.join(output, OUTPUT_FILE);
  let previous = null;
  if (resume) {
    previous = JSON.parse(await readFile(manifestPath, 'utf8'));
    if (previous.status === 'complete') throw new Error('already_complete');
  } else {
    await mkdir(path.dirname(output), { recursive: true });
    await mkdir(output);
    await writeFile(jsonlPath, '', { flag: 'wx' });
  }
  let discovery = previous?.discovery ?? null;
  if (!discovery) {
    discovery = await discover(api);
    await writeManifest(output, { status: 'in_progress', discovery });
  }
  const report = discovery.category_failures.map(failure => ({ kind: 'category', ...failure }));
  const done = await completedIds(jsonlPath);
  const pending = Object.keys(discovery.items).filter(id => !done.has(id));
  await runPool(pending, async id => {
    try {
      const record = await fetchItem(api, id, discovery.items[id]);
      await appendFile(jsonlPath, JSON.stringify(record) + '\n');
    } catch (error) {
      report.push({ kind: 'item', id, reason: reasonOf(error) });
    }
  });
  const stats = await finalizeOutput(jsonlPath);
  const complete = report.length === 0;
  const manifest = { source: 'HadeethEnc.com', source_host: HOST, language: 'ar',
    attribution: 'HadeethEnc.com', file: OUTPUT_FILE, status: complete ? 'complete' : 'partial',
    complete, generated_at: new Date().toISOString(),
    discovered_items: Object.keys(discovery.items).length, categories: discovery.categories.length,
    failures: report.length, ...stats,
    scope: 'owner-private; text copied verbatim; attribute HadeethEnc.com; no modification' };
  // Keep discovery only while the run is unfinished, so a resume can continue from it.
  if (!complete) manifest.discovery = discovery;
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await writeManifest(output, manifest);
  return manifest;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help')) {
    console.log('node collect-hadeethenc.mjs --owner-run --output NEW_PRIVATE_DIRECTORY [--resume]');
    return;
  }
  if (!args.includes('--owner-run')) throw new Error('Requires explicit --owner-run');
  const value = flag => args[args.indexOf(flag) + 1];
  if (!args.includes('--output') || !value('--output')) throw new Error('Requires --output');
  const result = await collectHadeethEnc({ output: path.resolve(value('--output')),
    resume: args.includes('--resume') });
  console.log(JSON.stringify({ complete: result.complete, count: result.count,
    failures: result.failures, sha256: result.sha256 }, null, 2));
  if (!result.complete) process.exitCode = 2;
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
