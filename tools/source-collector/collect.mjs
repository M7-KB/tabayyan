/** Owner-run collection only. Never imported by the API or run at build/startup. */
import { parse } from 'parse5';
import { createHash } from 'node:crypto';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const AUTHORITY = 'd3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f';
const ROOTS = ['https://bayenat.net/', 'https://islamic-content.com/dictionary'];
const sha = value => createHash('sha256').update(value).digest('hex');
const attr = (node, name) => node.attrs?.find(a => a.name === name)?.value ?? '';
const children = node => node.childNodes ?? [];
const walk = node => [node, ...children(node).flatMap(walk)];
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

export function allowedUrl(value, base) {
  let url;
  let decodedPath;
  try { url = new URL(value, base); decodedPath = decodeURIComponent(url.pathname); }
  catch { return null; }
  if (decodedPath.includes('\\') || decodedPath.includes('%') || decodedPath.split('/').some(part =>
    part === '.' || part === '..') || /%2f|%5c/i.test(url.pathname)) return null;
  if (url.protocol !== 'https:' || url.username || url.password || url.port) return null;
  if (!['bayenat.net', 'islamic-content.com'].includes(url.hostname)) return null;
  // Arabic pages only: no language prefix other than /ar.
  if (url.hostname === 'bayenat.net' && !/^(?:\/ar)?(?:\/(?:questions?|answers?|doubts?|shubuhat|categories?|topics?)(?:\/|$)|\/?$)/i
    .test(decodedPath)) return null;
  if (url.hostname === 'islamic-content.com' &&
      !/^\/dictionary(?:\/|$)/.test(url.pathname)) return null;
  if (/\.(pdf|zip|png|jpe?g|mp[34]|docx?|xlsx?|css|js)$/i.test(url.pathname)) return null;
  if (/(?:^|\/)(login|register|contact|privacy|copyright|about)(?:\/|$)/i
    .test(url.pathname)) return null;
  // Only listing pagination and Arabic language selectors; arbitrary search/user parameters are refused.
  if ([...url.searchParams].some(([key, value]) => key !== 'page' &&
    !(['lang', 'language'].includes(key) && value === 'ar'))) {
    return null;
  }
  url.hash = '';
  return url.href;
}

/** Extract an explicitly named short section, never a whole answer/body fallback. */
function section(document, names, ids = []) {
  const nodes = walk(document);
  const candidates = nodes.filter(n => ids.includes(attr(n, 'id')) ||
    (n.tagName === 'section' && children(n).some(child =>
      /^h[1-6]$/.test(child.tagName ?? '') && names.includes(label(text(child))))));
  // No following-sibling heuristic: only an explicit structural short container.
  if (candidates.length !== 1) return '';
  const container = candidates[0];
  const descendants = walk(container).slice(1);
  const permitted = new Set(['p', 'br', 'ul', 'ol', 'li', 'span', 'strong', 'em',
    'b', 'i', 'a', 'small', 'sup', 'sub']);
  if (descendants.some(n => n.tagName && !permitted.has(n.tagName) &&
    !(/^h[1-6]$/.test(n.tagName) && n.parentNode === container &&
      names.includes(label(text(n)))))) return '';
  if (descendants.some(n => /detailed|full[-_]?answer|long[-_]?answer/i
    .test(`${attr(n, 'id')} ${attr(n, 'class')}`))) return '';
  return clean(children(container).filter(n => !/^h[1-6]$/.test(n.tagName ?? ''))
    .map(text).join(''));
}

export function extract(html, url) {
  const document = parse(html);
  const nodes = walk(document);
  // Arabic only, whatever the URL shape: the page must declare an Arabic document language.
  // Undeclared or non-Arabic pages are not followed and yield no record.
  if (!/^ar(?:-|$)/i.test(attr(nodes.find(n => n.tagName === 'html') ?? {}, 'lang'))) {
    return { links: [], reason: 'not_arabic_page' };
  }
  const title = clean(text(nodes.find(n => n.tagName === 'h1') ?? {}));
  const links = [...new Set(nodes.filter(n => n.tagName === 'a').map(n =>
    allowedUrl(attr(n, 'href'), url)).filter(Boolean))];
  const source = new URL(url).hostname;
  const pathname = new URL(url).pathname;
  if (source === 'bayenat.net' &&
    /^(?:\/ar)?(?:\/(?:questions|answers|doubts|shubuhat|categories|topics)?\/?)?$/i
      .test(pathname)) return { links, reason: 'bayyinat_listing' };
  if (source === 'islamic-content.com' &&
    !/^\/dictionary\/word\/[^/]+\/?$/.test(pathname)) {
    return { links, reason: 'dictionary_listing' };
  }
  if (!title) return { links, reason: 'missing_h1' };
  if (source === 'bayenat.net') {
    const short = section(document, ['مختصر الجواب', 'الجواب المختصر'],
      ['short-answer', 'short_answer']);
    if (!short) return { links, reason: 'missing_explicit_short_answer' };
    return { links, record: {
      id: new URL(url).pathname + new URL(url).search, url, title,
      similar_phrasings: section(document, ['عبارات مشابهة للسؤال'])
        .split('\n').filter(Boolean),
      short_answer: short,
      keywords: section(document, ['الكلمات المفتاحية']).split('\n').filter(Boolean),
      category: section(document, ['التصنيف', 'تصنيف السؤال']),
    } };
  }
  const definition = section(document,
    ['التعريف المختصر', 'تعريف مختصر', 'المعنى المختصر'],
    ['definition-short', 'definition_short']);
  if (!definition) return { links, reason: 'missing_explicit_short_definition' };
  // Only publisher-labelled translation rows inside an explicit translations section.
  const translations = {};
  const translationRoot = nodes.find(n => ['translations', 'term-translations']
    .includes(attr(n, 'id')));
  if (translationRoot) {
    for (const row of walk(translationRoot).filter(n => n.tagName === 'tr')) {
      const cells = children(row).filter(n => ['td', 'th'].includes(n.tagName));
      if (cells.length === 2 && cells.every(n => n.tagName === 'td')) {
        const language = clean(text(cells[0]));
        const translation = clean(text(cells[1]));
        if (language && translation) {
          if (language in translations) throw new Error('duplicate_translation_language');
          translations[language] = translation;
        }
      }
    }
  }
  return { links, record: { id: new URL(url).pathname + new URL(url).search, url, term_ar: title,
    definition_short: definition, translations } };
}

