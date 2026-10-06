import test from 'node:test';
import assert from 'node:assert/strict';
import { appendFile, mkdtemp, readFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { allowedUrl, collect, collectFromHtml, extract, Fetcher } from './collect.mjs';

// Synthetic non-religious content; Arabic strings are publisher section labels only.
const arPage = body => `<!doctype html><html lang="ar"><body>${body}</body></html>`;
const BAY_URL = 'https://bayenat.net/ar/category/x/1';
const TERM_URL = 'https://islamic-content.com/dictionary/word/1';
const bay = arPage('<h1>سؤال عينة</h1>' +
  '<h2>نص السؤال</h2><p>نص سؤال عينة للاختبار.</p>' +
  '<h2>الجواب التفصيلي</h2><p>فقرة أولى من الجواب التفصيلي.</p>' +
  '<h3>الخلاصة</h3><p>خلاصة عينة &amp; دقيقة.</p>' +
  '<h3>المراجع</h3><p>مرجع عينة</p>' +
  '<h2>كلمات دلالية</h2><ul><li>كلمة أولى</li><li>كلمة ثانية</li></ul>');
const glossary = arPage('<h1>مصطلح عينة</h1>' +
  '<h2>المعنى الاصطلاحي</h2><p>معنى اصطلاحي عينة &amp; دقيق.</p>' +
  '<h2>الشرح المختصر</h2><p>شرح مختصر عينة.</p>' +
  '<h2>التعريف اللغوي المختصر</h2><p>تعريف لغوي عينة.</p>' +
  '<h2>التعريف</h2><p>تعريف عينة.</p>' +
  '<h2>ترجمة هذا المصطلح متوفرة باللغات التالية</h2><ul><li>English: Sample translation</li></ul>');
const html = { 'Content-Type': 'text/html' };

test('URL allowlist: category listings and records only, plus home seeds', () => {
  for (const url of ['http://bayenat.net/ar/categories/x', 'https://bayenat.net.evil/ar/categories/x',
    'https://user@bayenat.net/ar/categories/x', 'https://bayenat.net:444/ar/categories/x',
    'https://islamic-content.com/news', 'https://bayenat.net/ar/categories/x.pdf',
    'https://bayenat.net/news/1', 'https://bayenat.net/?q=personal',
    'https://bayenat.net/en/categories/x', 'https://bayenat.net/fr/category/x/1',
    'https://bayenat.net/questions/1', 'https://bayenat.net/ar/category/x/1?lang=en',
    'https://bayenat.net/ar/category/x/1?language=en', 'https://islamic-content.com/dictionary/search',
    'https://islamic-content.com/dictionary/word/1/extra', 'https://constructor/']) {
    assert.equal(allowedUrl(url), null, url);
  }
  assert.equal(allowedUrl('/dictionary/word/3529#x', 'https://islamic-content.com'),
    'https://islamic-content.com/dictionary/word/3529');
  assert.equal(allowedUrl('https://bayenat.net/ar/category/x/1?page=2'),
    'https://bayenat.net/ar/category/x/1?page=2');
  assert.equal(allowedUrl('https://bayenat.net/ar/categories/x'), 'https://bayenat.net/ar/categories/x');
  assert.equal(allowedUrl(BAY_URL + '?lang=ar'), BAY_URL + '?lang=ar');
  for (const seed of ['https://bayenat.net/', 'https://bayenat.net/ar/',
    'https://islamic-content.com/dictionary']) assert.equal(allowedUrl(seed), seed);
});

test('pages must declare an Arabic document language, whatever the URL', () => {
  const english = bay.replace('lang="ar"', 'lang="en"');
  const undeclared = bay.replace(' lang="ar"', '');
  for (const page of [english, undeclared]) {
    const result = extract(page, BAY_URL);
    assert.equal(result.record, undefined);
    assert.equal(result.reason, 'not_arabic_page');
    assert.deepEqual(result.links, []);
  }
});

test('listings queue only crawl targets, never home pages or other paths', () => {
  const home = extract(arPage('<a href="/ar/category/x/1">Sample</a>' +
    '<a href="/questions/1">Other</a><a href="/ar/">Home</a>'), 'https://bayenat.net/ar/');
  assert.equal(home.reason, 'home_listing');
  assert.deepEqual(home.links, ['https://bayenat.net/ar/category/x/1']);
  const category = extract(arPage('<a href="/ar/category/x/2">Next</a>'),
    'https://bayenat.net/ar/categories/x');
  assert.equal(category.reason, 'category_listing');
  assert.deepEqual(category.links, ['https://bayenat.net/ar/category/x/2']);
  const dictionary = extract(arPage('<a href="/dictionary/word/9">Word</a>'),
    'https://islamic-content.com/dictionary');
  assert.equal(dictionary.reason, 'home_listing');
  assert.deepEqual(dictionary.links, ['https://islamic-content.com/dictionary/word/9']);
});

test('bayenat record: h1 question, question text, summary, keywords, detailed answer', () => {
  const { record } = extract(bay, BAY_URL);
  assert.equal(record.id, '/ar/category/x/1');
  assert.equal(record.title, 'سؤال عينة');
  assert.equal(record.question_text, 'نص سؤال عينة للاختبار.');
  assert.equal(record.summary, 'خلاصة عينة & دقيقة.');
  assert.deepEqual(record.keywords, ['كلمة أولى', 'كلمة ثانية']);
  assert.match(record.detailed_answer, /فقرة أولى من الجواب التفصيلي\./);
  assert.match(record.detailed_answer, /مرجع عينة/);
  assert.ok(!record.summary.includes('فقرة أولى'));
});

test('bayenat summary is optional and stays empty when absent', () => {
  const noSummary = bay.replace('<h3>الخلاصة</h3><p>خلاصة عينة &amp; دقيقة.</p>', '');
  const { record } = extract(noSummary, BAY_URL);
  assert.equal(record.summary, '');
  assert.match(record.detailed_answer, /فقرة أولى/);
});

test('bayenat record fails closed on missing or duplicated sections', () => {
  const missingQuestion = bay.replace('<h2>نص السؤال</h2><p>نص سؤال عينة للاختبار.</p>', '');
  assert.equal(extract(missingQuestion, BAY_URL).reason, 'missing_question_text');
  const missingDetailed = bay.replace('<h2>الجواب التفصيلي</h2><p>فقرة أولى من الجواب التفصيلي.</p>', '');
  assert.equal(extract(missingDetailed, BAY_URL).reason, 'missing_detailed_answer');
  const twoSummaries = bay.replace('<h2>كلمات دلالية</h2>', '<h3>الخلاصة</h3><p>ثانية.</p><h2>كلمات دلالية</h2>');
  const result = extract(twoSummaries, BAY_URL);
  assert.equal(result.record, undefined);
  assert.equal(result.reason, 'ambiguous_summary');
});

test('glossary record: verbatim terminological meaning, optional fields, translation list', () => {
  const { record } = extract(glossary, TERM_URL);
  assert.equal(record.id, '/dictionary/word/1');
  assert.equal(record.term_ar, 'مصطلح عينة');
  assert.equal(record.terminological_meaning, 'معنى اصطلاحي عينة & دقيق.');
  assert.equal(record.short_explanation, 'شرح مختصر عينة.');
  assert.equal(record.linguistic_definition, 'تعريف لغوي عينة.');
  assert.equal(record.definition, 'تعريف عينة.');
  assert.deepEqual(record.translations, ['English: Sample translation']);
  const bare = extract(arPage('<h1>مصطلح عينة</h1><h2>المعنى الاصطلاحي</h2><p>معنى عينة.</p>'), TERM_URL).record;
  assert.equal(bare.short_explanation, '');
  assert.deepEqual(bare.translations, []);
  const noMeaning = extract(arPage('<h1>مصطلح عينة</h1><h2>الشرح المختصر</h2><p>شرح.</p>'), TERM_URL);
  assert.equal(noMeaning.reason, 'missing_terminological_meaning');
});

test('owner translation heading retains every publisher list item verbatim', () => {
  const page = glossary.replace('<li>English: Sample translation</li>',
    '<li>English: Sample translation</li><li>French: Sample equivalent</li>');
  assert.deepEqual(extract(page, TERM_URL).record.translations,
    ['English: Sample translation', 'French: Sample equivalent']);
});

test('a declared Arabic page still needs Arabic title and required text per record', () => {
  const englishBay = arPage('<h1>Sample question</h1><h2>نص السؤال</h2><p>نص سؤال.</p>' +
    '<h2>الجواب التفصيلي</h2><p>جواب.</p>');
  const result = extract(englishBay, BAY_URL);
  assert.equal(result.record, undefined);
  assert.equal(result.reason, 'not_arabic_record');
  const englishTerm = extract(arPage('<h1>Sample term</h1><h2>المعنى الاصطلاحي</h2>' +
    '<p>English definition.</p>'), TERM_URL);
  assert.equal(englishTerm.record, undefined);
  assert.equal(englishTerm.reason, 'not_arabic_record');
});

test('letter majority: one Arabic word in an English answer is not enough', () => {
  const page = (question) => arPage(`<h1>سؤال عينة</h1><h2>نص السؤال</h2><p>${question}</p>` +
    '<h2>الجواب التفصيلي</h2><p>جواب قصير.</p>');
  assert.equal(extract(page('English question with one word عينة.'), BAY_URL).reason, 'not_arabic_record');
  const majority = extract(page('سؤال قصير وواضح مع كلمة Sample.'), BAY_URL).record;
  assert.equal(majority.question_text, 'سؤال قصير وواضح مع كلمة Sample.');
});

test('global 1 request/s limit and redirect handling', async () => {
  let time = 0; const starts = []; const options = [];
  const fetcher = new Fetcher({ now: () => time, sleep: async ms => { time += ms; },
    fetchFn: async (url, opts) => {
      starts.push(time); options.push(opts);
      return new Response('text', { headers: html });
    } });
  await fetcher.get('https://bayenat.net/');
  await fetcher.get('https://islamic-content.com/dictionary');
  assert.deepEqual(starts, [0, 1000]);
  assert.ok(options.every(opts => opts.redirect === 'manual'));
});

test('same-host redirects are followed and paced; cross-host and bare redirects are refused', async () => {
  const seen = [];
  const followed = new Fetcher({ sleep: async () => {}, fetchFn: async url => {
    seen.push(url);
    if (seen.length === 1) return new Response('', { status: 302, headers: { Location: '/ar/category/x/1' } });
    return new Response('ok', { headers: html });
  } });
  assert.equal(await followed.get('https://bayenat.net/ar/category/x/0'), 'ok');
  assert.deepEqual(seen, ['https://bayenat.net/ar/category/x/0', 'https://bayenat.net/ar/category/x/1']);

  const crossHost = new Fetcher({ sleep: async () => {}, fetchFn: async () =>
    new Response('', { status: 301, headers: { Location: 'https://islamic-content.com/dictionary/word/1' } }) });
  await assert.rejects(crossHost.get(BAY_URL), /redirect_refused/);

  const bare = new Fetcher({ sleep: async () => {}, fetchFn: async () => new Response('', { status: 302 }) });
  await assert.rejects(bare.get(BAY_URL), /redirect_refused/);

  let calls = 0;
  const looping = new Fetcher({ sleep: async () => {}, fetchFn: async () => {
    calls += 1;
    return new Response('', { status: 302, headers: { Location: '/ar/category/x/1' } });
  } });
  await assert.rejects(looping.get(BAY_URL), /too_many_redirects/);
  assert.equal(calls, 4);
});

test('non-redirect HTTP errors stay visible as http_<status>', async () => {
  const notFound = new Fetcher({ sleep: async () => {}, fetchFn: async () => new Response('', { status: 404 }) });
  await assert.rejects(notFound.get(BAY_URL), /http_404/);
});

test('non HTML and oversized bodies fail closed', async () => {
  for (const response of [new Response('{}', { headers: { 'Content-Type': 'application/json' } }),
    new Response('x'.repeat(4 * 1024 * 1024 + 1), { headers: html })]) {
    await assert.rejects(new Fetcher({ sleep: async () => {}, fetchFn: async () => response })
      .get(BAY_URL), /not_html|page_too_large/);
  }
});

test('hashes cover output bytes; no overwrite; failures and limits stay visible', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-collector-'));
  try {
    const output = path.join(directory, 'output');
    const seeds = [BAY_URL, TERM_URL];
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
    const bounded = await collect({ output: path.join(directory, 'bounded'), seeds, fetcher, maxPages: 1 });
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

test('a broken required section prevents complete handoff', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-collector-'));
  try {
    const seeds = ['https://bayenat.net/ar/category/x/1', 'https://bayenat.net/ar/category/x/2',
      TERM_URL];
    const broken = arPage('<h1>سؤال عينة</h1><p>Full text only</p>');
    const result = await collect({ output: path.join(directory, 'broken'), seeds,
      fetcher: { get: async url => url.endsWith('/x/2') ? broken :
        url.includes('bayenat') ? bay : glossary } });
    assert.equal(result.complete, false);
    const report = JSON.parse(await readFile(path.join(directory, 'broken/report.json'), 'utf8'));
    assert.equal(report.find(row => row.url.endsWith('/x/2')).reason, 'missing_question_text');
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('from-html re-extracts saved snapshots offline and rejects tampered files', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-collector-'));
  try {
    const live = path.join(directory, 'live');
    const seeds = [BAY_URL, TERM_URL];
    const first = await collect({ output: live, seeds,
      fetcher: { get: async url => url.includes('bayenat') ? bay : glossary } });
    const offline = await collectFromHtml({ output: path.join(directory, 'offline'), htmlDir: live });
    assert.equal(offline.complete, true);
    assert.equal(offline.mode, 'from_html');
    for (const file of first.files) {
      assert.deepEqual(await readFile(path.join(directory, 'offline', file.file)),
        await readFile(path.join(live, file.file)));
    }
    await appendFile(path.join(live, first.snapshots[0].file), '<!-- edited -->');
    const tampered = await collectFromHtml({ output: path.join(directory, 'tampered'), htmlDir: live });
    assert.equal(tampered.complete, false);
    const report = JSON.parse(await readFile(path.join(directory, 'tampered/report.json'), 'utf8'));
    assert.ok(report.some(row => row.reason === 'snapshot_hash_mismatch'));
    await assert.rejects(collectFromHtml({ output: path.join(directory, 'no-manifest'),
      htmlDir: directory }), /ENOENT|from_html_requires_manifest/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
