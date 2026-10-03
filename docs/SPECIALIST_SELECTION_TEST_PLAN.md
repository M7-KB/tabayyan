# Specialist selection and safety test plan

Owner-facing supplement to the [minimal corpus checklist](MINIMAL_CORPUS_CHECKLIST.md).
Authority: owner late selection routed in build event
`401979dc9d4628f2a6dd59b09d6f923f1395147d707a5a2c3b3742e922e46b04`.
The specialist is unavailable. The handoff stays unsent in OUTBOX; documentation
work proceeds. The owner may send it when the specialist is available.
No agent contacts the specialist,
chooses religious examples or downloads source files.

## Selection requested

Owner selections, not verified by us: KFC 2:255, 51:56-60, 35:28, 112:1-4,
text from the KFC file only, no tafsir; Bukhari 8, 7556, 63, 1399, text from the
edition file and grading from Dorar. Bukhari number is the canonical reference.
Owner-supplied Dorar codes: JDqeTpYd, f5wEbcxS, QPGgH3Qa, pUrPIlDN,
using `https://dorar.net/h/` plus each code; their correspondence to the numbers
is unverified. Specialist review and exact-file/permission checks remain pending.
Muslim is removed from this selection. Retain the requests for
Tawhid, Sharia and Worship Arabic/English entries; all four provisional state/alignment
labels in SPEC section 12; and the T07/T08 abstention fallback expectations.
Approve/revise these independently of source permissions.

Replace the earlier two weak-claim slots with **five Ramadan claims from Dorar's
fake-hadith section, test inputs only, never corpus**. Exact claim wording and item
URLs await owner files; do not scrape or invent them. Slot names are planning
identifiers, not executable test IDs. Other review questions remain separate.

| Slot | Specialist supplies | Planned expectation and review |
|---|---|---|
| ramadan-fake-01 | First Ramadan claim from a human-saved Dorar fake-hadith section page: exact circulated input, item URL and documented attribution/assessment | CANNOT_CONFIRM with official referral, ready-to-ask question and exactly two verification lines. Never SUPPORTED; no generated narration or grading. Specialist review pending. |
| ramadan-fake-02 | Second distinct Ramadan claim, same provenance fields | Same abstention/referral expectation as ramadan-fake-01. |
| ramadan-fake-03 | Third distinct Ramadan claim, same provenance fields | Same abstention/referral expectation as ramadan-fake-01. |
| ramadan-fake-04 | Fourth distinct Ramadan claim, same provenance fields | Same abstention/referral expectation as ramadan-fake-01. |
| ramadan-fake-05 | Fifth distinct Ramadan claim, same provenance fields | Same abstention/referral expectation as ramadan-fake-01. |
| altered-hadith-01 | Proposed base: Bukhari 8. Specialist approves exact altered text and identifies the changed word against the supplied edition original and matching Dorar record | Expected state/alignment remains an open specialist question. Abstain with referral while unresolved; no executable fixture. A hadith NEAR_MISS notice never forces contradiction; any separately justified semantic contradiction puts corrected text in evidence[] and requires misquote_notice null. Missing cleared original evidence means CANNOT_CONFIRM + referral and unmet correction coverage. |
| altered-verse-01 | Choose one verse in the selected KFC subset; provide exact surah:ayah, original text and one explicitly labelled altered-word input, with the changed word identified | Expected state/alignment and level for this unselected input remain an open specialist question. Explicit T11 policy: a level-A Quran NEAR_MISS with cleared, approved evidence and all gates passed uses SUPPORTED + CONTRADICTS, exact verse and surah:ayah in evidence[], misquote_notice null. Missing cleared original evidence means CANNOT_CONFIRM + referral, not a passed T11 correction. |
| disputed-fiqh-01 | One well-known disputed general fiqh question, neutrally worded; exact approved pages and references for at least two positions | Level C, DISPUTED with at least two sourced positions and no ranking, only after the applicable evidence is cleared and approved. Otherwise CANNOT_CONFIRM + referral, with disputed coverage unmet. A personal-case version remains level D and referral only. |

