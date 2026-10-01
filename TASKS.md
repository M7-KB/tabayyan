# TASKS.md — Tabayyan (تبيّن)

Status: draft for owner review. **No task here is assigned yet** — the owner reviews the plan first.
Owner of this document: @Luffy (lead)
Last updated: 2026-10-01
Times are Riyadh. Build window: Oct 4 09:00 → Oct 6 23:59.

Conventions, from `AGENTS.md`: one task = one branch = one PR, small PRs, tests ship with code, the README section you touched is updated in the same PR, every PR goes to @Nami, never push to main, never merge. Corpus and test-set PRs also need Sharia specialist approval.

Estimates are in agent-hours. `AT` = acceptance test: what must be demonstrably true for the PR to be mergeable.

---

## Pre-work (before Oct 4) — allowed, and disclosed as `baseline`

Only work done Oct 4–6 is evaluated, and prior work must be disclosed. Everything in this section is tagged `baseline` in the repo and listed here so the disclosure is complete. Scope is deliberately limited to the test set, the source list, and planning — **no application code**.

See SPEC.md §8 question 3: whether offline corpus collection may also happen before Oct 4 is still an open question for the owner. P-04 below is written as collection-only and gated on that answer.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| P-01 | SPEC.md and TASKS.md | @Luffy | `plan/initial` | Both files cover scope, architecture, API contracts, the three data schemas, the A–D → state mapping, and acceptance criteria; PR open and reviewed by @Nami | 3h |
| P-02 | `eval/testset.jsonl` with all 12 required brief cases, in the §4.3 schema | @Robin | `data/testset-v0` | All 12 brief case ids present; each validates against the schema; `reviewed_by` set, or explicitly `pending` with the blocker named in the PR | 3h |
| P-03 | `SOURCES.md`: every approved source from the brief, with URL, how it is used, license and license URL | @Robin | `docs/sources-v0` | Every domain row in the brief's approved-references table appears; no source lacks a license field; no unapproved source present | 2.5h |
| P-04 | Approved-source allowlist + corpus collection notes (**collection only, no ingestion, pending SPEC.md §8 Q3**) | @Robin | `data/corpus-notes` | Allowlist derived from the brief and matching SOURCES.md; notes record what is collectable per domain and any licence limit found | 2h |
| P-05 | Repo hygiene: `.gitignore` for keys and audio, secret scan of existing history, `baseline` tag | @Luffy | `chore/repo-hygiene` | Secret scan clean; `baseline` tag pushed; no audio or data files tracked outside `corpus/` and `eval/` | 1h |

Pre-work total: ~11.5h

---

## Oct 4 — day 1: the spine

Goal by 23:59: Arabic text in → claims out, with level classification, retrieval against a real corpus slice, and a card that renders. No gates yet, no polish.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-401 | API scaffold: FastAPI app, `GET /health`, settings, CORS, error envelope, `pytest` + `ruff` in CI | @Vegapunk | `feat/api-scaffold` | CI green; `GET /health` returns `status`, `corpus_version`, `corpus_items`, `build`; error envelope covered by a test | 2h |
| T-402 | Arabic normalizer + corpus loader + `corpus/validate.py` implementing all 7 validator rules in SPEC.md §4.2 | @Vegapunk | `feat/corpus-loader` | Unit tests prove: a hadith item with no grading is rejected; an unknown `source_id` is rejected; a checksum mismatch is rejected; a normalizer-drift item is rejected; normalizer is idempotent | 3h |
| T-403 | Corpus v0: enough verified items to cover the 12 brief cases — Qur'an (KFC text) + Sahihayn with dorar.net gradings | @Robin | `data/corpus-v0` | `validate.py` passes on every item; each of the 12 cases has at least one plausible target item, or is explicitly recorded as a case that must abstain; every `source_id` is in SOURCES.md | 4h |
| T-404 | Retrieval: normalization + BM25 over corpus v0, behind a `Retriever` interface | @Vegapunk | `feat/retrieval` | A fixture of 12 queries returns the expected `corpus_id` in the top 5 for every case that has a target; cases with no target return an empty result rather than a weak match | 3h |
| T-405 | Level classifier A/B/C/D: deterministic level-D rules first, model may raise but never lower, low confidence → more restrictive | @Vegapunk | `feat/level-classifier` | All 12 brief cases classify to their expected level; a unit test proves a model answer of "B" cannot override a rule-matched "D"; a test proves low confidence escalates restrictiveness | 2.5h |
| T-406 | Web scaffold: React + Vite, RTL, Arabic UI text, text input, transcript/extract review screen, AI-not-a-fatwa notice | @Usopp | `feat/web-scaffold` | Builds clean; `dir="rtl"` and `lang="ar"` set; the notice is present on the result view and covered by a test; no English in product-facing text | 3.5h |
| T-407 | Eval harness: reads `eval/testset.jsonl`, calls the API, checks hard assertions, writes a per-case report, fails on a missing brief case id | @Nami | `test/eval-harness` | Runs end to end against a stub API; report lists every case with pass/fail per hard assertion; removing a brief case id from the file makes the run fail | 2.5h |
| T-408 | Daily status post: done / in progress / blocked / risks | @Luffy | — | Posted in the channel by 23:00 | 0.5h |

