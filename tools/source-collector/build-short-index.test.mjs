import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, readFile, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';

import { AUTHORITY, buildShortIndex, sourceStatus, verifyRun } from './build-short-index.mjs';

const sha = value => createHash('sha256').update(value).digest('hex');

async function run(dir, { glossaryRows = 3, bayyinatRows = 0, complete = false, remaining = 0,
  report = [], snapshots = 2500, authority = AUTHORITY, tamper = false } = {}) {
  await mkdir(path.join(dir, 'html'), { recursive: true });
  const files = [];
  for (const [file, host, rows] of [['bayyinat.jsonl', 'bayenat.net', bayyinatRows],
    ['glossary.jsonl', 'islamic-content.com', glossaryRows]]) {
    const lines = Array.from({ length: rows }, (_, i) => JSON.stringify({ id: `/x/${i}`, url: `https://${host}/x/${i}` }) + '\n');
    const bytes = Buffer.from(lines.join(''), 'utf8');
    await writeFile(path.join(dir, file), tamper && rows ? Buffer.concat([bytes, Buffer.from('\n')]) : bytes);
    files.push({ file, source_host: host, records: rows, bytes: bytes.length, sha256: sha(bytes) });
  }
  const manifest = { format_version: 2, mode: 'from_html', authority_event: authority, generated_at: 'now',
    complete, visited: 10, remaining_pages: remaining, files,
    snapshots: Array.from({ length: snapshots }, (_, i) => ({ file: `html/${i}.html`, url: 'u', sha256: 'h', bytes: 1 })),
    scope: 'owner-private' };
  await writeFile(path.join(dir, 'manifest.json'), JSON.stringify(manifest));
  await writeFile(path.join(dir, 'report.json'), JSON.stringify(report));
  return files;
}

const tmp = () => mkdtemp(path.join(os.tmpdir(), 'short-index-'));

test('glossary-only run with complete:false still yields a complete glossary source', async () => {
  const runDir = await tmp();
  const [, glossary] = await run(runDir, { report: [
    { url: 'https://islamic-content.com/dictionary', status: 'skipped', reason: 'home_listing' },
    { url: 'https://islamic-content.com/dictionary/word/1', status: 'collected' },
    { url: 'https://bayenat.net/', status: 'skipped', reason: 'home_listing' }] });
  const output = await tmp();
  const { manifest } = await buildShortIndex({ output, runs: { glossary: runDir } });
  assert.equal(manifest.format_version, 2);
  assert.equal(manifest.complete, true);
  assert.deepEqual(manifest.files.map(f => f.file), ['glossary.jsonl']);
  assert.equal(manifest.files[0].sha256, glossary.sha256);
  assert.equal(manifest.files[0].status, 'complete');
  assert.equal(manifest.sources.glossary.records, 3);
  assert.ok(!('snapshots' in manifest));
  const copied = await readFile(path.join(output, 'glossary.jsonl'));
  assert.equal(sha(copied), glossary.sha256);
  const written = JSON.parse(await readFile(path.join(output, 'manifest.json'), 'utf8'));
  assert.equal(written.authority_event, AUTHORITY);
});

test('page-capped bayyinat run is partial and the merged manifest says so per source', async () => {
  const glossaryRun = await tmp();
  await run(glossaryRun, { complete: false, report: [{ url: 'https://islamic-content.com/dictionary/word/1', status: 'collected' }] });
  const bayyinatRun = await tmp();
  await run(bayyinatRun, { glossaryRows: 0, bayyinatRows: 40, remaining: 120,
    report: [{ url: 'https://bayenat.net/ar/category/a/1', status: 'collected' }] });
  const output = await tmp();
  const { manifest } = await buildShortIndex({ output, runs: { glossary: glossaryRun, bayyinat: bayyinatRun } });
  assert.equal(manifest.complete, false);
  assert.deepEqual(Object.fromEntries(manifest.files.map(f => [f.file, f.status])),
    { 'glossary.jsonl': 'complete', 'bayyinat.jsonl': 'partial' });
  assert.equal(manifest.sources.bayyinat.remaining_pages, 120);
  assert.equal(manifest.files.length, 2);
});

test('a failed page for the host, or a complete run flag, decides the status', () => {
  const base = { complete: false, remaining_pages: 0 };
  assert.equal(sourceStatus({ ...base }, [{ url: 'https://bayenat.net/p', status: 'failed', reason: 'http_500' }], 'bayenat.net', 5), 'partial');
  assert.equal(sourceStatus({ ...base }, [{ url: 'https://bayenat.net/p', status: 'collected' }], 'bayenat.net', 5), 'complete');
  assert.equal(sourceStatus({ ...base }, null, 'bayenat.net', 5), 'partial');
  assert.equal(sourceStatus({ complete: true }, null, 'bayenat.net', 5), 'complete');
  assert.equal(sourceStatus({ ...base }, [], 'bayenat.net', 0), 'partial');
});

test('a file that differs from its run manifest is refused', async () => {
  const runDir = await tmp();
  await run(runDir, { tamper: true });
  await assert.rejects(verifyRun(runDir, 'glossary'), /sha256 differs/);
  const empty = await tmp();
  await run(empty, { glossaryRows: 0 });
  await assert.rejects(verifyRun(empty, 'glossary'), /no records/);
  const foreign = await tmp();
  await run(foreign, { authority: 'f'.repeat(64) });
  await assert.rejects(verifyRun(foreign, 'glossary'), /authority mismatch/);
  await assert.rejects(buildShortIndex({ output: await tmp(), runs: {} }), /Pass --glossary/);
});
