# Specialist selection and safety test plan

Owner-facing supplement to the [minimal corpus checklist](MINIMAL_CORPUS_CHECKLIST.md).
Authority: the owner-provided selection request dated 2026-10-03.
The owner sends this request to the specialist. No agent contacts the specialist,
chooses religious examples or downloads source files.

## Owner selection for specialist review

Authority: late October 3 planning event `d729c72249f924f9d0e64e3220f943b15b0b36037e5f35f02d4ad7743e102f26`.
The [checklist](MINIMAL_CORPUS_CHECKLIST.md) records KFC-only 2:255, 51:56-60,
35:28, 112:1-4 (no tafsir), and Bukhari 8, 7556, 63, 1399 with exact
owner-supplied Dorar grading links. Displayed hadith text is from the edition;
canonical reference is the Bukhari number. Specialist review remains pending.
Tawhid/Sharia/Worship entries and the disputed general-fiqh request remain pending.
Retain T07/T08 fallback review and at least two sourced fiqh positions, no ranking.

Owner decision 4 on labels stands: provisional wording is enough for development;
final specialist wording is a P0 submission gate, not a merge gate. It does not
approve corpus records, licences or test-set content. No specialist is available
now; the owner seeks organizer referral. Keep the handoff in OUTBOX and continue
preparation without waiting.

## Five Ramadan inputs only; never corpus

Slots ramadan-fake-01 through ramadan-fake-05 are five distinct Ramadan claims
from Dorar's fake-hadith section. Exact text and page URLs await owner files.
Each expects CANNOT_CONFIRM with official referral, a ready-to-ask question and
exactly two verification lines. Never generate narration or grading. Files remain
isolated under data/raw/test-inputs/ and excluded from ingestion. These planning
slots add no executable records; eventual test content needs specialist review.

## Altered-word questions remain open

Propose **Bukhari 8** as the base for altered-hadith-01; the specialist approves
the exact altered text. Select altered-verse-01 from the KFC subset for review.
Until answered: **abstention with referral, no executable altered-word fixtures**.
Neither correction path counts as passed coverage. [SPEC 5.2-5.4](../SPEC.md)
retains the domain split and conditional runtime gates; this plan assigns no
final verdict and does not authorize those paths for unreviewed inputs.

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
   path in SPEC 5.4; a level-D context remains referral-only. Engineering checks must
   establish the actual NEAR_MISS and runtime gates, independently of your review.

Neither altered-word slot has a final expected label until that review is recorded.
These questions do not reopen SPEC's domain split or waive its gates. Missing
required cleared evidence always means abstention/referral, regardless of the
eventual sourced fixture expectation.

## Test preparation after selection

1. Owner places original files and specialist-selected input files using the
   [download list](OWNER_DOWNLOAD_LIST.md), including source/permission metadata.
2. Check the specialist's exact text against the supplied files. Do not infer a
   grade, reference, source URL or mutation. Retain a local input-to-original diff;
   mutated text stays labelled as adversarial input and cannot become source text.
3. Only after the altered-word questions are answered, bind evidence-bearing variants to exact approved corpus IDs. Confirm the Ramadan
   inputs cannot acquire SUPPORTED through approximate matching to authentic material.
   Test the required referral, question, two verification lines and absence of
   generated scripture/gradings; echoed user input is not evidence.
4. Do not add executable altered-word fixtures until answered. Prepare a separate small test-set PR using SPEC's existing schema, with
   `needs_sharia_review: true` and `reviewed_by: pending` until the owner records
   specialist approval. Independent engineering review is also required.
5. Preserve all twelve required brief cases and the T09/T13 hostile/neutral pair.
   The five Ramadan slots and separate altered-word/fiqh requests do not complete the eventual balanced 80–100-item set. Blocked
   inputs, missing corpus bindings and unapproved expectations cannot count as
   evaluation passes. No executable test-set or corpus records change in this plan.

Sources: [challenge brief](challenge-brief.md), [SPEC](../SPEC.md),
[test-set notes](../eval/TESTSET_NOTES.md), [source register](../SOURCES.md),
and the dated owner selection request. This is a plan for review, not a test-run result.
