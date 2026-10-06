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

// Structure of a saved bayenat.net question page (card header + card body for the question,
// author/source reference lines, a similar-phrasings card, Bootstrap tabs for the answer).
// Content is placeholder text; only the publisher's section labels and ids are real.
const tabbedBay = ({ question = true, summary = true, detailedTab = true } = {}) => arPage(
  '<div class="page-header"><div><div><h1 class="page-title">عنوان سؤال عينة</h1>' +
  '<ol class="breadcrumb"><li><a href="https://bayenat.net/ar"><i class="fas fa-home"></i> الرئيسية</a></li>' +
  '<li><a href="https://bayenat.net/ar/categories/131"> التصنيف الموضوعي</a></li><li> تصنيف عينة</li></ol>' +
  '</div></div></div>' +
  '<main class="main-content"><div class="container">' +
  '<div class="next-prev"><a href="https://bayenat.net/ar/category/131/908" class="btn btn-success">السابق</a>' +
  '<a href="https://bayenat.net/ar/category/131/910" class="btn btn-dark">التالى</a></div>' +
  (question ? '<div class="card question-card shadow-sm"><div class="card-header">' +
    '<h2 class="card-title"> نص السؤال</h2></div>' +
    '<div class="card-body islamic-typography"><table><tbody><tr><td>' +
    '<p>فقرة أولى من نص السؤال.</p><p>فقرة ثانية من نص السؤال؛&nbsp;</p></td></tr></tbody></table></div>' +
    '<div class="reference"><h4><i class="fa fa-user"></i>  المؤلف: <span> مؤلف عينة </span></h4></div>' +
    '<div class="reference"><h4><i class="fa fa-pen"></i>  المصدر: <span> مصدر عينة </span></h4></div></div>' : '') +
  '<div class="card question-card second shadow-sm"><div class="card-header">' +
  '<h2 class="card-title"> عبارات مشابهة للسؤال</h2></div>' +
  '<div class="card-body islamic-typography"><p>صياغة مشابهة عينة&nbsp;</p></div></div>' +
  '<div class="shobha-menu"><ul class="nav nav-tabs" role="tablist">' +
  '<li role="presentation" class="active"><a href="#allAnswers" aria-controls="allAnswers" role="tab" data-toggle="tab">' +
  '<i class="flaticon flaticon-monitoring"></i><h4> عرض الرد كاملا </h4></a></li>' +
  (detailedTab ? '<li role="presentation"><a href="#detailedAnswer" aria-controls="detailedAnswer" role="tab" data-toggle="tab">' +
    '<i class="flaticon"></i><h4> الجواب التفصيلي </h4></a></li>' : '') +
  (summary ? '<li role="presentation"><a href="#summary" aria-controls="summary" role="tab" data-toggle="tab">' +
    '<h4> الخلاصة </h4></a></li>' : '') +
  '</ul><div class="tab-content">' +
  '<div role="tabpanel" class="tab-pane active" id="allAnswers"><p>فقرة أولى من الجواب التفصيلي.</p>' +
  '<p>فقرة ثانية من الجواب.</p>' + (summary ? '<p>خلاصة عينة.</p>' : '') + '</div>' +
  '<div role="tabpanel" class="tab-pane" id="detailedAnswer"><p>فقرة أولى من الجواب التفصيلي.</p>' +
  '<p>فقرة ثانية من الجواب.</p></div>' +
  (summary ? '<div role="tabpanel" class="tab-pane" id="summary"><p>خلاصة عينة.</p></div>' : '') +
  '</div></div></div></main>');
const TABBED_URL = 'https://bayenat.net/ar/category/131/909';

test('bayenat tabbed page: question from the card body, answer and summary from the panes', () => {
  const { record, reason } = extract(tabbedBay(), TABBED_URL);
  assert.equal(reason, undefined);
  assert.equal(record.id, '/ar/category/131/909');
  assert.equal(record.title, 'عنوان سؤال عينة');
  assert.equal(record.question_text, 'فقرة أولى من نص السؤال.\nفقرة ثانية من نص السؤال؛');
  assert.ok(!/مؤلف|مصدر|السابق|التالى/.test(record.question_text));
  assert.equal(record.detailed_answer, 'فقرة أولى من الجواب التفصيلي.\nفقرة ثانية من الجواب.');
  assert.equal(record.summary, 'خلاصة عينة.');
  assert.deepEqual(record.keywords, []);
});

test('bayenat tabbed page without a summary keeps the detailed answer and an empty summary', () => {
  const { record } = extract(tabbedBay({ summary: false }), TABBED_URL);
  assert.equal(record.summary, '');
  assert.equal(record.detailed_answer.split('\n')[0], 'فقرة أولى من الجواب التفصيلي.');
});

test('bayenat tabbed page without a question card uses the h1 as the question', () => {
  const { record } = extract(tabbedBay({ question: false }), TABBED_URL);
  assert.equal(record.question_text, 'عنوان سؤال عينة');
  assert.equal(record.detailed_answer, 'فقرة أولى من الجواب التفصيلي.\nفقرة ثانية من الجواب.');
});

test('bayenat detailed answer falls back to the known pane ids when no tab names it', () => {
  const { record } = extract(tabbedBay({ detailedTab: false }), TABBED_URL);
  assert.equal(record.detailed_answer, 'فقرة أولى من الجواب التفصيلي.\nفقرة ثانية من الجواب.');
  const onlyFull = tabbedBay({ detailedTab: false }).replace('id="detailedAnswer"', 'id="other"');
  assert.match(extract(onlyFull, TABBED_URL).record.detailed_answer, /^فقرة أولى من الجواب التفصيلي\./);
  const none = onlyFull.replace('id="allAnswers"', 'id="none"');
  assert.equal(extract(none, TABBED_URL).reason, 'missing_detailed_answer');
});

