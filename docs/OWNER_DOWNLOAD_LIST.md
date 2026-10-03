# Per-item owner download list

Updated from owner late October 3 selection, planning event `d729c72249f924f9d0e64e3220f943b15b0b36037e5f35f02d4ad7743e102f26`.
**Only the owner downloads and places files. No agent downloads anything.**
Numbers and grading URLs are owner-supplied; specialist review remains pending.
Exact KFC package and edition-page URLs still await owner handoff. Pending is
not a download link. Permission and ingestion gates remain unchanged.

## Original evidence files

Filenames below are proposed local targets, not assertions of publisher filenames.
Keep original names in the handoff metadata. If the selected file format differs,
record its actual extension and update the exact target path before acquisition.

| Item | Exact page/file URL | Target filename | Exact path relative to repo root |
|---|---|---|---|
| KFC Hafs package: 2:255; 51:56-60; 35:28; 112:1-4; no tafsir | Pending exact KFC package URL/version | SELECTED_HAFS_PACKAGE.json | `data/raw/kfc-mushaf/SELECTED_HAFS_PACKAGE.json` |
| Bukhari 8 edition text | Pending exact selected edition file/page | BUKHARI_8.html | `data/raw/sahih-bukhari/BUKHARI_8.html` |
| Bukhari 8 Dorar grading | https://dorar.net/h/JDqeTpYd | BUKHARI_8_GRADING.html | `data/raw/dorar-hadith/BUKHARI_8_GRADING.html` |
| Bukhari 7556 edition text | Pending exact selected edition file/page | BUKHARI_7556.html | `data/raw/sahih-bukhari/BUKHARI_7556.html` |
| Bukhari 7556 Dorar grading | https://dorar.net/h/f5wEbcxS | BUKHARI_7556_GRADING.html | `data/raw/dorar-hadith/BUKHARI_7556_GRADING.html` |
| Bukhari 63 edition text | Pending exact selected edition file/page | BUKHARI_63.html | `data/raw/sahih-bukhari/BUKHARI_63.html` |
| Bukhari 63 Dorar grading | https://dorar.net/h/QPGgH3Qa | BUKHARI_63_GRADING.html | `data/raw/dorar-hadith/BUKHARI_63_GRADING.html` |
| Bukhari 1399 edition text | Pending exact selected edition file/page | BUKHARI_1399.html | `data/raw/sahih-bukhari/BUKHARI_1399.html` |
| Bukhari 1399 Dorar grading | https://dorar.net/h/pUrPIlDN | BUKHARI_1399_GRADING.html | `data/raw/dorar-hadith/BUKHARI_1399_GRADING.html` |
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
verse reference they use. Bukhari 8 is the proposed altered-hadith base.
Canonical references are Bukhari numbers; displayed wording comes from the
edition file, Dorar supplies grading. The owner verified grader and source as
Bukhari on each page; exact grade text must come from the supplied file.

## Test-input-only files; never corpus

| Item | Exact page/file URL | Target filename | Exact path relative to repo root |
|---|---|---|---|
| ramadan-fake-01 input | Pending owner-selected exact Dorar fake-hadith page | RAMADAN_FAKE_01_INPUT.txt | `data/raw/test-inputs/RAMADAN_FAKE_01_INPUT.txt` |
| ramadan-fake-01 provenance | Same exact page; URL pending | RAMADAN_FAKE_01_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_01_SOURCE.html` |
| ramadan-fake-02 input | Pending owner-selected exact Dorar fake-hadith page | RAMADAN_FAKE_02_INPUT.txt | `data/raw/test-inputs/RAMADAN_FAKE_02_INPUT.txt` |
| ramadan-fake-02 provenance | Same exact page; URL pending | RAMADAN_FAKE_02_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_02_SOURCE.html` |
| ramadan-fake-03 input | Pending owner-selected exact Dorar fake-hadith page | RAMADAN_FAKE_03_INPUT.txt | `data/raw/test-inputs/RAMADAN_FAKE_03_INPUT.txt` |
| ramadan-fake-03 provenance | Same exact page; URL pending | RAMADAN_FAKE_03_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_03_SOURCE.html` |
| ramadan-fake-04 input | Pending owner-selected exact Dorar fake-hadith page | RAMADAN_FAKE_04_INPUT.txt | `data/raw/test-inputs/RAMADAN_FAKE_04_INPUT.txt` |
| ramadan-fake-04 provenance | Same exact page; URL pending | RAMADAN_FAKE_04_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_04_SOURCE.html` |
| ramadan-fake-05 input | Pending owner-selected exact Dorar fake-hadith page | RAMADAN_FAKE_05_INPUT.txt | `data/raw/test-inputs/RAMADAN_FAKE_05_INPUT.txt` |
| ramadan-fake-05 provenance | Same exact page; URL pending | RAMADAN_FAKE_05_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_05_SOURCE.html` |
| altered-hadith-01 input | Pending specialist-supplied file; no publisher URL for a mutation | ALTERED_HADITH_01_INPUT.txt | `data/raw/test-inputs/ALTERED_HADITH_01_INPUT.txt` |
| altered-verse-01 input | Pending specialist-supplied file; no publisher URL for a mutation | ALTERED_VERSE_01_INPUT.txt | `data/raw/test-inputs/ALTERED_VERSE_01_INPUT.txt` |
| disputed-fiqh-01 question | Pending specialist-supplied file; exact position URLs recorded above | DISPUTED_FIQH_01_INPUT.txt | `data/raw/test-inputs/DISPUTED_FIQH_01_INPUT.txt` |

The five Ramadan inputs expect CANNOT_CONFIRM with referral; never corpus.
Altered-word verdicts stay open: interim abstention/referral and no executable
fixtures until specialist answers and approves the altered text.

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
