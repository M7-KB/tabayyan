/** Owner-run collection only. Never imported by the API or run at build/startup. */
import { parse } from 'parse5';
import { createHash } from 'node:crypto';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const AUTHORITY = 'd3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f';
// Home pages are seeds for discovery only; they are never queued from links.
const HOME_SEEDS = ['https://bayenat.net/', 'https://islamic-content.com/dictionary'];
const HOME_PATHS = {
  'bayenat.net': [/^\/(?:ar\/?)?$/],
  'islamic-content.com': [/^\/dictionary\/?$/],
};
// Crawl targets: category listings (followed for discovery) and record pages.
const CRAWL_PATHS = {
  'bayenat.net': [/^\/ar\/categories\/[^/]+\/?$/, /^\/ar\/category\/[^/]+\/[^/]+\/?$/],
  'islamic-content.com': [/^\/dictionary\/word\/[^/]+\/?$/],
};
const RECORD_PATHS = {
  'bayenat.net': [/^\/ar\/category\/[^/]+\/[^/]+\/?$/],
  'islamic-content.com': [/^\/dictionary\/word\/[^/]+\/?$/],
};
const MAX_REDIRECTS = 3;
const REDIRECT_STATUS = new Set([301, 302, 303, 307, 308]);
const BAYENAT_LABELS = ['نص السؤال', 'الجواب التفصيلي', 'الخلاصة', 'مضمون الشبهة', 'المراجع', 'كلمات دلالية'];
// Sub-headings inside the detailed answer: kept as text, never a stop point for it.
const NESTED_LABELS = ['الخلاصة', 'مضمون الشبهة', 'المراجع'];
const TRANSLATIONS_LABEL = 'ترجمة هذا المصطلح متوفرة باللغات التالية';
const GLOSSARY_LABELS = ['المعنى الاصطلاحي', 'الشرح المختصر', 'التعريف اللغوي المختصر', 'التعريف', TRANSLATIONS_LABEL];
const LISTING_REASONS = new Set(['home_listing', 'category_listing']);
const sha = value => createHash('sha256').update(value).digest('hex');
const attr = (node, name) => node.attrs?.find(a => a.name === name)?.value ?? '';
const children = node => node.childNodes ?? [];
const walk = node => [node, ...children(node).flatMap(walk)];
const isElement = node => typeof node.tagName === 'string';
const isHeading = node => /^h[1-6]$/.test(node.tagName ?? '');
const text = node => {
  if (['script', 'style', 'nav', 'footer'].includes(node.tagName)) return '';
  if (node.nodeName === '#text') return node.value;
  if (node.tagName === 'br') return '\n';
  const value = children(node).map(text).join('');
  return ['p', 'li', 'div', 'section', 'tr'].includes(node.tagName) ? `${value}\n` : value;
};
const clean = value => value.replace(/\r/g, '').replace(/[\t ]+/g, ' ')
  .replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim();
const label = value => clean(value).replace(/[：:]$/, '').trim();
// Letter-majority rule: a field needs more Arabic letters than Latin letters.
const arabic = value => (value.match(/[ء-ي]/g) ?? []).length >
  (value.match(/[A-Za-z]/g) ?? []).length;
const matches = (rules, pathname) => rules.some(rule => rule.test(pathname));
// Own-property lookup: a hostname such as "constructor" must not reach inherited keys.
const rulesFor = (table, host) => (Object.hasOwn(table, host) ? table[host] : []);

export function allowedUrl(value, base) {
  let url;
  let decodedPath;
  try { url = new URL(value, base); decodedPath = decodeURIComponent(url.pathname); }
  catch { return null; }
  if (decodedPath.includes('\\') || decodedPath.includes('%') || decodedPath.split('/').some(part =>
    part === '.' || part === '..') || /%2f|%5c/i.test(url.pathname)) return null;
  if (url.protocol !== 'https:' || url.username || url.password || url.port) return null;
  const allowedPaths = [...rulesFor(HOME_PATHS, url.hostname), ...rulesFor(CRAWL_PATHS, url.hostname)];
  if (!matches(allowedPaths, url.pathname)) return null;
  if (/\.(pdf|zip|png|jpe?g|mp[34]|docx?|xlsx?|css|js)$/i.test(url.pathname)) return null;
  // Only listing pagination and Arabic language selectors; arbitrary search/user parameters are refused.
  if ([...url.searchParams].some(([key, value]) => key !== 'page' &&
    !(['lang', 'language'].includes(key) && value === 'ar'))) {
    return null;
  }
  url.hash = '';
  return url.href;
}

const crawlable = value => value && matches(
  rulesFor(CRAWL_PATHS, new URL(value).hostname), new URL(value).pathname) ? value : null;

