import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { allowedUrl, extract, Fetcher, collect } from './collect.mjs';

// Synthetic non-religious content; Arabic strings are publisher section labels only.
const arPage = body => `<!doctype html><html lang="ar"><body>${body}</body></html>`;
const bay = arPage('<h1>Sample question</h1><section><h2>عبارات مشابهة للسؤال</h2>' +
  '<p>Alternate label</p></section><section id="short-answer">' +
  '<p>Short &amp; exact.</p></section><h2>الجواب المفصل</h2>' +
  '<p>Detailed text must not enter the record.</p>');
const glossary = arPage('<h1>Sample term</h1><div id="definition_short">Brief &amp; exact.</div>' +
  '<table id="translations"><tr><th>Language</th><th>Text</th></tr>' +
  '<tr><td>English</td><td>Sample translation</td></tr></table>');

test('URL allowlist rejects host tricks, unrelated paths, assets and personal queries', () => {
  for (const url of ['http://bayenat.net/x', 'https://bayenat.net.evil/x',
    'https://user@bayenat.net/x', 'https://bayenat.net:444/x',
    'https://islamic-content.com/news', 'https://bayenat.net/x.pdf',
    'https://bayenat.net/news/1',
    'https://bayenat.net/?q=personal', 'https://bayenat.net/en/questions/1',
    'https://bayenat.net/fr/questions/1', 'https://bayenat.net/questions/1?lang=en',
    'https://bayenat.net/questions/1?language=en']) assert.equal(allowedUrl(url), null);
  assert.equal(allowedUrl('/dictionary/word/3529#x', 'https://islamic-content.com'),
    'https://islamic-content.com/dictionary/word/3529');
  assert.equal(allowedUrl('https://bayenat.net/ar/questions/1?page=2'),
    'https://bayenat.net/ar/questions/1?page=2');
  assert.equal(allowedUrl('https://bayenat.net/questions/1'), 'https://bayenat.net/questions/1');
  assert.equal(allowedUrl('https://bayenat.net/questions/1?lang=ar'),
    'https://bayenat.net/questions/1?lang=ar');
});
test('pages must declare an Arabic document language, whatever the URL', () => {
  const english = bay.replace('lang="ar"', 'lang="en"');
  const undeclared = bay.replace(' lang="ar"', '');
  for (const html of [english, undeclared]) {
    const result = extract(html, 'https://bayenat.net/questions/1');
    assert.equal(result.record, undefined);
    assert.equal(result.reason, 'not_arabic_page');
    assert.deepEqual(result.links, []);
  }
  const listing = extract(arPage('<a href="/questions/1">Sample</a>'), 'https://bayenat.net/');
  assert.deepEqual(listing.links, ['https://bayenat.net/questions/1']);
});
test('extract short source fields only, preserving decoded text', () => {
  const result = extract(bay, 'https://bayenat.net/question/1');
  assert.equal(result.record.short_answer, 'Short & exact.');
  assert.deepEqual(result.record.similar_phrasings, ['Alternate label']);
  assert.ok(!JSON.stringify(result.record).includes('Detailed text'));
  const term = extract(glossary, 'https://islamic-content.com/dictionary/word/1').record;
  assert.equal(term.definition_short, 'Brief & exact.');
  assert.deepEqual(term.translations, { English: 'Sample translation' });
  for (const url of ['https://bayenat.net/question/1',
    'https://islamic-content.com/dictionary/word/1']) {
    assert.equal(extract(arPage('<h1>Sample</h1><p>Full text</p>'), url).record, undefined);
  }
});
test('global 1 request/s limit and manual redirects', async () => {
  let time = 0; const starts = []; const options = [];
  const fetcher = new Fetcher({ now: () => time, sleep: async ms => { time += ms; },
    fetchFn: async (url, opts) => {
      starts.push(time); options.push(opts);
      return new Response('text', { headers: { 'Content-Type': 'text/html' } });
    } });
  await fetcher.get('https://bayenat.net/');
  await fetcher.get('https://islamic-content.com/dictionary');
  assert.deepEqual(starts, [0, 1000]);
  assert.ok(options.every(opts => opts.redirect === 'manual'));
  const redirect = new Fetcher({ fetchFn: async () => new Response('', { status: 302 }) });
  await assert.rejects(redirect.get('https://bayenat.net/'), /http_302/);
});
test('ambiguous following siblings and nested detailed containers fail closed', () => {
  for (const html of [
    '<h1>Sample</h1><h2>مختصر الجواب</h2><p>Short.</p><div><p>Detailed text.</p></div>',
    '<h1>Sample</h1><div id="short-answer"><p>Short.</p>' +
      '<div><p>Detailed text.</p></div></div>',
    '<h1>Sample</h1><div id="short-answer"><p>Short.</p><h2>Full answer</h2></div>',
    '<h1>Sample</h1><div id="short-answer"><p class="detailed-answer">Detailed.</p></div>',
  ]) assert.equal(extract(arPage(html), 'https://bayenat.net/question/1').record, undefined);
});
test('missing short content or title on a question prevents complete handoff', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-collector-'));
  try {
    const seeds = ['https://bayenat.net/question/1', 'https://bayenat.net/question/2',
      'https://islamic-content.com/dictionary/word/1'];
    for (const [index, broken] of [arPage('<h1>Question</h1><p>Full text only</p>'),
      arPage('<div id="short-answer">Short but missing title</div>')].entries()) {
      const result = await collect({ output: path.join(directory, String(index)), seeds,
        fetcher: { get: async url => url.endsWith('/question/2') ? broken :
          url.includes('bayenat') ? bay : glossary } });
      assert.equal(result.complete, false);
    }
    assert.equal(extract(arPage('<a href="/question/1">Sample</a>'),
      'https://bayenat.net/').reason, 'bayyinat_listing');
  } finally {
    assert.equal(path.dirname(path.resolve(directory)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(directory).startsWith('tabayyan-collector-'));
    await rm(directory, { recursive: true, force: true });
  }
});
test('non HTML and oversized bodies fail closed', async () => {
  for (const response of [new Response('{}', { headers: { 'Content-Type': 'application/json' } }),
    new Response('x'.repeat(4 * 1024 * 1024 + 1),
      { headers: { 'Content-Type': 'text/html' } })]) {
    await assert.rejects(new Fetcher({ fetchFn: async () => response })
      .get('https://bayenat.net/'), /not_html|page_too_large/);
  }
});
test('hashes cover output bytes; no overwrite; failures and limits stay visible', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-collector-'));
  try {
    const output = path.join(directory, 'output');
    const seeds = ['https://bayenat.net/question/1',
      'https://islamic-content.com/dictionary/word/1'];
    const fetcher = { get: async url => url.includes('bayenat') ? bay : glossary };
    const manifest = await collect({ output, seeds, fetcher });
    assert.equal(manifest.complete, true);
    for (const file of manifest.files) {
      const bytes = await readFile(path.join(output, file.file));
      assert.equal(createHash('sha256').update(bytes).digest('hex'), file.sha256);
      assert.equal(bytes.length, file.bytes);
      assert.equal(file.records, 1);
    }
    await assert.rejects(collect({ output, seeds, fetcher }), /EEXIST/);
    const bounded = await collect({ output: path.join(directory, 'bounded'),
      seeds, fetcher, maxPages: 1 });
    assert.equal(bounded.complete, false);
    assert.equal(bounded.remaining_pages, 1);
    const failed = await collect({ output: path.join(directory, 'failed'), seeds,
      fetcher: { get: async () => { throw new Error('secret page text'); } } });
    assert.equal(failed.complete, false);
    assert.ok(!(await readFile(path.join(directory, 'failed/report.json'), 'utf8'))
      .includes('secret page text'));
  } finally {
    assert.equal(path.dirname(path.resolve(directory)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(directory).startsWith('tabayyan-collector-'));
    await rm(directory, { recursive: true, force: true });
  }
});
