# Owner-run private source collection (R1)

Authority: owner event `d3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f`
in planning, 2026-10-05. O1 approves bayenat.net as the Osul Center web edition
of Bayyinat; O2 permits short glossary definitions and supplied translations,
verbatim with attribution and a link. The owner cites the organizers' 2026-10-03
reply. Public redistribution is not authorized here; written evidence is R2 work.

## Exact PowerShell command

Node 20+ and npm required. This path is the prepared R1 worktree; after merging,
the owner can use the main checkout instead. No Python, AI calls or keys needed.

```powershell
Set-Location 'C:\Users\m7md2\.buzz\REPOS\tabayyan-owner-collector-20261005'
npm.cmd ci --prefix tools/source-collector --ignore-scripts
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
$collectionOutput = Join-Path (Get-Location) ('data\private\source-collection-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
node tools/source-collector/collect.mjs --owner-run --output $collectionOutput --max-pages 10000
$collectionExit = $LASTEXITCODE
Write-Host "Output: $collectionOutput; exit: $collectionExit"
Get-Content -LiteralPath (Join-Path $collectionOutput 'manifest.json')
```

Exit 0: traversal ended, both sources produced records, no request or recognized
content-page extraction failed. Only recognized listing pages may be skipped.
Exit 2: partial output; keep for inspection, do not deploy as a complete index.
Exit 1: startup/output failure. Existing directories are never overwritten.
Output stays under ignored `data/private/`; never force-add it to Git.

## Collection and handoff

One global limiter spaces request starts at least 1 second apart. Only HTTPS
bayenat.net pages and islamic-content.com/dictionary pages are fetched. Listings
are followed for discovery. Bayyinat routes are restricted to question/answer,
doubt, category/topic paths, plus the Arabic home root (`/` or `/ar/`). Only Arabic
pages are collected: each page must declare an Arabic document language
(`<html lang="ar…">`) whatever its URL. Undeclared or non-Arabic pages are not
followed and yield no record. Language prefixes other than `/ar` are refused. Unknown route shapes
are refused and require a parser/route update from owner-supplied HTML.
Assets, unrelated dictionary paths, authentication
pages, arbitrary query parameters and redirects are refused. No retries or
anti-bot workarounds. Each request has a 30-second timeout and 4 MiB body limit;
the crawl stops at 10,000 pages (`--max-pages` overrides). This tool is never
an API/build/startup dependency. Agents must not run live collection.

- `bayyinat.jsonl`: id, url, title, similar_phrasings, short_answer, keywords,
  category. Optional missing metadata stays empty, never inferred.
- `glossary.jsonl`: id, url, term_ar, definition_short, translations.
  Missing publisher translations stay empty, never machine-translated.
- `manifest.json`: SHA-256, actual UTF-8 byte lengths and counts for JSONL and
  private HTML snapshots; authority event, timestamp, traversal status.
- `report.json`: page URLs and collection/skip/failure reasons without page text.
- `html/`: private publisher HTML snapshots for extraction inspection. Never
  display full pages or upload these snapshots/records to chat/public Git.

DOM text extraction decodes entities and standardizes HTML layout spaces/newlines.

Record identity is URL path plus its unchanged query. Only `page`, and `lang` or `language` set to `ar`,
are allowed query parameters. Other language selectors (for example `lang=en` or
`/en/` prefixes) are refused rather than collected, and query parameters are never
stripped to pretend that different content is identical.
No Arabic letters or diacritics are folded. Hashes include JSONL newline bytes.
R2 must verify hashes and validate records. Records alone do not authorize UI
evidence, embedded scripture, hadith gradings or level-D answers.

## Live coverage awaits the owner run

No source HTML was supplied in data/raw/ when R1 was built. Tests use synthetic
non-religious content. The extractor requires an h1 title and an explicit short
bounded section container. Bare headings with following sibling paragraphs are
ambiguous and refused. Containers with nested blocks or detailed headings are
refused too. It never substitutes a detailed answer or the whole
page. Dictionary entries must use `/dictionary/word/<id>`; supplied translations
must be two-column publisher rows inside an explicit translations container.
Different markup or client-rendered pages may yield no records. Exit 0 does
not establish comprehensive source coverage.

Report only record counts and skipped/failed reason counts. If short fields are
missing, place representative owner-saved HTML in data/raw/ with its original URL
for parser adaptation. Inspect sample short fields against the publisher before
R2 handoff. Do not accept a large skipped-page count as complete coverage.
For navigation gaps, use `--seeds <UTF-8-file>` with exact approved page URLs,
one per line, and a new output directory. No guessed references or wording.

## Offline tests and code licences

```powershell
npm.cmd ci --prefix tools/source-collector --ignore-scripts
npm.cmd test --prefix tools/source-collector
node --test tests/*.test.mjs
```

parse5 7.3.0 is MIT; entities is BSD-2-Clause. Installed package licence files
carry the upstream notices. These code licences are separate from the content
permissions in SOURCES.md.
