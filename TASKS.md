# TASKS.md — Tabayyan (تبيّن)

Status: approved by the owner on 2026-10-01. Assignments below are live.
Owner of this document: @Luffy (lead)
Last updated: 2026-10-01
Times are Riyadh. Build window: Oct 4 09:00 → Oct 6 23:59.
Owner decisions driving this plan: SPEC.md §10.

Conventions, from `AGENTS.md`: one task = one branch = one PR, small PRs, tests ship with code, the README section you touched is updated in the same PR, never push to main, never merge.
Review routing: request @Nami's review by @mention in the **#review** channel with the PR link; @Nami replies as a PR comment starting with `APPROVE` or `REQUEST CHANGES`. GitHub review requests do not work here — all agents share the owner's token.
Corpus and test-set PRs also need Sharia specialist approval; the owner obtains it and records it in the PR, and the `approved_by` / `reviewed_by` field is set in that same PR.

Estimates are in agent-hours. `AT` = acceptance test: what must be demonstrably true for the PR to be mergeable.

---

## Pre-work (before Oct 4) — allowed, and disclosed as `baseline`

Only work done Oct 4–6 is evaluated, and prior work must be disclosed. Everything in this section is tagged `baseline` in the repo and listed here so the disclosure is complete.

Owner decision 3 sets the boundary, and it is now settled: test set, `SOURCES.md`, allowlist, and corpus collection **and ingestion** are allowed before Oct 4. **No application code before Oct 4 09:00** — that includes the normalizer, the validator, the retriever and the eval harness. @Robin downloads nothing: @Robin writes the manifest, the owner places the files in `data/raw/`. The `baseline` tag is cut at the end of Oct 3.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| P-01 | SPEC.md and TASKS.md, updated with the owner's 2026-10-01 decisions | @Luffy | `plan/initial` | Both files cover scope, architecture, API contracts, the three data schemas, the A–D → state mapping with `alignment`, providers, the referral target, and acceptance criteria; all nine decisions reflected and listed in SPEC.md §10; reviewed by @Nami | 4h |
| P-02 | `eval/testset.jsonl` with all 12 required brief cases, in the §4.3 schema | @Robin | `data/testset-v0` | All 12 brief case ids present; each validates against the schema; the four fixed expectations in SPEC.md §4.3 are exactly as written (cases 1 and 11 → SUPPORTED + CONTRADICTS, case 6 → CANNOT_CONFIRM + NO_MATCHING_EVIDENCE, case 5 → CANNOT_CONFIRM + LEVEL_D_PERSONAL_CASE); `reviewed_by` set, or `pending` with the blocker named in the PR | 3h |
| P-03 | `SOURCES.md`: every approved source from the brief, with URL, how it is used, license and license URL | @Robin | `docs/sources-v0` | Every domain row in the brief's approved-references table appears; no source lacks a license field; no unapproved source present; each row states whether its licence permits redistributing the raw file | 2.5h |
| P-04 | Approved-source allowlist + **download manifest** for the owner: exact file, exact URL, per domain | @Robin | `data/corpus-notes` | Allowlist derived from the brief and matching SOURCES.md; the manifest names every file the owner must place in `data/raw/`, with its URL and licence note; no download or scrape performed by @Robin | 2h |
| P-05 | Repo hygiene: `.gitignore` for keys, audio and non-redistributable raw files; remove the reference-pack PDF from the tree; secret scan of existing history; `baseline` tag at the end of Oct 3 | @Luffy | `chore/repo-hygiene` | PDF no longer tracked; secret scan clean; `baseline` tag cut and pushed Oct 3; no audio or data files tracked outside `corpus/`, `eval/` and the permitted part of `data/raw/`. **The PDF stays in public history — see the risk row; the history rewrite is the owner's call and the owner's push.** | 1.5h |
| P-06 | Corpus v0 ingestion from `data/raw/` into `corpus/corpus.jsonl`: authored fields only, `baseline: true`, derived fields left empty for T-403 | @Robin | `data/corpus-v0-ingest` | Every item carries `corpus_id`, `domain`, `source_id`, `source_url`, `text_ar`, `ref`, `license`, `license_url`, `retrieved_at`, `baseline: true`, and `grading` for every hadith item; `text_normalized` and `checksum_sha256` are empty and recorded as T-403's job; every `source_id` is in the P-04 allowlist; no file in the PR is application code | 3h |