/**
 * The text under the one element whose whole text is `name`. Missing or duplicated
 * headings fail closed. Content runs over following siblings until a stop label or a
 * heading that is not a nested label. Nothing is inferred from other containers.
 */
function field(document, name, stops) {
  const elements = walk(document).filter(n => isElement(n) && label(text(n)) === name);
  // Innermost match only: a wrapper whose text is just the heading is not a second match.
  const heads = elements.filter(n => !walk(n).slice(1).some(d => isElement(d) &&
    label(text(d)) === name));
  if (heads.length > 1) return { status: 'ambiguous' };
  if (heads.length === 0) return { status: 'missing' };
  const siblings = children(heads[0].parentNode ?? {});
  const body = [];
  for (const node of siblings.slice(siblings.indexOf(heads[0]) + 1)) {
    if (isElement(node) && (stops.includes(label(text(node))) ||
      (isHeading(node) && !NESTED_LABELS.includes(label(text(node)))))) break;
    body.push(node);
  }
  const value = clean(body.map(text).join(''));
  return value ? { status: 'ok', text: value, body } : { status: 'missing' };
}

/** Verbatim list items from the section; plain lines when the section has no list. */
function items(body) {
  const nodes = body.flatMap(walk);
  const listed = nodes.filter(n => n.tagName === 'li').map(n => clean(text(n))).filter(Boolean);
  return listed.length ? listed : clean(body.map(text).join('')).split('\n').filter(Boolean);
}

const others = (labels, self) => labels.filter(name => name !== self);

export function extract(html, url) {
  const document = parse(html);
  const nodes = walk(document);
  // Arabic only, whatever the URL shape: the page must declare an Arabic document language.
  // Undeclared or non-Arabic pages are not followed and yield no record.
  if (!/^ar(?:-|$)/i.test(attr(nodes.find(n => n.tagName === 'html') ?? {}, 'lang'))) {
    return { links: [], reason: 'not_arabic_page' };
  }
  const links = [...new Set(nodes.filter(n => n.tagName === 'a').map(n =>
    crawlable(allowedUrl(attr(n, 'href'), url))).filter(Boolean))];
  const { hostname, pathname } = new URL(url);
  if (matches(rulesFor(HOME_PATHS, hostname), pathname)) return { links, reason: 'home_listing' };
  if (matches(rulesFor(CRAWL_PATHS, hostname), pathname) &&
    !matches(rulesFor(RECORD_PATHS, hostname), pathname)) return { links, reason: 'category_listing' };
  if (!matches(rulesFor(RECORD_PATHS, hostname), pathname)) return { links, reason: 'unsupported_path' };
  const id = pathname + new URL(url).search;
  const title = clean(text(nodes.find(n => n.tagName === 'h1') ?? {}));
  if (!title) return { links, reason: 'missing_h1' };
  if (!arabic(title)) return { links, reason: 'not_arabic_record' };
  const fail = (status, key) => ({ links, reason: `${status}_${key}` });
  if (hostname === 'bayenat.net') {
    const question = field(document, 'نص السؤال', others(BAYENAT_LABELS, 'نص السؤال'));
    if (question.status !== 'ok') return fail(question.status, 'question_text');
    const detailed = field(document, 'الجواب التفصيلي', ['نص السؤال', 'كلمات دلالية']);
    if (detailed.status !== 'ok') return fail(detailed.status, 'detailed_answer');
    const summary = field(document, 'الخلاصة', others(BAYENAT_LABELS, 'الخلاصة'));
    if (summary.status === 'ambiguous') return fail('ambiguous', 'summary');
    const keywords = field(document, 'كلمات دلالية', others(BAYENAT_LABELS, 'كلمات دلالية'));
    if (keywords.status === 'ambiguous') return fail('ambiguous', 'keywords');
    if (!arabic(title) || !arabic(question.text) || !arabic(detailed.text)) {
      return { links, reason: 'not_arabic_record' };
    }
    return { links, record: {
      id, url, title, question_text: question.text,
      summary: summary.status === 'ok' ? summary.text : '',
      keywords: keywords.status === 'ok' ? items(keywords.body) : [],
      detailed_answer: detailed.text,
    } };
  }
  const meaning = field(document, 'المعنى الاصطلاحي', others(GLOSSARY_LABELS, 'المعنى الاصطلاحي'));
  if (meaning.status !== 'ok') return fail(meaning.status, 'terminological_meaning');
  const optional = name => field(document, name, others(GLOSSARY_LABELS, name));
  const short = optional('الشرح المختصر');
  const linguistic = optional('التعريف اللغوي المختصر');
  const definition = optional('التعريف');
  const translations = field(document, TRANSLATIONS_LABEL, others(GLOSSARY_LABELS, TRANSLATIONS_LABEL));
  for (const found of [short, linguistic, definition, translations]) {
    if (found.status === 'ambiguous') return { links, reason: 'ambiguous_section' };
  }
  if (!arabic(title) || !arabic(meaning.text)) return { links, reason: 'not_arabic_record' };
  return { links, record: {
    id, url, term_ar: title, terminological_meaning: meaning.text,
    short_explanation: short.status === 'ok' ? short.text : '',
    linguistic_definition: linguistic.status === 'ok' ? linguistic.text : '',
    definition: definition.status === 'ok' ? definition.text : '',
    translations: translations.status === 'ok' ? items(translations.body) : [],
  } };
}

