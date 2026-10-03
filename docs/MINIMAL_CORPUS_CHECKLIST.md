# Oct 4 minimal corpus clearance checklist

Prepared for the owner's **2026-10-04 12:00 Riyadh** file-selection decision.
Authority: owner evening update, 2026-10-03, planning event
`c960d48e041c2476131ab9147e86ed542005aa6765018921490ea025ac6d1cb0`;
[challenge brief](challenge-brief.md), [source register](../SOURCES.md),
[manual acquisition manifest](DOWNLOAD_MANIFEST.md) and [SPEC](../SPEC.md).
Updated by the owner's late selection routed in build event
`401979dc9d4628f2a6dd59b09d6f923f1395147d707a5a2c3b3742e922e46b04`.
The selections below are owner-supplied, not independently verified by us.
Specialist review is pending; the handoff stays in OUTBOX and work proceeds.
This is a selection checklist, not a corpus artifact or permission grant.
Only files placed by humans in `data/raw/` may become corpus input. No scraping.

## Owner-selected minimum

| Candidate | Proposed size | Selection and evidence required | Demo purpose |
|---|---|---|---|
| `kfc-mushaf` | 2:255; 51:56-60; 35:28; 112:1-4 (11 verses) | Text from the human-provided KFC file only; no tafsir. Record exact package/version, unchanged Arabic text, surah:ayah, source URLs and package-specific permission. Owner selection; specialist review pending. | Verbatim verse match; a T11 mutation still needs specialist selection and approval. |
| `sahih-bukhari` | Bukhari numbers 8, 7556, 63, 1399 | Bukhari number is the canonical reference. Text comes only from the human-provided edition file; grading comes separately from Dorar. Record exact edition, book/page, source URL and edition-specific permission. | Sourced hadith matching; number 8 is proposed as the altered-word test base, pending specialist approval. |
| `dorar-hadith` | One matching grading record per selected hadith | Verbatim grading, named grader, grading reference, exact grading URL and separate permission. Do not infer grading from a collection title. | Required grading provenance for every displayed hadith. |
| `jamhara-glossary` | Three terms: Tawhid, Sharia, Worship | Exact Arabic entries and publisher-supplied English equivalents, source/reference and permission for each selected item. Tawhid entry: https://islamic-content.com/dictionary/word/3529 . Other exact entry and English URLs remain pending owner selection. | T07/T08 and the culturally loaded term path in T12. |

Owner-supplied Dorar codes: `JDqeTpYd`, `f5wEbcxS`, `QPGgH3Qa`, `pUrPIlDN`;
permalinks use `https://dorar.net/h/` plus the exact code. These codes and Bukhari
numbers have not been verified by us. Their per-item correspondence must be checked
against the human files before recording grading provenance; list order is not proof.
Muslim is removed from this selection and the owner download list.

This minimum is not a claim of complete brief coverage. Hadith texts and gradings
remain pending the human files, permission checks and specialist review. It does not cover all
history, disagreement or introductory explanation cases. Keep their missing-source
behavior explicit; do not describe this selection as a passing 80–100-item evaluation.

## Owner file handoff

The [specialist selection and safety test plan](SPECIALIST_SELECTION_TEST_PLAN.md)
adds five Ramadan claims from Dorar's fake-hadith section as test inputs only,
with CANNOT_CONFIRM and referral expected. Exact claims/pages remain owner-supplied
handoff fields; no wording or grading is invented. The earlier altered-hadith,
altered-verse and disputed-fiqh review questions remain separate.
They are not corpus additions. The [per-item owner download list](OWNER_DOWNLOAD_LIST.md)
defines target filenames and exact local paths; missing item URLs remain pending
owner file handoff. The owner performs every download. The specialist handoff
remains unsent in OUTBOX while the specialist is unavailable; no work waits on it.

1. Place only selected, permission-cleared source files in the manifest's `data/raw/`
   directories. Keep permission evidence with the source metadata. Unclear files remain
   excluded from ingestion and public commits, including derived excerpts and indexes.
2. Record exact filenames, edition/package, source URLs, references and permitted scope
   in SOURCES.md. Permission must cover the intended raw/derived publication and public
   application display; record any restriction explicitly. Confirm the grading source
   separately from the hadith edition.
3. Robin prepares records with unchanged text, checksums, source IDs, level, licence and
   complete grading metadata. English text stays separate, with its own checksum.
4. Obtain independent review and Sharia specialist approval in the content PR. Pending
   approval may be checked offline with `python -m corpus.validate --allow-pending-review`
   after licence clearance; it is never runtime approval. Runtime uses only approved
   records passing `python -m corpus.validate` and the loader gates.

## Required behavior if a source is not cleared

These are implementation and evaluation requirements, not claims that the deployed
health-only API already implements verification.

| Missing clearance | Required demo behavior |
|---|---|
| Qur'an package or selected verse | Do not show a source quote or corrected verse. Abstain with CANNOT_CONFIRM, the configured official referral, a ready-to-ask question and two verification lines. T11's sourced correction remains blocked; do not count it as passed. |
| Bukhari edition or its grading source | Exclude the affected hadith. Never show it with an inferred grade or a grade from an uncleared source. If no other cleared matching evidence exists, use CANNOT_CONFIRM with referral and verification guidance. |
| Jamhara glossary | No copied definition, translated definition or generated substitute. Luffy owns the requested T07/T08 fallback: English equivalent plus an outbound entry link. A permitted, verified equivalent and its provenance must be identified before display; the fallback does not create a SUPPORTED definition or close the full sourced-explanation requirement. Missing verified equivalent or exact entry URL remains explicit and abstains. |
| No cleared and specialist-approved records | Demonstrate the abstention/referral path only. Report empty corpus and unmet source/content gates; do not claim sourced verification or a passing evaluation. |

Level D always remains general information plus referral, regardless of corpus readiness.
Any future misquote notice uses the same retrieved, verbatim provenance object required
for a SUPPORTED quote, including complete hadith grading provenance when applicable
(owner decision 3a). No uncleared text can enter that object.

Product notices and cards stay Arabic and disclose AI use and that the tool is not a fatwa.
The current API health response and screenshots establish deployment evidence only;
composer, source gates and the above fallback require their own end-to-end verification.
