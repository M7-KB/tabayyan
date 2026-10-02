# P-02 required brief cases

Baseline pre-work, 2026-10-02. Twelve review records, T01–T12, following **plan/initial at e157ecf, SPEC §4.3–4.4**, not the older main schema. All records have `reviewed_by: pending`, `needs_sharia_review: true`. State expectations live in `expect.state`; source requirements live in `expect.required_evidence_domains` / `required_corpus_ids` and the target URLs in `notes_en`. No fabricated religious answer, grade or citation is included.

The four owner-fixed outcomes are unchanged: T01/T11 SUPPORTED + CONTRADICTS; T05 CANNOT_CONFIRM + LEVEL_D_PERSONAL_CASE; T06 CANNOT_CONFIRM + NO_MATCHING_EVIDENCE. Other level/state choices are draft proposals requiring specialist approval.

## Readiness and coverage

**This is not a complete runnable evaluation set or a passing G9 claim.** No corpus is present. Evidence-bearing cases need human-provided, licence-cleared, specialist-approved records and exact corpus ids before evaluation. An empty id array is not evidence and is not permission to accept an arbitrary record. The corpus-fixture binding must be recorded in this PR before approval.

| Case | Preparation / decision |
|---|---|
| T01 | Preserve brief text and owner-fixed contradicted state; KFC evidence fixture pending. |
| T02 | Introductory Bayyinat evidence target; exact passage pending. |
| T03 | Choose the spec's permitted abstention branch with a no-matching-evidence fixture. No historical position invented. A later DISPUTED variant requires ≥2 sourced positions. |
| T04 | Question about disagreement, level B; approved ijtihad glossary record pending. |
| T05 | Personal marriage question; referral only, even with strong retrieval. |
| T06 | No matching authentic hadith fixture as required by the brief; no narration generated. |
| T07/T08 | Require populated `card.term` and the approved English equivalent; glossary pair pending. Harness must explicitly check these outputs, not count prose review as automated verification. |
| T09 | Replace unspecified topic with the general concept ijtihad and actual hostile wording. Neutral wording is in notes; harness must compare both and assert tone leaves level/state unchanged. Proposed presupposition correction, pending review. |
| T10 | Keep the brief's unresolved subject. Choose NO_CHECKABLE_CLAIM rather than invent a disputed issue or consensus. Specialist reviews this departure from the proposed DISPUTED branch. |
| T11 | **Blocked placeholder.** Owner must supply a KFC verse; construct one explicitly labelled adversarial mutation from that file, then bind the corrected verse's exact corpus id/reference. No source text supplied, so no verse/misquote authored. Placeholder must fail readiness; never silently skip or count it as a passed test. |
| T12 | Concrete English Sharia question from the brief's glossary sample; require `card.term` and `explanation_en`. Approved Arabic/English glossary pair pending. |

T11 is the immediate input blocker. Remaining sourced-case prerequisites belong to P-04 → human files → corpus ingestion. The owner records anonymous specialist approval in the PR; only then change `reviewed_by` to `sharia-reviewer-1` in this same PR.

## Verification

Review JSON parseability, exact T01–T12 coverage and uniqueness, §4.3 key/type/enumeration consistency, state/alignment/reason/label relationships, level-D referral, all four owner-fixed expectations, English T12, term kinds T07/T08/T12, and explicit failure of T11 readiness. These are data checks only, not a model evaluation or application-code harness.

The requested first slice is 12 brief cases. The eventual 80–100 balanced evaluation items and team red-team cases remain separate work; this PR does not claim that coverage.