export class Fetcher {
  constructor({ fetchFn = fetch, now = Date.now, sleep = ms =>
    new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
    Object.assign(this, { fetchFn, now, sleep, last: null });
  }
  async get(url) {
    if (allowedUrl(url) !== url) throw new Error('unapproved_url');
    if (this.last !== null) await this.sleep(Math.max(0, 1000 - (this.now() - this.last)));
    this.last = this.now();
    const response = await this.fetchFn(url, { redirect: 'manual',
      signal: AbortSignal.timeout(30000),
      headers: { 'User-Agent': 'TabayyanOwnerCollector/1.0', Accept: 'text/html' } });
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

export async function collect({ output, maxPages = 10000, seeds = ROOTS,
  fetcher = new Fetcher() }) {
  // New directory only: never overwrite a previous owner handoff.
  await mkdir(path.dirname(output), { recursive: true });
  await mkdir(output);
  await mkdir(path.join(output, 'html'));
  const queue = [...seeds]; const visited = new Set();
  const records = { 'bayenat.net': [], 'islamic-content.com': [] };
  const report = []; const snapshots = [];
  while (queue.length && visited.size < maxPages) {
    const url = queue.shift();
    if (!allowedUrl(url) || visited.has(url)) continue;
    visited.add(url);
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
        /^(http_\d+|not_html|page_too_large|duplicate_translation_language)$/
          .test(error.message) ? error.message : 'fetch_or_parse_failure' });
    }
  }
  const files = [];
  for (const [host, name] of [['bayenat.net', 'bayyinat.jsonl'],
    ['islamic-content.com', 'glossary.jsonl']]) {
    const value = records[host].map(record => JSON.stringify(record) + '\n').join('');
    const bytes = Buffer.from(value, 'utf8');
    await writeFile(path.join(output, name), bytes, { flag: 'wx' });
    files.push({ file: name, source_host: host, records: records[host].length,
      bytes: bytes.length, sha256: sha(bytes) });
  }
  const complete = queue.length === 0 && files.every(file => file.records > 0) &&
    report.every(row => row.status === 'collected' ||
      ['bayyinat_listing', 'dictionary_listing'].includes(row.reason));
  const manifest = { format_version: 1, authority_event: AUTHORITY,
    generated_at: new Date().toISOString(), complete, visited: visited.size,
    remaining_pages: queue.length, files, snapshots,
    scope: 'owner-private; short excerpts only; no public redistribution approval' };
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  await writeFile(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2));
  return manifest;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help')) {
    console.log('node collect.mjs --owner-run --output NEW_PRIVATE_DIRECTORY [--max-pages 10000] [--seeds URL_LIST.txt]');
    return;
  }
  if (!args.includes('--owner-run')) throw new Error('Requires explicit --owner-run');
  const value = flag => args[args.indexOf(flag) + 1];
  if (!args.includes('--output') || !value('--output')) throw new Error('Requires --output');
  const maxPages = args.includes('--max-pages') ? Number(value('--max-pages')) : 10000;
  if (!Number.isInteger(maxPages) || maxPages < 1) throw new Error('Invalid --max-pages');
  const seeds = args.includes('--seeds') ? (await readFile(value('--seeds'), 'utf8'))
    .split(/\r?\n/).map(s => s.trim()).filter(Boolean) : ROOTS;
  if (!seeds.length || seeds.some(url => !allowedUrl(url))) throw new Error('Invalid seed URL');
  const result = await collect({ output: path.resolve(value('--output')), maxPages, seeds });
  console.log(JSON.stringify({ complete: result.complete, visited: result.visited,
    files: result.files, remaining_pages: result.remaining_pages }, null, 2));
  if (!result.complete) process.exitCode = 2;
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
