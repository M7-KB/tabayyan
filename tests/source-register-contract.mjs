import assert from 'node:assert/strict';

export const legalDomains = new Set([
  'quran', 'hadith', 'tafsir', 'aqeeda', 'fiqh', 'seerah', 'glossary', 'faq',
  'quran_translation',
]);

export function registerRows(markdown) {
  const lines = markdown.split(/\r?\n/);
  const start = lines.findIndex((line) => line.startsWith('| Source id |'));
  assert.ok(start >= 0, 'Source register table is required');
  const cells = (line) => line.trim().slice(1, -1).split('|').map((cell) => cell.trim());
  const headers = cells(lines[start]);
  for (const name of ['Source id', 'domain', 'use', 'license', 'license_url']) {
    assert.ok(headers.includes(name), `Explicit ${name} column is required`);
  }
  assert.equal(new Set(headers).size, headers.length, 'Duplicate column header');
  const rows = [];
  for (const line of lines.slice(start + 2)) {
    if (!line.startsWith('|')) break;
    const values = cells(line);
    assert.equal(values.length, headers.length, 'Register row column count');
    const row = Object.fromEntries(headers.map((header, index) => [header, values[index]]));
    for (const name of ['Source id', 'use', 'license', 'license_url']) {
      assert.ok(row[name], `Missing ${name} for ${row['Source id']}`);
    }
    assert.ok(legalDomains.has(row.domain), `Illegal domain ${row.domain}`);
    assert.ok(row.license_url === 'pending' || /^https:\/\/\S+$/.test(row.license_url),
      'license_url must be HTTPS or pending');
    rows.push(row);
  }
  assert.ok(rows.length > 0, 'Source register must not be empty');
  assert.equal(new Set(rows.map((row) => row['Source id'])).size, rows.length,
    'Register: duplicate source ID');
  return rows;
}