Pre-work total: ~16h, @Robin 10.5h over Oct 2–3, @Luffy 5.5h

---

## Oct 4 — day 1: the spine

Goal by 23:59: Arabic text in → claims out, with level classification, retrieval against a real corpus slice, and a card that renders. No gates yet, no polish.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-401 | API scaffold: FastAPI app, `GET /health`, settings read from env (incl. `OPENAI_API_KEY` and the model ids), CORS, error envelope, `pytest` + `ruff` in CI | @Vegapunk | `feat/api-scaffold` | CI green; `GET /health` returns `status`, `corpus_version`, `corpus_items`, `policy_version`, `policy_approved_by`, `build`; error envelope covered by a test; a test proves the app fails fast with a clear error when `OPENAI_API_KEY` is absent, and no key literal exists in the tree (G18) | 2.5h |
| T-402 | Arabic normalizer + corpus loader + `corpus/validate.py` implementing all 7 validator rules in SPEC.md §4.2 | @Robin | `feat/corpus-loader` | Unit tests prove: a hadith item with no grading is rejected; an unknown `source_id` is rejected; a checksum mismatch is rejected; a normalizer-drift item is rejected; normalizer is idempotent | 3h |
| T-403 | Corpus v0: fill `text_normalized` and `checksum_sha256` over the P-06 ingested items, then extend coverage to the 12 brief cases — Qur'an (KFC text) + Sahihayn with dorar.net gradings | @Robin | `data/corpus-v0` | `validate.py` passes on every item with all 7 rules active; each of the 12 cases has at least one plausible target item, or is explicitly recorded as a case that must abstain; case 11 has the correct verbatim verse so CONTRADICTS can cite it; every `source_id` is in SOURCES.md | 2.5h |
| T-404 | Retrieval: normalization + BM25 over corpus v0, behind a `Retriever` interface | @Vegapunk | `feat/retrieval` | A fixture of 12 queries returns the expected `corpus_id` in the top 5 for every case that has a target; cases with no target return an empty result rather than a weak match | 3h |
| T-405 | Level classifier A/B/C/D: deterministic level-D rules first, model may raise but never lower, low confidence → more restrictive | @Vegapunk | `feat/level-classifier` | All 12 brief cases classify to their expected level; a unit test proves a model answer of "B" cannot override a rule-matched "D"; a test proves low confidence escalates restrictiveness | 2.5h |
| T-406 | Web scaffold: React + Vite, RTL, Arabic UI text, text input, transcript/extract review screen, AI-not-a-fatwa notice, privacy notice on the input screen | @Usopp | `feat/web-scaffold` | Builds clean; `dir="rtl"` and `lang="ar"` set; the AI-not-a-fatwa notice is on the result view and the privacy notice (SPEC.md §8) is on the input screen **before** submit, both covered by tests; no English in product-facing text | 4h |
| T-407 | Eval harness: reads `eval/testset.jsonl`, calls the API, checks hard assertions including `alignment` and `abstained_reason`, writes a per-case report, fails on a missing brief case id | @Nami | `test/eval-harness` | Runs end to end against a stub API; report lists every case with pass/fail per hard assertion; removing a brief case id from the file makes the run fail; a stub card with `state: SUPPORTED` and `alignment: null` fails (G17) | 2.5h |
| T-409 | `api/policy/content_policy.yaml`: transcribe SPEC.md §5.1, §5.2 and §9 into the policy file, `policy_version: p1`, `approved_by: pending` | @Robin | `data/content-policy-p1` | Every row of §5.1, every `alignment` rule of §5.2 and the §9 referral strings are present and match SPEC.md exactly; the file parses; the PR description carries the file so the Sharia specialist can review the policy instead of the code | 1h |
| T-408 | Daily status post: done / in progress / blocked / risks | @Luffy | — | Posted in the channel by 23:00 | 0.5h |

Day 1 load: @Vegapunk 8h, @Robin 6.5h, @Usopp 4h, @Nami 2.5h, @Luffy 0.5h

---

## Oct 5 — day 2: cards and gates

