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
        'https://bayenat.net/': arPage('<a href="/question/1?lang=ar">One</a>' +
          '<a href="/question/1?language=ar">Two</a><a href="/question/1?page=2">Three</a>' +
          '<a href="/question/1?lang=en">English</a>'),
        'https://islamic-content.com/dictionary': arPage(
          '<a href="/dictionary/word/1?lang=ar">Term</a>'),
      };
      const bay = arPage('<h1>سؤال عينة</h1><section id="short-answer"><p>جواب قصير &amp; دقيق.</p></section>');
      const term = arPage('<h1>سؤال عينة</h1><section id="definition_short"><p>تعريف.</p></section>');
      const manifest = await collect({ output, fetcher: { get: async url =>
        pages[url] ?? (url.includes('bayenat.net') ? bay : term) } });
      assert.equal(manifest.complete, true);
      const bayyinat = await readFile(path.join(output, 'bayyinat.jsonl'), 'utf8');
      assert.ok(!bayyinat.includes('lang=en'), 'English selectors must not be collected');
      const script = `import json,sys\nfrom pathlib import Path\nsys.path.insert(0,'.')\n` +
        `from corpus.short_indexes import load_short_index\n` +
        `directory=Path(sys.argv[1])\nmanifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))\n` +
        `for source,name,count in [('bayyinat','bayyinat.jsonl',3),` +
        `('jamhara-glossary','glossary.jsonl',1)]:\n` +
        ` digest=next(row['sha256'] for row in manifest['files'] if row['file']==name)\n` +
        ` rows=load_short_index(directory,source,digest,allow_pending_review=True)\n` +
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
