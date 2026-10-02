import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const root = new URL('../', import.meta.url);
const read = (path) => readFileSync(new URL(path, root), 'utf8');
// SPEC.md sections 4.1 and 4.2, merged in PR #5. Change only after SPEC review.
const legalDomains = new Set([
  'quran', 'hadith', 'tafsir', 'aqeeda', 'fiqh', 'seerah', 'glossary', 'faq',
  'quran_translation',
]);

function registerRows(markdown) {
  const lines = markdown.split(/\r?\n/);
  const start = lines.findIndex((line) => line.startsWith('| Source id |'));
  assert.ok(start >= 0, 'Source register table is required');
  const cells = (line) => line.trim().slice(1, -1).split('|').map((cell) => cell.trim());
  const headers = cells(lines[start]);
  assert.ok(headers.includes('license'), 'Explicit license column is required');
  assert.equal(headers.indexOf('Source id'), 0);
  const rows = [];
  for (const line of lines.slice(start + 2)) {
    if (!line.startsWith('|')) break;
    const values = cells(line);
    assert.equal(values.length, headers.length, 'Register row column count');
    const row = Object.fromEntries(headers.map((header, index) => [header, values[index]]));
    assert.ok(row.license, `Missing license for ${row['Source id']}`);
    rows.push(row);
  }
  assert.ok(rows.length > 0, 'Source register must not be empty');
  return rows;
}

function uniqueIds(ids, label) {
  for (const id of ids) assert.ok(typeof id === 'string' && id.length > 0, `${label}: missing ID`);
  assert.equal(new Set(ids).size, ids.length, `${label}: duplicate source ID`);
  return new Set(ids);
}

function checkIds(sources, rows) {
  const allowed = uniqueIds(sources.map((source) => source.source_id), 'Allowlist');
  const registered = uniqueIds(rows.map((row) => row['Source id']), 'Register');
  assert.deepEqual(registered, allowed, 'Register and allowlist source IDs must be equal');
  return allowed;
}

function checkDomains(sources) {
  for (const source of sources) {
    assert.ok(Array.isArray(source.domains) && source.domains.length > 0,
      `${source.source_id}: domains must be a nonempty array`);
    for (const domain of source.domains) {
      assert.ok(legalDomains.has(domain), `${source.source_id}: illegal domain ${domain}`);
    }
  }
}

function checkCorpus(jsonl, allowed) {
  for (const [index, line] of jsonl.split(/\r?\n/).entries()) {
    if (!line.trim()) continue;
    const record = JSON.parse(line);
    assert.ok(allowed.has(record.source_id),
      `Corpus line ${index + 1}: unregistered source ID ${record.source_id}`);
  }
}

const sources = JSON.parse(read('corpus/approved_sources.json')).sources;
const rows = registerRows(read('SOURCES.md'));

test('source register IDs equal allowlist IDs, without duplicates', () => {
  checkIds(sources, rows);
});

test('allowlist domains are among the nine pinned SPEC values', () => {
  checkDomains(sources);
});

test('corpus source IDs are a subset of the allowlist when records exist', (context) => {
  const path = fileURLToPath(new URL('corpus/corpus.jsonl', root));
  if (!existsSync(path)) {
    context.diagnostic('No corpus/corpus.jsonl present; no corpus records validated.');
    return;
  }
  checkCorpus(readFileSync(path, 'utf8'), checkIds(sources, rows));
});

test('register drift, duplicates, and missing license columns fail', () => {
  assert.throws(() => checkIds(sources, rows.slice(1)), /must be equal/);
  assert.throws(() => checkIds([...sources, sources[0]], rows), /duplicate source ID/);
  assert.throws(() => checkIds(sources, [...rows, rows[0]]), /duplicate source ID/);
  assert.throws(() => registerRows(read('SOURCES.md').replace('| license |', '| finding |')),
    /license column/);
});

test('unknown or missing domains fail instead of extending the enum', () => {
  assert.throws(() => checkDomains([{ source_id: 'fixture', domains: ['history'] }]),
    /illegal domain/);
  assert.throws(() => checkDomains([{ source_id: 'fixture', domains: [] }]),
    /nonempty array/);
});

test('corpus fixtures accept registered IDs and reject unknown or missing IDs', () => {
  const allowed = new Set(['fixture-source']);
  // Synthetic metadata only: no religious text, source attribution, or approval claim.
  checkCorpus('\n{"source_id":"fixture-source"}\n', allowed);
  assert.throws(() => checkCorpus('{"source_id":"unknown"}', allowed), /unregistered source ID/);
  assert.throws(() => checkCorpus('{}', allowed), /unregistered source ID/);
  assert.throws(() => checkCorpus('not json', allowed), SyntaxError);
});