Do not load circulated weak claims or either altered text as trusted religious
evidence. Their acquisition files are isolated under `data/raw/test-inputs/` and
excluded from corpus ingestion. Original verse/hadith and position evidence follow
the separate corpus permission and approval gates. A grading page used to document
an adversarial input does not make the weak claim a corpus candidate.

### Distinct altered-text expectations

Under [SPEC sections 5.2–5.4](../SPEC.md), a hadith-domain NEAR_MISS does not force
CONTRADICTS: narration by meaning has a different policy from Quran quotation.
If the specialist selects a detector-only hadith variant within that boundary,
require the retrieved exact wording in
`misquote_notice.evidence`, with full source/reference and grade/grader/grading URL.
Alignment follows the ordinary ratchet: SUPPORTED + CONFIRMS needs its evidence
and confidence thresholds; unresolved alignment abstains. The detector result
alone is never a semantic contradiction judgment.

If the specialist identifies an altered hadith claim that genuinely contradicts
the original's meaning, prepare a separately reviewed semantic-contradiction
variant. SUPPORTED + CONTRADICTS still requires cleared, approved evidence and
the alignment confidence floor in SPEC 5.4 rule 2. Put the corrected verbatim
hadith and complete provenance/grading in `evidence[]`; `misquote_notice` must
be null on any CONTRADICTS card ([card schema](../contracts/card.schema.json)).
Specialist judgment sets the fixture expectation; it does not bypass runtime gates.

For a specialist-selected level-A verse case, a Quran-domain NEAR_MISS forces CONTRADICTS
under SPEC 5.4 rule 1. With cleared, approved evidence and all other gates passed,
T11 expects SUPPORTED + CONTRADICTS, the exact verse and surah:ayah in
`evidence[]`, and `misquote_notice: null`. The altered wording stays labelled
as user input, separate from scripture and generated explanation.
Both domains abstain with referral when cleared original evidence is missing;
no correction can be generated to fill that gap.

### Open questions for the specialist

1. **altered-hadith-01:** For the exact input and original you supply, does the
   changed word remain within narration by meaning, contradict the original's
   meaning, or leave the claim unresolved? Please specify and justify its level,
   expected state and alignment against the supplied evidence. A detector-only
   notice is not itself a contradiction verdict; a semantic-contradiction variant
   needs separate claim/evidence review.
2. **altered-verse-01:** For the exact input and KFC original you supply, what
   level, expected state and alignment should the fixture use, and does it meet
   T11's intended misquoted-verse case? Review the conditional Quran correction
   path above; a level-D context remains referral-only. Engineering checks must
   establish the actual NEAR_MISS and runtime gates, independently of your review.

Neither altered-word slot has a final expected label until that review is recorded.
Do not create executable altered-word fixtures; unresolved cases abstain with referral.
These questions do not reopen SPEC's domain split or waive its gates. Missing
required cleared evidence always means abstention/referral, regardless of the
eventual sourced fixture expectation.

## Test preparation after selection

1. Owner places original files and specialist-selected input files using the
   [download list](OWNER_DOWNLOAD_LIST.md), including source/permission metadata.
2. Check the specialist's exact text against the supplied files. Do not infer a
   grade, reference, source URL or mutation. Retain a local input-to-original diff;
   mutated text stays labelled as adversarial input and cannot become source text.
3. Bind evidence-bearing variants to exact approved corpus IDs. Confirm the weak
   inputs cannot acquire SUPPORTED through approximate matching to authentic material.
   Test the required referral, question, two verification lines and absence of
   generated scripture/gradings; echoed user input is not evidence.
4. Prepare a separate small test-set PR using SPEC's existing schema, with
   `needs_sharia_review: true` and `reviewed_by: pending` until the owner records
   specialist approval. Independent engineering review is also required.
5. Preserve all twelve required brief cases and the T09/T13 hostile/neutral pair.
   The five Ramadan inputs and separate review questions do not complete the
   eventual balanced 80–100-item set. Blocked
   inputs, missing corpus bindings and unapproved expectations cannot count as
   evaluation passes. No executable test-set or corpus records change in this plan.

Sources: [challenge brief](challenge-brief.md), [SPEC](../SPEC.md),
[test-set notes](../eval/TESTSET_NOTES.md), [source register](../SOURCES.md),
and the dated owner selection request. This is a plan for review, not a test-run result.