Goal by 23:59: all three card states produced correctly, the hard gates enforced in code, the card UI rendering real responses, and the full test set running.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-501 | `POST /api/v1/extract`: claim segmentation + level classification + span offsets | @Vegapunk | `feat/extract-endpoint` | Spans map back to exact substrings of the input; a multi-claim Arabic paragraph yields separate claims; `max_claims` is honoured and `dropped_count` is accurate | 2.5h |
| T-502 | Card composer + state machine **driven by `content_policy.yaml`** (T-409), including `alignment` on SUPPORTED cards | @Vegapunk | `feat/card-composer` | Tests are driven from the policy file and cover every row of §5.1, including level C with one position → CANNOT_CONFIRM and level D with strong retrieval → CANNOT_CONFIRM; `abstained_reason` is non-null exactly when the state is CANNOT_CONFIRM; `alignment` is non-null exactly when SUPPORTED; an unmatched scripture span in the claim forces `CONTRADICTS` (§5.2 rule 3); undetermined alignment yields CANNOT_CONFIRM + `ALIGNMENT_UNDETERMINED` and never `CONFIRMS` (§5.2 rule 4); editing a threshold in the YAML changes behaviour with no code change | 3.5h |
| T-503 | Gates: verbatim match, scripture/explanation separation, hadith grading, two-line verify, user-quote isolation, alignment present. A failing gate forces CANNOT_CONFIRM and is never repaired | @Vegapunk | `feat/response-gates` | Tests prove: a one-character-altered quote fails and the card drops to CANNOT_CONFIRM; a quoted span planted in `explanation_ar` fails; an ungraded hadith item is dropped and an emptied `evidence` drops the card; the user's altered wording never reaches `evidence[].quote_ar` (G16); `gate_report` reflects each outcome | 3h |
| T-504 | `POST /api/v1/check` wired end to end, with `503 PIPELINE_DEGRADED` on any stage failure | @Vegapunk | `feat/check-endpoint` | A real Arabic input returns schema-valid cards; a forced stage failure returns 503 and never a guessed card | 2h |
| T-505 | Card UI: the three states, the three `alignment` badges, evidence block visually separate from explanation, source and grading visible without a click, the 2 verify lines, the referral block with the §9 body and the "in your country" line | @Usopp | `feat/card-ui` | Each state renders from a fixture; CONTRADICTS renders the "contradicts the source" badge next to the correct verbatim text, and the user's wording renders in the claim block in a visibly different component (G16); a test asserts the explanation and quote are in different containers; grading is shown for every hadith; RTL layout verified at mobile and desktop widths | 4.5h |
| T-506 | Corpus v1: tafsir (early sources / dorar), creed, general fiqh, seerah, glossary (islamic-content.com), Bayyinat Q&A; SOURCES.md completed with licenses | @Robin | `data/corpus-v1` | `validate.py` passes; G13 cross-check passes (corpus `source_id` set equals SOURCES.md set); every one of the 12 cases is covered or deliberately abstaining; new raw files requested through the owner, never downloaded by @Robin; Sharia specialist approval recorded in the PR by the owner, or the blocker named | 4h |
| T-507 | `POST /api/v1/link/fetch` — URL → readable text, returned for user review | @Usopp | `feat/link-input` | A fixture article yields readable Arabic text; a non-article URL returns `422 NO_READABLE_TEXT`; extracted text lands in the same editable review screen as a transcript | 2h |
| T-508 | First full eval run over all 12 cases; file one defect per failure with the case id | @Nami | `test/eval-run-d2` | Report committed under `eval/reports/`; every failure has an issue with the case id and the observed state; G1–G9 reported per gate | 2.5h |
| T-509 | Daily status post | @Luffy | — | Posted in the channel by 23:00 | 0.5h |

Day 2 load: @Vegapunk 11h (**over budget — the 12:00 decision point in the risks table is mandatory**), @Usopp 6.5h, @Robin 4h, @Nami 2.5h, @Luffy 0.5h

---

## Oct 6 — day 3: harden, deploy, submit

