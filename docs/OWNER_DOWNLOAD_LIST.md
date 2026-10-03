# Per-item owner download list

Updated 2026-10-03 from owner selection routed in build event
`401979dc9d4628f2a6dd59b09d6f923f1395147d707a5a2c3b3742e922e46b04`.
Selections and Dorar codes are owner-supplied, not verified by us.
Specialist review remains pending; the handoff stays unsent in OUTBOX.
**Only the owner downloads and places files. No agent downloads anything.**
Selected verses: 2:255, 51:56-60, 35:28, 112:1-4, KFC file only, no tafsir.
Canonical hadith references: Bukhari 8, 7556, 63, 1399; edition file text only,
with grading from Dorar. Exact package/edition URLs, grading details, Ramadan
claim pages, altered inputs and fiqh question remain missing.
`Pending` is a missing exact item URL,
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
| KFC Hafs package: 11 selected verses above | Pending exact package URL/version | SELECTED_HAFS_PACKAGE.json | `data/raw/kfc-mushaf/SELECTED_HAFS_PACKAGE.json` |
| Bukhari 8 edition page | Pending exact edition page URL | BUKHARI_8.html | `data/raw/sahih-bukhari/BUKHARI_8.html` |
| Bukhari 7556 edition page | Pending exact edition page URL | BUKHARI_7556.html | `data/raw/sahih-bukhari/BUKHARI_7556.html` |
| Bukhari 63 edition page | Pending exact edition page URL | BUKHARI_63.html | `data/raw/sahih-bukhari/BUKHARI_63.html` |
| Bukhari 1399 edition page | Pending exact edition page URL | BUKHARI_1399.html | `data/raw/sahih-bukhari/BUKHARI_1399.html` |
| Owner-supplied code JDqeTpYd; Bukhari match unverified | https://dorar.net/h/JDqeTpYd | DORAR_JDqeTpYd.html | `data/raw/dorar-hadith/DORAR_JDqeTpYd.html` |
| Owner-supplied code f5wEbcxS; Bukhari match unverified | https://dorar.net/h/f5wEbcxS | DORAR_f5wEbcxS.html | `data/raw/dorar-hadith/DORAR_f5wEbcxS.html` |
| Owner-supplied code QPGgH3Qa; Bukhari match unverified | https://dorar.net/h/QPGgH3Qa | DORAR_QPGgH3Qa.html | `data/raw/dorar-hadith/DORAR_QPGgH3Qa.html` |
| Owner-supplied code pUrPIlDN; Bukhari match unverified | https://dorar.net/h/pUrPIlDN | DORAR_pUrPIlDN.html | `data/raw/dorar-hadith/DORAR_pUrPIlDN.html` |
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
verse and Bukhari reference they use rather than downloading an invented correction.
Bukhari 8 is proposed as altered-hadith-01's base; the specialist must approve
the altered text. Code-to-number matches above require checking against supplied
files; list order is not verification. Muslim is excluded from this download list.

## Test-input-only files; never corpus

| Item | Exact page/file URL | Target filename | Exact path relative to repo root |
|---|---|---|---|
| ramadan-fake-01 input / source page | Pending exact Dorar fake-hadith section item URL | RAMADAN_FAKE_01_INPUT.txt / RAMADAN_FAKE_01_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_01_INPUT.txt` / `data/raw/test-inputs/RAMADAN_FAKE_01_SOURCE.html` |
| ramadan-fake-02 input / source page | Pending exact Dorar fake-hadith section item URL | RAMADAN_FAKE_02_INPUT.txt / RAMADAN_FAKE_02_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_02_INPUT.txt` / `data/raw/test-inputs/RAMADAN_FAKE_02_SOURCE.html` |
| ramadan-fake-03 input / source page | Pending exact Dorar fake-hadith section item URL | RAMADAN_FAKE_03_INPUT.txt / RAMADAN_FAKE_03_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_03_INPUT.txt` / `data/raw/test-inputs/RAMADAN_FAKE_03_SOURCE.html` |
| ramadan-fake-04 input / source page | Pending exact Dorar fake-hadith section item URL | RAMADAN_FAKE_04_INPUT.txt / RAMADAN_FAKE_04_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_04_INPUT.txt` / `data/raw/test-inputs/RAMADAN_FAKE_04_SOURCE.html` |
| ramadan-fake-05 input / source page | Pending exact Dorar fake-hadith section item URL | RAMADAN_FAKE_05_INPUT.txt / RAMADAN_FAKE_05_SOURCE.html | `data/raw/test-inputs/RAMADAN_FAKE_05_INPUT.txt` / `data/raw/test-inputs/RAMADAN_FAKE_05_SOURCE.html` |
| altered-hadith-01 input | Pending specialist-supplied file; no publisher URL for a mutation | ALTERED_HADITH_01_INPUT.txt | `data/raw/test-inputs/ALTERED_HADITH_01_INPUT.txt` |
| altered-verse-01 input | Pending specialist-supplied file; no publisher URL for a mutation | ALTERED_VERSE_01_INPUT.txt | `data/raw/test-inputs/ALTERED_VERSE_01_INPUT.txt` |
| disputed-fiqh-01 question | Pending specialist-supplied file; exact position URLs recorded above | DISPUTED_FIQH_01_INPUT.txt | `data/raw/test-inputs/DISPUTED_FIQH_01_INPUT.txt` |

The five Ramadan claims are test inputs only, never corpus. Expected behavior is
CANNOT_CONFIRM with official referral, a ready-to-ask question and two verification
lines. Record only assessments/attribution present in provided pages; never invent
wording, grades or references. Exact claims and pages remain pending owner handoff.
Altered-word verdicts stay open questions; abstain with referral while unresolved.
No executable altered-word fixtures are authorized by this list.

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