Day 1 load: @Vegapunk 10.5h (**over budget — see risks**), @Robin 4h, @Usopp 3.5h, @Nami 2.5h, @Luffy 0.5h

---

## Oct 5 — day 2: cards and gates

Goal by 23:59: all three card states produced correctly, the hard gates enforced in code, the card UI rendering real responses, and the full test set running.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-501 | `POST /api/v1/extract`: claim segmentation + level classification + span offsets | @Vegapunk | `feat/extract-endpoint` | Spans map back to exact substrings of the input; a multi-claim Arabic paragraph yields separate claims; `max_claims` is honoured and `dropped_count` is accurate | 2.5h |
| T-502 | Card composer + state machine implementing the approved SPEC.md §5 table | @Vegapunk | `feat/card-composer` | Table-driven tests cover every row of §5, including level C with one position → CANNOT_CONFIRM, and level D with strong retrieval → CANNOT_CONFIRM; `abstained_reason` is non-null exactly when the state is CANNOT_CONFIRM | 3h |
| T-503 | Gates: verbatim match, scripture/explanation separation, hadith grading, two-line verify. A failing gate forces CANNOT_CONFIRM and is never repaired | @Vegapunk | `feat/response-gates` | Tests prove: a one-character-altered quote fails and the card drops to CANNOT_CONFIRM; a quoted span planted in `explanation_ar` fails; an ungraded hadith item is dropped and an emptied `evidence` drops the card; `gate_report` reflects each outcome | 3h |
| T-504 | `POST /api/v1/check` wired end to end, with `503 PIPELINE_DEGRADED` on any stage failure | @Vegapunk | `feat/check-endpoint` | A real Arabic input returns schema-valid cards; a forced stage failure returns 503 and never a guessed card | 2h |
| T-505 | Card UI: the three states, evidence block visually separate from explanation, source and grading visible without a click, the 2 verify lines, the referral block | @Usopp | `feat/card-ui` | Each state renders from a fixture; a test asserts the explanation and quote are in different containers; grading is shown for every hadith; RTL layout verified at mobile and desktop widths | 4h |
| T-506 | Corpus v1: tafsir (early sources / dorar), creed, general fiqh, seerah, glossary (islamic-content.com), Bayyinat Q&A; SOURCES.md completed with licenses | @Robin | `data/corpus-v1` | `validate.py` passes; G13 cross-check passes (corpus `source_id` set equals SOURCES.md set); every one of the 12 cases is covered or deliberately abstaining; Sharia specialist approval recorded or blocker named | 4h |
| T-507 | `POST /api/v1/link/fetch` — URL → readable text, returned for user review | @Usopp | `feat/link-input` | A fixture article yields readable Arabic text; a non-article URL returns `422 NO_READABLE_TEXT`; extracted text lands in the same editable review screen as a transcript | 2h |
| T-508 | First full eval run over all 12 cases; file one defect per failure with the case id | @Nami | `test/eval-run-d2` | Report committed under `eval/reports/`; every failure has an issue with the case id and the observed state; G1–G9 reported per gate | 2.5h |
| T-509 | Daily status post | @Luffy | — | Posted in the channel by 23:00 | 0.5h |

Day 2 load: @Vegapunk 10.5h (**over budget**), @Usopp 6h, @Robin 4h, @Nami 2.5h, @Luffy 0.5h

---

## Oct 6 — day 3: harden, deploy, submit

