import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const collectorPath = process.env.R1_COLLECTOR_PATH ??
  path.resolve('tools/source-collector/collect.mjs');

test('actual R1 collector to R2 loader: publisher language and page selectors',
  { skip: !existsSync(collectorPath) && 'R1 collector dependency not merged' }, async () => {
    const { collect } = await import(pathToFileURL(collectorPath));
    const directory = await mkdtemp(path.join(os.tmpdir(), 'tabayyan-handoff-'));
    try {
      const output = path.join(directory, 'collection');
      const arPage = body => `<!doctype html><html lang="ar"><body>${body}</body></html>`;
      const pages = {
        'https://bayenat.net/': arPage('<a href="/ar/categories/sample">Category</a>'),
        'https://bayenat.net/ar/categories/sample': arPage(
          '<a href="/ar/category/sample/1?lang=ar">One</a>' +
          '<a href="/ar/category/sample/1?language=ar">Two</a>' +
          '<a href="/ar/category/sample/1?page=2">Three</a>' +
          '<a href="/ar/category/sample/1?lang=en">English</a>'),
        'https://islamic-content.com/dictionary': arPage(
          '<a href="/dictionary/word/1?lang=ar">Term</a>'),
      };
      const bay = arPage('<h1>سؤال عينة</h1>' +
        '<h2>نص السؤال</h2><p>نص سؤال عينة.</p>' +
        '<h2>الجواب التفصيلي</h2><p>جواب عينة &amp; دقيق.</p>');
      const term = arPage('<h1>مصطلح عينة</h1>' +
        '<h2>المعنى الاصطلاحي</h2><p>تعريف عينة.</p>' +
        '<h2>ترجمة هذا المصطلح متوفرة باللغات التالية</h2>' +
        '<ul><li>English: Sample equivalent</li></ul>');
      const fetched = [];
      const manifest = await collect({ output, fetcher: { get: async url => {
        fetched.push(url);
        return pages[url] ?? (url.includes('bayenat.net') ? bay : term);
      } } });
      assert.equal(manifest.complete, true);
      const bayyinat = await readFile(path.join(output, 'bayyinat.jsonl'), 'utf8');
      assert.ok(!bayyinat.includes('lang=en'), 'English selectors must not be collected');
      assert.ok(!fetched.some(url => url.includes('lang=en')), 'English selectors must not be fetched');
      const script = `import json,sys\nfrom pathlib import Path\nsys.path.insert(0,'.')\n` +
        `from corpus.short_indexes import load_short_index\n` +
        `directory=Path(sys.argv[1])\nmanifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))\n` +
        `for source,name,count in [('bayyinat','bayyinat.jsonl',3),` +
        `('jamhara-glossary','glossary.jsonl',1)]:\n` +
        ` digest=next(row['sha256'] for row in manifest['files'] if row['file']==name)\n` +
        ` rows=load_short_index(directory,source,digest,allow_pending_review=True,expected_format_version=2)\n` +
        ` original=tuple(json.loads(line) for line in (directory/name).read_text(encoding='utf-8').splitlines())\n` +
        ` assert rows==original and len(rows)==count\n` +
        ` assert all('?' in row['url'] and '?' in row['id'] for row in rows)\n`;
      const result = spawnSync(process.env.R2_TEST_PYTHON ?? 'python', ['-c', script, output],
        { cwd: process.cwd(), encoding: 'utf8' });
      assert.equal(result.status, 0, result.stderr || result.error?.message);
    } finally {
      assert.equal(path.dirname(path.resolve(directory)), path.resolve(os.tmpdir()));
      assert.ok(path.basename(directory).startsWith('tabayyan-handoff-'));
      await rm(directory, { recursive: true, force: true });
    }
  });
