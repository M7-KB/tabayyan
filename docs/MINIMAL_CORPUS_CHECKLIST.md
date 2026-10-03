# Oct 4 minimal corpus clearance checklist

Prepared for the owner's **2026-10-04 12:00 Riyadh** file-selection decision.
Authority: owner evening update, 2026-10-03, planning event
`c960d48e041c2476131ab9147e86ed542005aa6765018921490ea025ac6d1cb0`;
[challenge brief](challenge-brief.md), [source register](../SOURCES.md),
[manual acquisition manifest](DOWNLOAD_MANIFEST.md) and [SPEC](../SPEC.md).
This is a proposed small selection, not a corpus artifact or permission grant.
Only files placed by humans in `data/raw/` may become corpus input. No scraping.

## Proposed minimum

| Candidate | Proposed size | Selection and evidence required | Demo purpose |
|---|---|---|---|
| `kfc-mushaf` | One exact Hafs text package; initially index a small specialist-selected verse subset | Exact package/version, unchanged Arabic text, surah:ayah references, source URLs and package-specific permission. Specialist selects verse IDs; none is invented here. | Verbatim verse match and a corrected misquote with complete provenance (T11). |
| `sahih-bukhari` | Two specialist-selected hadith records | Exact edition text, collection + number, source URL and edition-specific permission. Separate matching Dorar records for each item. | Sourced hadith matching. |
| `sahih-muslim` | Two specialist-selected hadith records | Same per-item requirements as Bukhari, for the selected Muslim edition. | Sourced hadith matching across both collections. |
| `dorar-hadith` | One matching grading record per selected hadith | Verbatim grading, named grader, grading reference, exact grading URL and separate permission. Do not infer grading from a collection title. | Required grading provenance for every displayed hadith. |
| `jamhara-glossary` | Three terms: Tawhid, Sharia, Worship | Exact Arabic entries and publisher-supplied English equivalents, source/reference and permission for each selected item. Tawhid entry: https://islamic-content.com/dictionary/word/3529 . Other exact entry and English URLs remain pending owner selection. | T07/T08 and the culturally loaded term path in T12. |

Counts are an engineering proposal for a short demo, not a religious selection or a
claim of complete brief coverage. Hadith texts, numbers, gradings and verse selections
remain pending the human files and specialist review. The minimum does not cover all
history, disagreement or introductory explanation cases. Keep their missing-source
behavior explicit; do not describe this selection as a passing 80–100-item evaluation.

## Owner file handoff

The [specialist selection and safety test plan](SPECIALIST_SELECTION_TEST_PLAN.md)
adds five test-input-only selections requested in the owner's Oct 3 night update.
They are not corpus additions. The [per-item owner download list](OWNER_DOWNLOAD_LIST.md)
defines target filenames and exact local paths; missing item URLs remain pending
specialist selection. The owner performs every download and sends the handoff.

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
| Either hadith edition or its grading source | Exclude the affected hadith. Never show it with an inferred grade or a grade from an uncleared source. If no other cleared matching evidence exists, use CANNOT_CONFIRM with referral and verification guidance. |
| Jamhara glossary | No copied definition, translated definition or generated substitute. Luffy owns the requested T07/T08 fallback: English equivalent plus an outbound entry link. A permitted, verified equivalent and its provenance must be identified before display; the fallback does not create a SUPPORTED definition or close the full sourced-explanation requirement. Missing verified equivalent or exact entry URL remains explicit and abstains. |
| No cleared and specialist-approved records | Demonstrate the abstention/referral path only. Report empty corpus and unmet source/content gates; do not claim sourced verification or a passing evaluation. |

Level D always remains general information plus referral, regardless of corpus readiness.
Any future misquote notice uses the same retrieved, verbatim provenance object required
for a SUPPORTED quote, including complete hadith grading provenance when applicable
(owner decision 3a). No uncleared text can enter that object.

Product notices and cards stay Arabic and disclose AI use and that the tool is not a fatwa.
The current API health response and screenshots establish deployment evidence only;
composer, source gates and the above fallback require their own end-to-end verification.