Goal by 23:59: deployed demo passing all gates on the live URL, plus the submission package. **Code freeze 18:00.** After the freeze only documentation, video, and deck work continues.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-601 | Deploy API to Render: config, CORS, rate limit, no-input logging confirmed | @Vegapunk | `ops/deploy-api` | Live `GET /health` returns the committed corpus version; a rate-limit test returns 429; deployed logs inspected and contain no input text, transcript, or claim text (G11) | 2h |
| T-602 | Deploy web to Cloudflare Pages, pointed at the live API, end-to-end smoke test | @Usopp | `ops/deploy-web` | Live URL runs Arabic text input → cards; notice visible; smoke steps written into the README | 2h |
| T-603 | Audio input (P1): `POST /api/v1/transcribe`, ≤ 3 min limit, user reviews and edits the transcript before anything downstream runs | @Vegapunk | `feat/audio-input` | A 2-min Arabic clip returns an editable transcript; a 4-min clip returns `413 AUDIO_TOO_LONG`; a test proves the pipeline cannot run on an unconfirmed transcript. **First to cut if behind at 12:00.** | 3h |
| T-604 | README: run and setup docs, architecture summary, privacy statement, AI-disclosure statement, source-verification documentation | @Robin | `docs/readme-run-setup` | A clean clone can be run from the README alone by someone who has not seen the repo; the privacy and AI-disclosure statements are present; source verification is documented (submission requirement) | 2.5h |
| T-605 | Full eval + safety regression on the **live** demo: all 12 cases, G1–G15, sign-off | @Nami | `test/eval-final` | Report committed; every one of G1–G15 marked pass with evidence; any fail is escalated to @Luffy and the owner before 18:00 | 3h |
| T-606 | Secret scan over full history, dependency licence list, final repo hygiene | @Luffy | `chore/submission-hygiene` | Scan clean on all history; licence list committed; no user data or keys anywhere in the tree (G12) | 1h |
| T-607 | Demo video ≤ 2 min + deck (problem, solution, how it works, added value, technologies, results, continuation plan, screenshots) | @Usopp + @Robin | `docs/demo-assets` | Video under 2:00 and recorded against the live demo; deck covers all seven required sections | 3h |
| T-608 | Submission via the portal; keep the confirmation. Fallback: email info@IslamicAIch.org with proof of attempt and entry number | @Luffy | — | Confirmation saved and posted in the channel before 23:00, not 23:59 | 1h |
| T-609 | Final status post: what shipped, what was cut, known limits | @Luffy | — | Posted in the channel | 0.5h |

Day 3 load: @Vegapunk 5h, @Usopp 5h + shared 3h, @Robin 2.5h + shared 3h, @Nami 3h, @Luffy 2.5h

---

## Dependencies

```
P-02 testset ──────────────────────► T-407 harness ──► T-508 ──► T-605
P-03 SOURCES ──► P-04 allowlist ──► T-403 corpus v0 ──► T-404 retrieval ──┐
T-401 scaffold ──► T-402 loader ──► T-404 ──► T-502 composer ──► T-503 gates ──► T-504 ──┐
T-405 classifier ──────────────────────────► T-502                                      │
T-406 web scaffold ──► T-505 card UI ◄── T-504 (fixtures unblock earlier) ───────────────┤
T-506 corpus v1 ──────────────────────────► T-508                                       │
                                                       T-601 + T-602 deploy ◄───────────┘
                                                                     └──► T-605 ──► T-607 ──► T-608
```

Hard sequencing rules:
- **SPEC.md §5 must be signed off before T-502 starts.** The state machine is the one thing we cannot rework on Oct 6.
- @Usopp works against committed JSON fixtures of the card schema, not against a live API. T-505 must not wait on T-504.
- T-403 must land before T-404 can be meaningfully tested; a stub corpus is acceptable for T-404's first commit but not for its PR.
- T-506 needs Sharia specialist approval, which is outside the team's control. See risks.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| @Vegapunk is at ~10.5h on both Oct 4 and Oct 5 — the real bottleneck | Day 2 slips, which pushes gates into Oct 6 | Move T-402 (corpus loader and validator) to @Robin, who owns the schema anyway, and T-407 stays with @Nami. If still over, cut T-507 link input on Oct 5 at 12:00. Decide at the Oct 4 status post, not later. |
| Sharia specialist unavailable | G14 cannot pass; corpus and test set stay `pending` | Escalated as blocking open question 2. Fallback: ship with `approved_by: pending` recorded honestly in SOURCES.md and the README, and say so in the demo rather than claim approval we do not have. |
| Level → state table not signed off before Oct 4 | T-502 and T-503 are blocked, which is most of day 2 | Escalated as blocking open question 1. If unanswered by Oct 4 12:00, @Vegapunk implements the table as a data-driven policy file so a change is a config edit, not a rewrite. |
| Corpus too thin, so most cases land on CANNOT_CONFIRM | Demo looks like it cannot answer anything | T-403 is scoped to the 12 cases specifically, not to breadth. Abstention is a correct outcome and we present it as one, but we need SUPPORTED and DISPUTED to appear at least once each in the demo. |
| Retrieval returns a weak match and the card claims support | Reliability failure — the worst outcome in the evaluation | Score floor below which retrieval returns empty; G2 verbatim gate; T-404 explicitly tests that a no-target case returns empty rather than a weak match. |
| LLM provider and keys undecided | Blocks T-405, T-501, and all generated text | Escalated as blocking open question 4. Classifier rules for level D need no model, so T-405 can start on rules alone. |
| Audio eats day 3 | Deploy and submission slip | T-603 is explicitly first to cut, with a 12:00 decision point. |
| Submission at 23:59 | Portal failure with no time to recover | T-608 targets 23:00, and the email fallback path is written into the task. |

---

## Not yet planned

Deliberately excluded from the 3-day window: embedding retrieval (SPEC.md P2), multi-language input beyond the brief's required non-Arabic case, caching, and any admin or corpus-editing UI. These belong to the continuation plan in the deck, not to the build.
