# Oct 4 minimal corpus clearance checklist

Updated from the owner's late October 3 selection, planning event `d729c72249f924f9d0e64e3220f943b15b0b36037e5f35f02d4ad7743e102f26`.
This supersedes the earlier proposed verse and Sahihayn selection. Specialist
review remains pending. Selection grants no licence or runtime approval.
Only human-provided files in data/raw/ may become corpus input; no scraping.
See [challenge brief](challenge-brief.md), [SOURCES.md](../SOURCES.md) and [SPEC](../SPEC.md).

## Owner-selected minimum

| Candidate | Proposed size | Selection and evidence required | Demo purpose |
|---|---|---|---|
| `kfc-mushaf` | 2:255; 51:56-60; 35:28; 112:1-4 (11 verses) | KFC file only, no tafsir. Exact package/version, unchanged text, references and package-specific permission required. Specialist review pending. | Verbatim verse matching; altered-verse verdict remains open, interim abstention/referral, no executable fixture. |
| `sahih-bukhari` | Bukhari 8, 7556, 63, 1399 | Exact edition files/pages and permission. Canonical ref is the Bukhari number. Displayed wording comes from the edition file; matching Dorar pages supply grading. | Sourced hadith matching after all gates pass. |
| `dorar-hadith` | One matching grading record per selected hadith | Verbatim grading, named grader, grading reference, exact grading URL and separate permission. Do not infer grading from a collection title. | Required grading provenance for every displayed hadith. |
| `jamhara-glossary` | Three terms: Tawhid, Sharia, Worship | Exact Arabic entries and publisher-supplied English equivalents, source/reference and permission for each selected item. Tawhid entry: https://islamic-content.com/dictionary/word/3529 . Other exact entry and English URLs remain pending owner selection. | T07/T08 and the culturally loaded term path in T12. |

## Exact owner-supplied grading links

| Canonical reference | Dorar grading URL |
|---|---|
| Bukhari 8 | https://dorar.net/h/JDqeTpYd |
| Bukhari 7556 | https://dorar.net/h/f5wEbcxS |
| Bukhari 63 | https://dorar.net/h/QPGgH3Qa |
| Bukhari 1399 | https://dorar.net/h/pUrPIlDN |

The owner reports verifying grader and source as Bukhari on each page. This is
owner-supplied metadata, not agent website verification. Copy exact grade,
grader and reference only from supplied files; never infer a grade.

## Test inputs only; never corpus

- Five distinct Ramadan claims from Dorar's fake-hadith section, slots
  ramadan-fake-01 through ramadan-fake-05. Exact wording/page URLs await owner
  files. Expect CANNOT_CONFIRM with official referral, ready-to-ask question and
  exactly two verification lines. These are never authentic corpus evidence.
- Propose Bukhari 8 as the base of altered-hadith-01. The specialist approves
  the exact altered text, level and verdict; no mutation is authored here.
- Select altered-verse-01 from the KFC subset with specialist review. Both
  altered-word verdicts stay open: abstention with referral until answered,
  no executable fixtures, and no claim of correction coverage.
- Glossary and disputed-fiqh requests remain pending. This selection does not
  establish complete brief coverage or a passing 80-100-item evaluation.

## Owner file handoff

The [specialist selection and safety test plan](SPECIALIST_SELECTION_TEST_PLAN.md)
records five Ramadan test-input-only slots and separate altered-word questions.
They are not corpus additions. The [per-item owner download list](OWNER_DOWNLOAD_LIST.md)
defines target filenames and exact local paths; missing item URLs remain pending
owner handoff or specialist selection as indicated. The owner performs every download and sends the handoff.

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