export class Fetcher {
  constructor({ fetchFn = fetch, now = Date.now, sleep = ms =>
    new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
    Object.assign(this, { fetchFn, now, sleep, last: null });
  }
  async pace() {
    if (this.last !== null) await this.sleep(Math.max(0, 1000 - (this.now() - this.last)));
    this.last = this.now();
  }
  async get(url) {
    if (allowedUrl(url) !== url) throw new Error('unapproved_url');
    const origin = new URL(url).hostname;
    let current = url;
    for (let hop = 0; ; hop += 1) {
      await this.pace();
      const response = await this.fetchFn(current, { redirect: 'manual',
        signal: AbortSignal.timeout(30000),
        headers: { 'User-Agent': 'TabayyanOwnerCollector/1.0', Accept: 'text/html' } });
      if (REDIRECT_STATUS.has(response.status)) {
        if (hop === MAX_REDIRECTS) throw new Error('too_many_redirects');
        const location = response.headers.get('location');
        const next = location ? allowedUrl(location, current) : null;
        // Same-host and allowlisted targets only; cross-host redirects are refused.
        if (!next || new URL(next).hostname !== origin) throw new Error('redirect_refused');
        current = next;
        continue;
      }
      if (!response.ok) throw new Error(`http_${response.status}`);
      if (!/text\/html/i.test(response.headers.get('content-type') ?? '')) {
        throw new Error('not_html');
      }
      // Bound bytes while streaming, including when Content-Length is absent.
      const chunks = []; let length = 0;
      for await (const chunk of response.body) {
        length += chunk.length;
        if (length > 4 * 1024 * 1024) throw new Error('page_too_large');
        chunks.push(chunk);
      }
      return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
    }
  }
}

const OUTPUTS = [['bayenat.net', 'bayyinat.jsonl'], ['islamic-content.com', 'glossary.jsonl']];
const EXPECTED_ERRORS = /^(http_\d+|not_html|page_too_large|too_many_redirects|redirect_refused|duplicate_translation_language)$/;

async function writeOutputs(output, { mode, records, report, hosts, queueLength, visited, snapshots }) {
  const files = [];
  for (const [host, name] of OUTPUTS) {
    const value = records[host].map(record => JSON.stringify(record) + '\n').join('');
    const bytes = Buffer.from(value, 'utf8');
    await writeFile(path.join(output, name), bytes, { flag: 'wx' });
    files.push({ file: name, source_host: host, records: records[host].length,
      bytes: bytes.length, sha256: sha(bytes) });
  }
  // Complete only when traversal ended, every page was collected or is a recognised listing,
  // and every host that was visited produced at least one record.
  const complete = queueLength === 0 &&
    report.every(row => row.status === 'collected' || LISTING_REASONS.has(row.reason)) &&
    files.every(file => !hosts.has(file.source_host) || file.records > 0);
  const manifest = { format_version: 2, mode, authority_event: AUTHORITY,
    generated_at: new Date().toISOString(), complete, visited, remaining_pages: queueLength,
    files, snapshots,
    scope: 'owner-private; short excerpts only; no public redistribution approval' };
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await writeFile(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2));
  return manifest;
}

const emptyRecords = () => ({ 'bayenat.net': [], 'islamic-content.com': [] });

