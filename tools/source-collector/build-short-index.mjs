/**
 * Owner-run step: assemble the private short-index directory the API loads.
 *
 *   node build-short-index.mjs --glossary RUN_DIR [--bayyinat RUN_DIR] --output OUT_DIR
 *
 * Each RUN_DIR is one collector run (collect.mjs, live or --from-html) holding
 * manifest.json, report.json and the JSONL files. This tool copies the two JSONL
 * files, verifies each against its run manifest entry (sha256, bytes, record count),
 * derives a per-source traversal status, and writes one loader manifest listing only
 * the JSONL files: no html snapshot entries. It never fetches, parses or edits
 * records; it is never imported by the API or run at build or startup.
 */
import { createHash } from 'node:crypto';
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const AUTHORITY = 'd3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f';
const LISTING_REASONS = new Set(['home_listing', 'category_listing']);
export const SOURCES = {
  bayyinat: { file: 'bayyinat.jsonl', host: 'bayenat.net', variable: 'PRIVATE_BAYYINAT_SHA256' },
  glossary: { file: 'glossary.jsonl', host: 'islamic-content.com', variable: 'PRIVATE_GLOSSARY_SHA256' },
};
const sha = value => createHash('sha256').update(value).digest('hex');

async function readJson(file) {
  return JSON.parse(await readFile(file, 'utf8'));
}

function hostOf(url) {
  try { return new URL(url).hostname; } catch { return null; }
}

/** complete when traversal ended and every page of this host was collected or is a listing. */
export function sourceStatus(manifest, report, host, records) {
  if (manifest.complete === true) return 'complete';
  if (records === 0 || !Array.isArray(report) || manifest.remaining_pages !== 0) return 'partial';
  const rows = report.filter(row => hostOf(row.url) === host);
  const clean = rows.every(row => row.status === 'collected' || LISTING_REASONS.has(row.reason));
  return clean ? 'complete' : 'partial';
}

export async function verifyRun(runDir, source) {
  const { file, host } = SOURCES[source];
  const manifest = await readJson(path.join(runDir, 'manifest.json'));
  if (manifest.format_version !== 2) throw new Error(`${source}: run manifest is not format_version 2`);
  if (manifest.authority_event !== AUTHORITY) throw new Error(`${source}: run manifest authority mismatch`);
  const entries = (manifest.files ?? []).filter(item => item.file === file);
  if (entries.length !== 1) throw new Error(`${source}: run manifest must list ${file} exactly once`);
  const [entry] = entries;
  if (entry.source_host !== host) throw new Error(`${source}: run manifest host mismatch`);
  const bytes = await readFile(path.join(runDir, file));
  const lines = bytes.toString('utf8').split('\n').filter(line => line.length > 0);
  if (sha(bytes) !== entry.sha256) throw new Error(`${source}: ${file} sha256 differs from its run manifest`);
  if (bytes.length !== entry.bytes) throw new Error(`${source}: ${file} size differs from its run manifest`);
  if (lines.length !== entry.records) throw new Error(`${source}: ${file} record count differs from its run manifest`);
  if (entry.records === 0) throw new Error(`${source}: ${file} has no records`);
  let report = null;
  try { report = await readJson(path.join(runDir, 'report.json')); } catch { report = null; }
  return {
    file, source_host: host, records: entry.records, bytes: entry.bytes, sha256: entry.sha256,
    status: sourceStatus(manifest, report, host, entry.records),
    run: { mode: manifest.mode ?? null, generated_at: manifest.generated_at ?? null,
      visited: manifest.visited ?? null, remaining_pages: manifest.remaining_pages ?? null },
  };
}

export async function buildShortIndex({ output, runs }) {
  const sources = Object.keys(runs).filter(source => runs[source]);
  if (sources.length === 0) throw new Error('Pass --glossary and/or --bayyinat run directories');
  await mkdir(output, { recursive: true });
  const files = [];
  const summary = {};
  for (const source of sources) {
    const verified = await verifyRun(runs[source], source);
    await copyFile(path.join(runs[source], verified.file), path.join(output, verified.file));
    const { run, ...entry } = verified;
    files.push(entry);
    summary[source] = { ...entry, run };
  }
  const manifest = {
    format_version: 2,
    mode: 'short-index-build',
    authority_event: AUTHORITY,
    generated_at: new Date().toISOString(),
    complete: files.every(entry => entry.status === 'complete'),
    sources: Object.fromEntries(sources.map(source => [source, {
      status: summary[source].status, records: summary[source].records, ...summary[source].run }])),
    files,
    scope: 'owner-private; short excerpts only; no public redistribution approval',
  };
  await writeFile(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  return { manifest, summary };
}

function value(args, flag) {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const args = process.argv.slice(2);
  const output = value(args, '--output');
  if (!output || (!value(args, '--glossary') && !value(args, '--bayyinat'))) {
    console.log('node build-short-index.mjs --glossary RUN_DIR [--bayyinat RUN_DIR] --output OUT_DIR');
    process.exit(1);
  }
  const runs = {
    glossary: value(args, '--glossary') && path.resolve(value(args, '--glossary')),
    bayyinat: value(args, '--bayyinat') && path.resolve(value(args, '--bayyinat')),
  };
  const { manifest, summary } = await buildShortIndex({ output: path.resolve(output), runs });
  for (const [source, entry] of Object.entries(summary)) {
    console.log(`${source}: ${entry.records} records, ${entry.bytes} bytes, status ${entry.status}`);
    console.log(`${SOURCES[source].variable}=${entry.sha256}`);
  }
  console.log(`manifest complete: ${manifest.complete}` +
    (manifest.complete ? '' : ' (a partial source loads only with PRIVATE_SHORT_INDEX_ALLOW_PARTIAL=true)'));
}
