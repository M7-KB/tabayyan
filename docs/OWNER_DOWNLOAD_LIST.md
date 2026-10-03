# Per-item owner download list

Prepared 2026-10-03 for the owner to fill after specialist selection.
Authority: the owner-provided acquisition request dated 2026-10-03.
**Only the owner downloads and places files. No agent downloads anything.**
No selected verse range, numbered hadith, grading permalink, altered input or fiqh
question has been supplied to this task. `Pending` is a missing exact item URL,
not a download link. Collection/search home pages in
[DOWNLOAD_MANIFEST.md](DOWNLOAD_MANIFEST.md) are starting points only; never substitute
them for an exact selected page. The known Tawhid Arabic page below is an existing
manifest reference, not a new download or verification.

## Original evidence files

Filenames below are proposed local targets, not assertions of publisher filenames.
Keep original names in the handoff metadata. If the selected file format differs,
record its actual extension and update the exact target path before acquisition.

| Item | Exact page/file URL | Target filename | Exact path relative to repo root |
|---|---|---|---|
| Selected KFC Hafs package | Pending exact package URL/version | SELECTED_HAFS_PACKAGE.json | `data/raw/kfc-mushaf/SELECTED_HAFS_PACKAGE.json` |
| Bukhari 1 selected numbered page | Pending specialist selection | BUKHARI_01.html | `data/raw/sahih-bukhari/BUKHARI_01.html` |
| Bukhari 2 selected numbered page | Pending specialist selection | BUKHARI_02.html | `data/raw/sahih-bukhari/BUKHARI_02.html` |
| Muslim 1 selected numbered page | Pending specialist selection | MUSLIM_01.html | `data/raw/sahih-muslim/MUSLIM_01.html` |
| Muslim 2 selected numbered page | Pending specialist selection | MUSLIM_02.html | `data/raw/sahih-muslim/MUSLIM_02.html` |
| Bukhari 1 matching Dorar grading | Pending exact matching permalink | BUKHARI_01_GRADING.html | `data/raw/dorar-hadith/BUKHARI_01_GRADING.html` |
| Bukhari 2 matching Dorar grading | Pending exact matching permalink | BUKHARI_02_GRADING.html | `data/raw/dorar-hadith/BUKHARI_02_GRADING.html` |
| Muslim 1 matching Dorar grading | Pending exact matching permalink | MUSLIM_01_GRADING.html | `data/raw/dorar-hadith/MUSLIM_01_GRADING.html` |
| Muslim 2 matching Dorar grading | Pending exact matching permalink | MUSLIM_02_GRADING.html | `data/raw/dorar-hadith/MUSLIM_02_GRADING.html` |
| Tawhid Arabic entry | https://islamic-content.com/dictionary/word/3529 | TAWHID_AR.html | `data/raw/jamhara-glossary/TAWHID_AR.html` |
| Tawhid publisher English entry | Pending exact supplied English URL | TAWHID_EN.html | `data/raw/jamhara-glossary/TAWHID_EN.html` |
| Sharia Arabic entry | Pending specialist selection | SHARIA_AR.html | `data/raw/jamhara-glossary/SHARIA_AR.html` |
| Sharia publisher English entry | Pending exact supplied English URL | SHARIA_EN.html | `data/raw/jamhara-glossary/SHARIA_EN.html` |
| Worship Arabic entry | Pending specialist selection | WORSHIP_AR.html | `data/raw/jamhara-glossary/WORSHIP_AR.html` |
| Worship publisher English entry | Pending exact supplied English URL | WORSHIP_EN.html | `data/raw/jamhara-glossary/WORSHIP_EN.html` |
| Disputed fiqh position 1 evidence | Pending exact approved page/reference | DISPUTED_FIQH_01_POSITION_01.html | `data/raw/dorar-fiqh/DISPUTED_FIQH_01_POSITION_01.html` |
| Disputed fiqh position 2 evidence | Pending exact approved page/reference | DISPUTED_FIQH_01_POSITION_02.html | `data/raw/dorar-fiqh/DISPUTED_FIQH_01_POSITION_02.html` |

Fiqh paths assume selected Dorar pages; if the specialist chooses an approved
school-book edition instead, update the source ID, exact URL, format, path and
permission register before collection. Add rows for any further positions.
The altered verse and hadith reuse their selected originals above; record which
verse and Sahihayn slot they use rather than downloading an invented correction.

## Test-input-only files; never corpus

| Item | Exact page/file URL | Target filename | Exact path relative to repo root |
|---|---|---|---|
| weak-01 circulated input | Pending specialist-selected page or supplied file; record `human supplied` if no web URL | WEAK_01_INPUT.txt | `data/raw/test-inputs/WEAK_01_INPUT.txt` |
| weak-01 documented grading | Pending matching approved grading permalink | WEAK_01_GRADING.html | `data/raw/test-inputs/WEAK_01_GRADING.html` |
| weak-02 circulated input | Pending specialist-selected page or supplied file; record `human supplied` if no web URL | WEAK_02_INPUT.txt | `data/raw/test-inputs/WEAK_02_INPUT.txt` |
| weak-02 documented grading | Pending matching approved grading permalink | WEAK_02_GRADING.html | `data/raw/test-inputs/WEAK_02_GRADING.html` |
| altered-hadith-01 input | Pending specialist-supplied file; no publisher URL for a mutation | ALTERED_HADITH_01_INPUT.txt | `data/raw/test-inputs/ALTERED_HADITH_01_INPUT.txt` |
| altered-verse-01 input | Pending specialist-supplied file; no publisher URL for a mutation | ALTERED_VERSE_01_INPUT.txt | `data/raw/test-inputs/ALTERED_VERSE_01_INPUT.txt` |
| disputed-fiqh-01 question | Pending specialist-supplied file; exact position URLs recorded above | DISPUTED_FIQH_01_INPUT.txt | `data/raw/test-inputs/DISPUTED_FIQH_01_INPUT.txt` |

For a human-authored input, a supplied file is the source: record that provenance
instead of inventing a page URL. Have the specialist identify altered words and
their original references. Extract only the exact selected input from saved pages;
do not treat commentary or circulation as authenticity evidence.

## Metadata accompanying every item

Place `OWNER_HANDOFF_METADATA.json` in `data/raw/` with one entry per actual file:
slot, exact repo-relative path, original filename, exact source/download URL (or
human-supplied provenance), selection/reference, edition/version, acquisition date,
source ID, permission evidence and permitted scope, and specialist review status.
For grading files also record the exact grade, grader, grading reference and permalink.
For mutations record the original slot/reference and the specialist-approved change.
Never insert missing religious fields from memory.

Raw paths stay ignored. Do not force-add raw text, test-input text or derived
excerpts to the public repository while redistribution is unresolved. Challenge
partner approval is recorded in [SOURCES.md](../SOURCES.md); it does not lift
the existing machine-readable ingestion or redistribution gates. This list is
ready for selection handoff, not a completed download manifest or permission grant.