export async function collect({ output, maxPages = 10000, seeds = HOME_SEEDS,
  fetcher = new Fetcher() }) {
  // New directory only: never overwrite a previous owner handoff.
  await mkdir(path.dirname(output), { recursive: true });
  await mkdir(output);
  await mkdir(path.join(output, 'html'));
  const queue = [...seeds]; const visited = new Set();
  const records = emptyRecords(); const report = []; const snapshots = []; const hosts = new Set();
  while (queue.length && visited.size < maxPages) {
    const url = queue.shift();
    if (!allowedUrl(url) || visited.has(url)) continue;
    visited.add(url);
    hosts.add(new URL(url).hostname);
    try {
      const html = await fetcher.get(url);
      const bytes = Buffer.from(html, 'utf8');
      const file = `html/${sha(url)}.html`;
      await writeFile(path.join(output, file), bytes, { flag: 'wx' });
      snapshots.push({ file, url, sha256: sha(bytes), bytes: bytes.length });
      const result = extract(html, url);
      if (result.record) records[new URL(url).hostname].push(result.record);
      report.push({ url, status: result.record ? 'collected' : 'skipped',
        reason: result.reason ?? null });
      for (const link of result.links) if (!visited.has(link) && !queue.includes(link)) {
        queue.push(link);
      }
    } catch (error) {
      // Do not log page contents or arbitrary exception messages.
      report.push({ url, status: 'failed', reason:
        EXPECTED_ERRORS.test(error.message) ? error.message : 'fetch_or_parse_failure' });
    }
  }
  return writeOutputs(output, { mode: 'live', records, report, hosts,
    queueLength: queue.length, visited: visited.size, snapshots });
}

/** Offline re-extraction of an earlier run's snapshots. No network; hashes verified first. */
export async function collectFromHtml({ output, htmlDir }) {
  const source = JSON.parse(await readFile(path.join(htmlDir, 'manifest.json'), 'utf8'));
  if (!Array.isArray(source.snapshots)) throw new Error('from_html_requires_manifest');
  await mkdir(path.dirname(output), { recursive: true });
  await mkdir(output);
  const records = emptyRecords(); const report = []; const snapshots = []; const hosts = new Set();
  let visited = 0;
  for (const snap of source.snapshots) {
    const url = allowedUrl(snap.url);
    if (!url) { report.push({ url: String(snap.url), status: 'failed', reason: 'unapproved_url' }); continue; }
    visited += 1;
    hosts.add(new URL(url).hostname);
    if (!/^html\/[0-9a-f]{64}\.html$/.test(snap.file)) {
      report.push({ url, status: 'failed', reason: 'bad_snapshot_name' }); continue;
    }
    const bytes = await readFile(path.join(htmlDir, snap.file));
    if (sha(bytes) !== snap.sha256) {
      report.push({ url, status: 'failed', reason: 'snapshot_hash_mismatch' }); continue;
    }
    let html;
    try { html = new TextDecoder('utf-8', { fatal: true }).decode(bytes); }
    catch { report.push({ url, status: 'failed', reason: 'not_utf8' }); continue; }
    snapshots.push({ file: snap.file, url, sha256: snap.sha256, bytes: bytes.length });
    const result = extract(html, url);
    if (result.record) records[new URL(url).hostname].push(result.record);
    report.push({ url, status: result.record ? 'collected' : 'skipped',
      reason: result.reason ?? null });
  }
  return writeOutputs(output, { mode: 'from_html', records, report, hosts,
    queueLength: 0, visited, snapshots });
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help')) {
    console.log('node collect.mjs --owner-run --output NEW_PRIVATE_DIRECTORY [--max-pages 10000] [--seeds URL_LIST.txt]');
    console.log('node collect.mjs --from-html SNAPSHOT_DIRECTORY --output NEW_PRIVATE_DIRECTORY');
    return;
  }
  const value = flag => args[args.indexOf(flag) + 1];
  if (!args.includes('--output') || !value('--output')) throw new Error('Requires --output');
  const output = path.resolve(value('--output'));
  if (args.includes('--from-html')) {
    if (!value('--from-html')) throw new Error('Requires a snapshot directory');
    const result = await collectFromHtml({ output, htmlDir: path.resolve(value('--from-html')) });
    console.log(JSON.stringify({ complete: result.complete, visited: result.visited,
      files: result.files }, null, 2));
    if (!result.complete) process.exitCode = 2;
    return;
  }
  if (!args.includes('--owner-run')) throw new Error('Requires explicit --owner-run');
  const maxPages = args.includes('--max-pages') ? Number(value('--max-pages')) : 10000;
  if (!Number.isInteger(maxPages) || maxPages < 1) throw new Error('Invalid --max-pages');
  const seeds = args.includes('--seeds') ? (await readFile(value('--seeds'), 'utf8'))
    .split(/\r?\n/).map(s => s.trim()).filter(Boolean) : HOME_SEEDS;
  if (!seeds.length || seeds.some(url => !allowedUrl(url))) throw new Error('Invalid seed URL');
  const result = await collect({ output, maxPages, seeds });
  console.log(JSON.stringify({ complete: result.complete, visited: result.visited,
    files: result.files, remaining_pages: result.remaining_pages }, null, 2));
  if (!result.complete) process.exitCode = 2;
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