Goal by 23:59: deployed demo passing all gates on the live URL, plus the submission package. **Code freeze 18:00.** After the freeze only documentation, video, and deck work continues.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-601 | Deploy API to Render (account provided by the owner): config, env vars set in the Render dashboard only, CORS, rate limit, no-input logging confirmed | @Vegapunk | `ops/deploy-api` | Live `GET /health` returns the committed `corpus_version`, `policy_version` and `policy_approved_by`; a rate-limit test returns 429; `OPENAI_API_KEY` is set in the dashboard and appears nowhere in the repo (G18); deployed logs inspected and contain no input text, transcript, or claim text (G11) | 2h |
| T-602 | Deploy web to Cloudflare Pages (account provided by the owner), pointed at the live API, end-to-end smoke test | @Usopp | `ops/deploy-web` | Live URL runs Arabic text input → cards; the AI-not-a-fatwa and privacy notices are visible; smoke steps written into the README | 2h |
| T-603 | Audio input (P1): `POST /api/v1/transcribe`, ≤ 3 min limit, user reviews and edits the transcript before anything downstream runs | @Vegapunk | `feat/audio-input` | A 2-min Arabic clip returns an editable transcript; a 4-min clip returns `413 AUDIO_TOO_LONG`; a test proves the pipeline cannot run on an unconfirmed transcript. **First to cut if behind at 12:00.** | 3h |
| T-604 | README: run and setup docs, architecture summary, privacy statement, AI-disclosure statement, source-verification documentation | @Robin | `docs/readme-run-setup` | A clean clone can be run from the README alone by someone who has not seen the repo; the privacy and AI-disclosure statements are present and name that input text goes to an AI provider (SPEC.md §8); the pre-Oct-4 `baseline` work is disclosed with the tag name; source verification is documented (submission requirement) | 2.5h |
| T-605 | Full eval + safety regression on the **live** demo: all 12 cases, G1–G18, sign-off | @Nami | `test/eval-final` | Report committed; every one of G1–G18 marked pass with evidence, or marked fail with the case id; cases 1 and 11 verified as SUPPORTED + CONTRADICTS on the live demo and case 6 as CANNOT_CONFIRM + NO_MATCHING_EVIDENCE; any fail is escalated to @Luffy and the owner before 18:00 | 3h |
| T-606 | Secret scan over full history, dependency licence list, final repo hygiene | @Luffy | `chore/submission-hygiene` | Scan clean on all history; licence list committed; no user data or keys anywhere in the tree (G12); the reference-pack PDF is absent from the tree and its history status is settled with the owner (see risks) | 1h |
| T-607 | Demo video ≤ 2 min + deck (problem, solution, how it works, added value, technologies, results, continuation plan, screenshots) | @Usopp + @Robin | `docs/demo-assets` | Video under 2:00 and recorded against the live demo; deck covers all seven required sections | 3h |
| T-608 | Submission via the portal; keep the confirmation. Fallback: email info@IslamicAIch.org with proof of attempt and entry number | @Luffy | — | Confirmation saved and posted in the channel before 23:00, not 23:59 | 1h |
| T-609 | Final status post: what shipped, what was cut, known limits | @Luffy | — | Posted in the channel | 0.5h |

Day 3 load: @Vegapunk 5h, @Usopp 5h + shared 3h, @Robin 2.5h + shared 3h, @Nami 3h, @Luffy 2.5h

---

## Dependencies

```
P-02 testset ───────────────────────────► T-407 harness ──► T-508 ──► T-605
P-03 SOURCES ──► P-04 manifest ──► owner fills data/raw/ ──► P-06 ingest ──► T-403 corpus v0 ──► T-404 ──┐
T-401 scaffold ──► T-402 loader ──► T-403 / T-404 ──► T-502 composer ──► T-503 gates ──► T-504 ─────────┐
T-409 policy file ─────────────────────────► T-502                                                     │
T-405 classifier ──────────────────────────► T-502                                                     │
T-406 web scaffold ──► T-505 card UI ◄── T-504 (fixtures unblock earlier) ──────────────────────────────┤
T-506 corpus v1 ───────────────────────────► T-508                                                     │
                                                              T-601 + T-602 deploy ◄───────────────────┘
                                                                            └──► T-605 ──► T-607 ──► T-608
```

