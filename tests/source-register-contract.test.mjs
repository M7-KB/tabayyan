import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { registerRows } from './source-register-contract.mjs';

const markdown = readFileSync(new URL('../SOURCES.md', import.meta.url), 'utf8');
const fixture = '| Source id | domain | use | license | license_url |\n'
  + '|---|---|---|---|---|\n| fixture | quran | metadata only | pending | pending |\n';

test('register has explicit fields, unique IDs and valid domains', () => {
  registerRows(markdown);
});

test('missing or duplicate headers and malformed rows fail', () => {
  for (const name of ['Source id', 'domain', 'use', 'license', 'license_url']) {
    assert.throws(() => registerRows(fixture.replace(`| ${name} |`, '| other |')));
  }
  assert.throws(() => registerRows(fixture.replace('| license_url |', '| license |')));
  assert.throws(() => registerRows(fixture.replace('metadata only |', 'metadata only | extra |')),
    /column count/);
});

test('empty fields and duplicate IDs fail', () => {
  for (const value of ['fixture', 'metadata only', 'quran']) {
    assert.throws(() => registerRows(fixture.replace(`| ${value} |`, '| |')));
  }
  assert.throws(() => registerRows(fixture.replace('| pending | pending |', '| | pending |')),
    /Missing license/);
  assert.throws(() => registerRows(fixture.replace('| pending | pending |', '| pending | |')),
    /Missing license_url/);
  assert.throws(() => registerRows(fixture + fixture.split('\n')[2] + '\n'), /duplicate source ID/);
});

test('free-text domains and non-policy placeholder URLs fail', () => {
  assert.throws(() => registerRows(fixture.replace('| quran |', '| quran; text |')), /Illegal domain/);
  assert.throws(() => registerRows(fixture.replace('| pending | pending |', '| pending | unknown |')),
    /license_url/);
});