// Real pages repeat section headings: the full-reply pane (#allAnswers) carries every
// section with its heading, and the dedicated pane carries the section heading again.
const dupBay = ({ detailedPane = true, summaryPane = true, detailedCopies = 1, summaryCopies = 1,
  identical = false } = {}) => arPage(
  '<h1>عنوان سؤال عينة</h1>' +
  '<div class="card"><div class="card-header"><h2> نص السؤال</h2></div>' +
  '<div class="card-body"><p>نص سؤال عينة.</p></div></div>' +
  '<ul class="nav nav-tabs" role="tablist">' +
  '<li><a href="#allAnswers" aria-controls="allAnswers" role="tab"><h4> عرض الرد كاملا </h4></a></li>' +
  (detailedPane ? '<li><a href="#detailedAnswer" aria-controls="detailedAnswer" role="tab"><h4> الجواب التفصيلي </h4></a></li>' : '') +
  '</ul><div class="tab-content">' +
  '<div role="tabpanel" id="allAnswers"><h3>الجواب التفصيلي</h3><p>نسخة الرد الكامل من الجواب.</p>' +
  '<h3>الخلاصة</h3><p>نسخة الرد الكامل من الخلاصة.</p></div>' +
  (detailedPane ? '<div role="tabpanel" id="detailedAnswer"><h3>الجواب التفصيلي</h3><p>جواب تفصيلي من لوحته.</p></div>' : '') +
  Array.from({ length: detailedCopies - 1 }, (_, i) =>
    `<section><h3>الجواب التفصيلي</h3><p>${identical ? 'جواب تفصيلي من لوحته.' : `نسخة مستقلة ${i + 1} من الجواب.`}</p></section>`).join('') +
  (summaryPane ? '<div role="tabpanel" id="summary"><h3>الخلاصة</h3><p>خلاصة من لوحتها.</p></div>' : '') +
  Array.from({ length: summaryCopies - 1 }, (_, i) =>
    `<section><h3>الخلاصة</h3><p>${identical ? 'خلاصة من لوحتها.' : `خلاصة مستقلة ${i + 1}.`}</p></section>`).join('') +
  '</div>');

test('duplicated labels: the detailedAnswer pane wins over the full-reply copy and a tab link', () => {
  const { record, reason } = extract(dupBay(), TABBED_URL);
  assert.equal(reason, undefined);
  assert.equal(record.detailed_answer, 'جواب تفصيلي من لوحته.');
  assert.equal(record.summary, 'خلاصة من لوحتها.');
});

test('duplicated labels: the full-reply copy is used only when it is the sole candidate', () => {
  const { record } = extract(dupBay({ detailedPane: false, summaryPane: false }), TABBED_URL);
  // In the full reply the detailed answer runs on through its nested summary heading,
  // as in the flat markup; the summary section is its own copy.
  assert.equal(record.detailed_answer.split('\n')[0], 'نسخة الرد الكامل من الجواب.');
  assert.equal(record.summary, 'نسخة الرد الكامل من الخلاصة.');
});

test('duplicated labels: identical copies collapse, differing detailed answers take the first', () => {
  const same = extract(dupBay({ detailedPane: false, detailedCopies: 3, identical: true }), TABBED_URL);
  assert.equal(same.record.detailed_answer, 'جواب تفصيلي من لوحته.');
  const differing = extract(dupBay({ detailedPane: false, detailedCopies: 3 }), TABBED_URL);
  assert.equal(differing.record.detailed_answer, 'نسخة مستقلة 1 من الجواب.');
});

test('duplicated labels: differing summaries outside the full reply still fail closed', () => {
  assert.equal(extract(dupBay({ summaryCopies: 2 }), TABBED_URL).reason, 'ambiguous_summary');
  const identical = extract(dupBay({ summaryCopies: 2, identical: true }), TABBED_URL);
  assert.equal(identical.record.summary, 'خلاصة من لوحتها.');
});

test('a page with no detailed answer anywhere stays skipped', () => {
  const none = dupBay({ detailedPane: false }).replace('id="allAnswers"', 'id="none"')
    .replace('<h3>الجواب التفصيلي</h3><p>نسخة الرد الكامل من الجواب.</p>', '');
  assert.equal(extract(none, TABBED_URL).reason, 'missing_detailed_answer');
});

test('bayenat record fails closed on missing or duplicated sections', () => {
  // A missing question section falls back to the h1; a duplicated one still fails.
  const missingQuestion = bay.replace('<h2>نص السؤال</h2><p>نص سؤال عينة للاختبار.</p>', '');
  assert.equal(extract(missingQuestion, BAY_URL).record.question_text, 'سؤال عينة');
  const twoQuestions = bay.replace('<h2>الجواب التفصيلي</h2>', '<h2>نص السؤال</h2><p>ثانٍ.</p><h2>الجواب التفصيلي</h2>');
  assert.equal(extract(twoQuestions, BAY_URL).reason, 'ambiguous_question_text');
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
    // The h1 stands in for a missing question section; the missing detailed answer
    // is what keeps this page out of the handoff.
    assert.equal(report.find(row => row.url.endsWith('/x/2')).reason, 'missing_detailed_answer');
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