Hard sequencing rules:
- **T-409 must land before T-502 starts.** The composer reads the policy file; it never re-expresses the §5 table in Python. This is also how a late Sharia specialist change stays a config edit.
- **P-04 blocks on the owner, not on @Robin.** @Robin produces the manifest; nothing can be ingested until the owner has placed the files in `data/raw/`. P-06 is the first task that slips if that lands late.
- T-402 is the normalizer, so P-06 cannot compute `text_normalized` or `checksum_sha256`; T-403 does that on Oct 4.
- @Usopp works against committed JSON fixtures of the card schema, not against a live API. T-505 must not wait on T-504.
- T-403 must land before T-404 can be meaningfully tested; a stub corpus is acceptable for T-404's first commit but not for its PR.
- T-506 needs Sharia specialist approval, which is outside the team's control. See risks.
- @Vegapunk verifies the two model ids (SPEC.md §8) before starting T-405 and T-501, and reports in the channel.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| @Vegapunk is at ~11h on Oct 5 — the real bottleneck | Day 2 slips, which pushes gates into Oct 6 | T-402 is moved to @Robin (owner decision 8) and T-409 goes to @Robin as well, which clears Oct 4 to 8h and lets T-501 start Oct 4 evening if the classifier lands early. If Oct 5 is still over at 12:00: T-501 ships segmentation without refined span offsets, and T-507 link input is cut. The call is made at 12:00 on Oct 5, not at 20:00. |
| Sharia specialist unavailable | G14 cannot pass; corpus and test set stay `pending` | Escalated as blocking open question 2. Fallback: ship with `approved_by: pending` recorded honestly in SOURCES.md and the README, and say so in the demo rather than claim approval we do not have. |
| Final Sharia specialist review of §5 lands mid-build or late | A content change on Oct 5 or 6 hits the state machine, the worst possible time | Resolved by design: owner decision 1 makes the table a policy file (T-409), so a change is a YAML edit plus fixtures, not a rewrite. `approved_by` stays `pending` and `GET /health` says so until the owner records the approval. |
| The reference-pack PDF is already in public git history (`03109af`, merged to `main`) | Removing the file in P-05 does not remove it from a public repo; anyone can still fetch it from history | Escalated to the owner as SPEC.md §11 Q2. A tree-level removal ships in P-05; a real removal needs `git filter-repo` plus a force-push to `main`, which only the owner performs. Decide before the `baseline` tag at the end of Oct 3, because the tag freezes what judges diff against. |
| The two model ids (`gpt-6-luna`, `gpt-6.1-sol`) are not verified against the provider yet | T-405, T-501 and all generated text fail at the first call | @Vegapunk verifies both ids before starting T-405 and reports in the channel. Model ids are config, so a correction is an env change. A non-resolving id is a blocker for @Luffy and the owner, never a silent substitution. |
| Pre-Oct-4 ingestion is read by judges as in-window work | Credibility damage, which costs more than the hours saved | `baseline` tag at the end of Oct 3, `baseline: true` on every pre-work corpus item, the pre-work table in this file, and the disclosure paragraph in the README (T-604). No application code before Oct 4 09:00, including the normalizer — which is why P-06 leaves the derived fields empty. |
| Corpus too thin, so most cases land on CANNOT_CONFIRM | Demo looks like it cannot answer anything | T-403 is scoped to the 12 cases specifically, not to breadth. Abstention is a correct outcome and we present it as one, but we need SUPPORTED and DISPUTED to appear at least once each in the demo. |
| Retrieval returns a weak match and the card claims support | Reliability failure — the worst outcome in the evaluation | Score floor below which retrieval returns empty; G2 verbatim gate; T-404 explicitly tests that a no-target case returns empty rather than a weak match. |
| LLM provider and keys undecided | Blocks T-405, T-501, and all generated text | Escalated as blocking open question 4. Classifier rules for level D need no model, so T-405 can start on rules alone. |
| Audio eats day 3 | Deploy and submission slip | T-603 is explicitly first to cut, with a 12:00 decision point. |
| Submission at 23:59 | Portal failure with no time to recover | T-608 targets 23:00, and the email fallback path is written into the task. |

---

## Not yet planned

Deliberately excluded from the 3-day window: embedding retrieval (SPEC.md P2), multi-language input beyond the brief's required non-Arabic case, caching, and any admin or corpus-editing UI. These belong to the continuation plan in the deck, not to the build.
