# TASKS.md — Tabayyan (تبيّن)

Status: owner-approved in substance; pending @Nami's `APPROVE` on PR #5. Assignments below go live when
the owner merges.
Owner of this document: @Luffy (lead)
Last updated: 2026-10-02
Times are Riyadh. Build window: Oct 4 09:00 → Oct 6 23:59.
Owner decisions driving this plan: SPEC.md §10. Still open: SPEC.md §12.

Conventions, from `AGENTS.md`: one task = one branch = one PR, small PRs, tests ship with code, the README section you touched is updated in the same PR, never push to main, never merge.
Review routing: request @Nami's review by @mention in the **#review** channel with the PR link; @Nami replies as a PR comment starting with `APPROVE` or `REQUEST CHANGES`. GitHub review requests do not work here — all agents share the owner's token. **The owner merges only after `APPROVE`** (owner decision 13).
Corpus and test-set PRs also need Sharia specialist approval; the owner obtains it and records it in the PR, and the `approved_by` / `reviewed_by` field is set to `sharia-reviewer-1` in that same PR.

Estimates are in agent-hours. `AT` = acceptance test: what must be demonstrably true for the PR to be mergeable.

---

## Pre-work (before Oct 4) — allowed, and disclosed as `baseline`

Only work done Oct 4–6 is evaluated, and prior work must be disclosed. Everything in this section is
tagged `baseline` in the repo and listed here so the disclosure is complete. `baseline` means **only**
the pre-Oct-4 disclosure; the corpus-free eval arm is called `control` (SPEC.md §6.5).

Owner decision 3 sets the boundary and owner decision 12 extends it once, for contract and configuration
artifacts only: test set (brief **and** red-team cases), `SOURCES.md`, allowlist, corpus collection and
ingestion, **plus `contracts/card.schema.json` and the two config files**. **No application code before
Oct 4 09:00** — that includes the normalizer, the validator, the retriever, the span detector and the
eval harness. @Robin downloads nothing: @Robin writes the manifest, the owner places the files in
`data/raw/`. The `baseline` tag is cut at the end of Oct 3. The widening is named explicitly in
SPEC.md §7 rather than left implicit.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| P-01 | SPEC.md and TASKS.md, updated with @Nami's PR #3 findings and the owner's second decision set (10–14) | @Luffy | `plan/initial` | Both files cover scope, architecture, API contracts, the three data schemas, input kinds and the question → claim design for all 12 brief cases, the A–D → state mapping with the `alignment` ratchet, the scripture-span detector, the policy/tuning split, untrusted input, providers, referral target, clip privacy and acceptance criteria; decisions 10–14 reflected and listed in SPEC.md §10; every @Nami finding either fixed or listed in SPEC.md §12; `APPROVE` from @Nami | 6h |
| P-02 | `eval/testset.jsonl`: all 12 required brief cases in the §4.3 schema, following the §4.4 design table | @Robin | `data/testset-v0` | All 12 brief case ids present; each validates against the schema; **each case carries the `input_kind` fixed in SPEC.md §4.4**; the four owner-fixed expectations are exactly as written (cases 1 and 11 → SUPPORTED + CONTRADICTS, case 6 → CANNOT_CONFIRM + NO_MATCHING_EVIDENCE, case 5 → CANNOT_CONFIRM + LEVEL_D_PERSONAL_CASE); case 12 carries `lang: "en"`; cases 7, 8 and 12 expect `card.term` populated; `reviewed_by` set to `sharia-reviewer-1`, or `pending` with the blocker named in the PR | 3.5h |
| P-03 | `SOURCES.md`: every approved source from the brief, with URL, how it is used, license and license URL | @Robin | `docs/sources-v0` | Every domain row in the brief's approved-references table appears; no source lacks a license field; no unapproved source present; each row states whether its licence permits redistributing the raw file; **the approved Qur'an translation (KFC or quranpedia.net) and the islamic-content.com glossary each have their own row**, since SPEC.md §4.2 now depends on them for cases 8 and 12 | 2.5h |
| P-04 | Approved-source allowlist + **download manifest** for the owner: exact file, exact URL, per domain. **This is the task that unblocks the owner's downloads — it goes first.** | @Robin | `data/corpus-notes` | Allowlist derived from the brief and matching SOURCES.md; the manifest names every file the owner must place in `data/raw/`, with its URL and licence note; the manifest covers the Qur'an translation and glossary sources; no download or scrape performed by @Robin | 2h |
| P-05 | Repo hygiene: `.gitignore` for keys, audio, images and non-redistributable raw files; `CODEOWNERS` with `api/policy/` owned by the owner; secret scan of existing history; `baseline` tag at the end of Oct 3 | @Luffy | `chore/repo-hygiene` | PDF no longer tracked (done in PR #4); `CODEOWNERS` committed and names the owner for `api/policy/` (G24); secret scan clean; `baseline` tag cut and pushed Oct 3; no audio, image or data files tracked outside `corpus/`, `eval/` and the permitted part of `data/raw/`. **The PDF remains reachable in public history at `03109af` — owner decision 13 is no rewrite, and SPEC.md §7 discloses it in those words.** | 1.5h |
| P-06 | Corpus v0 ingestion from `data/raw/` into `corpus/corpus.jsonl`: authored fields only, `baseline: true`, derived fields left empty for T-403 | @Robin | `data/corpus-v0-ingest` | Every item carries `corpus_id`, `domain`, `source_id`, `source_url`, `text_ar`, `ref`, `license`, `license_url`, `retrieved_at`, `baseline: true`, `grading` for every hadith item, and `text_en` + `translation_of` for every `quran_translation` item; `text_normalized` and `checksum_sha256` are empty and recorded as T-403's job; every `source_id` is in the P-04 allowlist; no file in the PR is application code | 3h |
| P-07 | **`contracts/card.schema.json`** — the machine-readable §4.1 card contract, plus one example fixture per state and per `alignment` value under `contracts/fixtures/` | @Vegapunk | `contract/card-schema` | The schema expresses every §4.1 field rule a schema can express: `alignment` non-null iff SUPPORTED and restricted to `CONFIRMS \| CONTRADICTS` (no `PARTIAL`); `abstained_reason` non-null iff CANNOT_CONFIRM; `how_to_verify_ar` exactly 2 entries; `positions` non-empty only when DISPUTED with ≥ 2 entries; `alignment_confidence` **required in every state**; `state_label_key` restricted to the four keys. Four example fixtures validate; four deliberately-invalid fixtures are rejected. **Schema and fixtures only — no Python, no Pydantic, no pipeline code** (SPEC.md §7). Lands before P-08, T-407, T-502 and T-505 | 2h |
| P-08 | **`api/policy/content_policy.yaml` + `api/tuning.yaml`** — transcribe SPEC.md §5.1, §5.4, §5.5 and §9 into the two files, split specialist-owned from engineering-owned | @Robin | `data/content-policy-p1` | Both files parse; `content_policy.yaml` carries every row of §5.1, every rule of §5.4, the full `scripture_span_markers` list, `near_miss_max_ceiling`, `tone_affects_level: false`, the §9 referral strings, `policy_version: p1` and `approved_by: pending`; `tuning.yaml` carries the four thresholds and `tuning_version: t1`, and **no content rule appears in it**; `near_miss_max <= near_miss_max_ceiling`; the PR description carries both files inline so the Sharia specialist reviews the policy instead of the code. Config only — no code | 1.5h |
| P-09 | **Red-team test cases** in `eval/testset.jsonl` with `origin: "team"` | @Nami | `test/redteam-v0` | At minimum: fabricate-a-hadith; hostile tone over a level-B subject; a personal fatwa framed as a general question; prompt injection inside **pasted** text; prompt injection inside **fetched link** text; a misquoted verse behind an attribution formula; **a misquoted verse with no marker at all, which must still be caught by Trigger B**; a correct paraphrase with no marker, which must **not** be flagged; an English injection attempt. Each case states the expected state and why, and each validates against the §4.3 schema. These run in CI beside the brief cases (G21) | 2h |

Pre-work total: ~24h — @Robin 12.5h over Oct 2–3, @Luffy 7.5h, @Vegapunk 2h, @Nami 2h.
**@Robin is the pre-work bottleneck and has roughly Oct 2–3 to do it in.** If P-04 lands early the owner's
downloads overlap the rest, which is why P-04 goes first.

**Ordering inside pre-work:** P-04 first (it unblocks the owner's downloads) → P-03 → P-02 / P-09 in
parallel → P-07 → P-08 → P-06 once the owner has filled `data/raw/` → P-05 last, with the tag.

---

## Oct 4 — day 1: the spine

Goal by 23:59: Arabic text in → claims out, with input-kind detection, level classification, retrieval
against a real corpus slice, the misquote detector, the gates running against fixtures, and a card that
renders. No end-to-end wiring yet, no polish.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-401 | API scaffold: FastAPI app, `GET /health`, settings from env (`OPENAI_API_KEY`, the model ids), **loads `content_policy.yaml` and `tuning.yaml` and fails fast if `near_miss_max > near_miss_max_ceiling`**, CORS, error envelope, `pytest` + `ruff` in CI | @Vegapunk | `feat/api-scaffold` | CI green; `GET /health` returns `status`, `corpus_version`, `corpus_items`, `policy_version`, `policy_approved_by`, `tuning_version`, `card_schema_version`, `build`; error envelope covered by a test; a test proves the app fails fast with a clear error when `OPENAI_API_KEY` is absent, and no key literal exists in the tree (G18); a test proves the ceiling violation is a startup failure, not a warning (G24) | 3h |
| T-402 | Arabic normalizer + corpus loader + `corpus/validate.py` implementing all 8 validator rules in SPEC.md §4.2 | @Robin | `feat/corpus-loader` | Unit tests prove: a hadith item with no grading is rejected; an unknown `source_id` is rejected; a checksum mismatch is rejected; a normalizer-drift item is rejected; a `quran_translation` item without `translation_of` is rejected; the normalizer is idempotent | 3h |
| T-403 | Corpus v0: fill `text_normalized` and `checksum_sha256` over the P-06 items, then extend coverage to the 12 brief cases — Qur'an (KFC text), Sahihayn with dorar.net gradings, the approved translation and glossary records cases 8 and 12 need | @Robin | `data/corpus-v0` | `validate.py` passes on every item with all 8 rules active; each of the 12 cases has at least one plausible target item, or is explicitly recorded as a case that must abstain; **case 11 carries the correct verbatim verse so CONTRADICTS can cite it**; cases 7, 8 and 12 have glossary records with `text_en`; every `source_id` is in SOURCES.md | 2.5h |
| T-404 | Retrieval: normalization + BM25 over corpus v0, behind a `Retriever` interface, with the `retrieval_score_floor` from `tuning.yaml` | @Robin | `feat/retrieval` | A fixture of 12 queries returns the expected `corpus_id` in the top 5 for every case that has a target; **cases with no target return an empty result rather than a weak match**; a test proves a score below the floor is returned as empty. *(Moved from @Vegapunk — it is normalizer-adjacent and he is the bottleneck.)* | 3h |
| T-405 | Level classifier A/B/C/D: deterministic level-D rules first, model may raise but never lower, low confidence → more restrictive, **tone is never a level input** | @Vegapunk | `feat/level-classifier` | All 12 brief cases classify to their expected level; a unit test proves a model answer of "B" cannot override a rule-matched "D"; a test proves low confidence escalates restrictiveness; **a test proves the hostile phrasing of case 9 classifies the same as a neutral phrasing of the same subject** (SPEC.md §4.4) | 3h |
| T-406 | Web scaffold: React + Vite, RTL, Arabic UI text, text input, the one review/edit screen for all input kinds, AI-not-a-fatwa notice, privacy notice on the input screen, **consent checkbox on the upload control** | @Usopp | `feat/web-scaffold` | Builds clean; `dir="rtl"` and `lang="ar"` set; the AI-not-a-fatwa notice is on the result view and the privacy notice (SPEC.md §8) is on the input screen **before** submit, both covered by tests; the consent checkbox carries the exact Arabic string from SPEC.md §6.6 and submit is disabled until it is ticked, covered by a test (G22); no English in product-facing text | 4.5h |
| T-407 | Eval harness: reads `eval/testset.jsonl`, calls the API, **validates every card against `contracts/card.schema.json`**, checks hard assertions including `input_kind`, `alignment`, `alignment_confidence`, `state_label_key` and `abstained_reason`, writes a per-case report, fails on a missing brief case id | @Nami | `test/eval-harness` | Runs end to end against a stub API; report lists every case with pass/fail per hard assertion; removing a brief case id from the file makes the run fail (G9); a stub card with `state: SUPPORTED` and `alignment: null` fails (G17); a stub card that does not validate against the schema fails (G23) | 3h |
| T-410 | **Policy pinning test**: SPEC.md §5.1 and §5.4 as literals in test code, independent of the YAML; plus a `CODEOWNERS` assertion | @Nami | `test/policy-pin` | The pinned table and rules are written out as literals in the test file, not read from `content_policy.yaml`; **a test proves that editing `allowed_states` for level C to include `SUPPORTED` fails CI**; a test asserts `CODEOWNERS` covers `api/policy/`; a test asserts `PARTIAL` is not an accepted `alignment` value (G24) | 1.5h |
| T-411 | **Scripture-span detector + the two near-miss triggers** (SPEC.md §5.2): Trigger A markers from `content_policy.yaml` against the whole corpus, Trigger B a sliding window over unmarked claim text against the **cited** record only, both yielding `VERBATIM \| NEAR_MISS \| UNRELATED` | @Luffy | `feat/span-detector` | Markers come from the policy file, never hard-coded; **a verse with one word altered behind `﴿ ﴾` or an attribution formula is `NEAR_MISS`** (Trigger A); **the same one-word-altered verse with no marker at all is also `NEAR_MISS` against the cited record** (Trigger B — @Nami's original attack; the test for it is the point of this task); the same verse quoted exactly is `VERBATIM`; **a correct paraphrase with no marker returns no span at all**; a misquote inside a longer sentence is found by the window rather than hidden by whole-string distance; unrelated text inside quote marks is `UNRELATED` and produces no alignment signal; both bands respect the ceiling. Deterministic — no model call anywhere in this module. Lands before T-502. *(See SPEC.md §12 Q7: taken by the lead because @Vegapunk has no capacity and this is @Nami's hard blocker.)* | 3h |
| T-408 | Daily status post: done / in progress / blocked / risks, plus API spend against the $30 cap | @Luffy | — | Posted in the channel by 23:00 | 0.5h |

Day 1 load: @Vegapunk 10h *(see risks — T-405 can slip to Oct 5 morning)*, @Robin 8.5h, @Usopp 4.5h, @Nami 4.5h, @Luffy 3.5h

---

## Oct 5 — day 2: cards, gates, and the misquote path

Goal by 23:59: all three card states produced correctly, the alignment ratchet enforced, the hard gates
in code, the card UI rendering real responses, and the full test set plus the control arm running.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-501 | `POST /api/v1/extract`: **input-kind detection, question → claim handling (presupposition extraction, question subject, term lookup, no-checkable-claim)**, claim segmentation, span offsets, and the untrusted-input prompt boundary | @Vegapunk | `feat/extract-endpoint` | Spans map back to exact substrings of the input; a multi-claim Arabic paragraph yields separate claims; `max_claims` honoured and `dropped_count` accurate; **brief case 1 yields a claim with `origin: "presupposition"`**; a term request yields `origin: "term_lookup"`; input with no checkable proposition sets `no_checkable_claim`; English input returns `detected_lang: "en"` and is not rejected; **every model call puts input in a delimited data region and returns a strict JSON-schema-constrained object** (SPEC.md §5.7, G19, G21) | 4h |
| T-502 | Card composer + state machine **driven by `content_policy.yaml` and `tuning.yaml`**, including the **alignment ratchet** of §5.4 (both §5.2 triggers) and the glossary/term path | @Vegapunk | `feat/card-composer` | Tests cover every row of §5.1, including level C with one position → CANNOT_CONFIRM and level D with strong retrieval → CANNOT_CONFIRM; `abstained_reason` non-null exactly when CANNOT_CONFIRM; `alignment` non-null exactly when SUPPORTED; **`alignment_confidence` present in every state**; **a stubbed model `CONFIRMS` yields `CONTRADICTS` both on a claim with a marked `NEAR_MISS` span and on a claim whose unmarked text is a near-miss against the cited record**; a stubbed `CONFIRMS` below `alignment_confidence_min` or below the score floor yields CANNOT_CONFIRM + `ALIGNMENT_UNDETERMINED`; **no code path assigns `CONFIRMS` directly from a model field**; `state_label_key` set correctly for all four combinations; `card.term` filled from the glossary record and never generated; editing a threshold in `tuning.yaml` changes behaviour with no code change (G17, G20, G23, G26) | 4h |
| T-503 | Gates: verbatim match (both languages), scripture/explanation separation, hadith grading, two-line verify, user-quote isolation, alignment present, untrusted-input marker. A failing gate forces CANNOT_CONFIRM and is never repaired | @Vegapunk | `feat/response-gates` | Tests prove: a one-character-altered quote fails and the card drops to CANNOT_CONFIRM; a quoted span planted in `explanation_ar` or `explanation_en` fails; an ungraded hadith item is dropped and an emptied `evidence` drops the card; a `translation.text_en` that is not a verbatim approved-translation record fails (G2); **the user's altered wording never reaches `evidence[].quote_ar`, asserted as a property over all cards after normalization, not as a substring check on one fixture** (G16); `gate_report` reflects each outcome. Built against the P-07 fixtures, so it does not wait on T-502 | 3h |
| T-504 | `POST /api/v1/check` wired end to end, with `503 PIPELINE_DEGRADED` on any stage failure and schema validation before the response leaves | @Vegapunk | `feat/check-endpoint` | A real Arabic input returns schema-valid cards; an English input returns Arabic cards with `explanation_en`; a forced stage failure returns 503 and never a guessed card; a card that fails `contracts/card.schema.json` returns 503 rather than shipping (G23); client-supplied `level`, `input_kind` and `scripture_spans` cannot make the result less restrictive | 2h |
| T-505 | Card UI: the three states, the `alignment` badges, **the four `state_label_key` labels**, evidence block visually separate from explanation, source and grading visible without a click, the 2 verify lines, the referral block, `card.term` rendering, claim timestamp when present | @Usopp | `feat/card-ui` | Each state renders from a P-07 fixture; **CONTRADICTS renders the "contradicts the source" badge next to the correct verbatim text, and the `supported_contradicts` label is a distinct string that does not read as endorsement** (G26); the claim block carries `data-role="user-text"` and the evidence block `data-role="scripture"`, asserted by marker plus snapshot rather than by component identity (G16); a test asserts explanation and quote are in different containers; grading shown for every hadith; `term_en` rendered for a term card; RTL verified at mobile and desktop widths | 5h |
| T-506 | Corpus v1: tafsir, creed, general fiqh, seerah, glossary (islamic-content.com), Bayyinat Q&A, approved Qur'an translation; SOURCES.md completed with licenses | @Robin | `data/corpus-v1` | `validate.py` passes; G13 cross-check passes; every one of the 12 cases is covered or deliberately abstaining; new raw files requested through the owner, never downloaded by @Robin; Sharia specialist approval recorded in the PR by the owner as `sharia-reviewer-1`, or the blocker named | 4h |
| T-507 | `POST /api/v1/link/fetch` — article text **and** TikTok/YouTube official oEmbed, behind the **shared outbound-fetch guard** of SPEC.md §3, plus the click-to-load embed placeholder | @Usopp | `feat/link-input` | A fixture article yields readable Arabic text; a non-article URL returns `422 NO_READABLE_TEXT`; extracted text lands in the same editable review screen as a transcript; a YouTube and a TikTok URL return `kind: "platform_embed"` with title and thumbnail; **the official player renders only after an explicit click**, and the Arabic notice says it contacts the platform (A11); **SSRF tests: `http://` refused, a URL resolving to loopback / RFC1918 / `169.254.169.254` refused with `400 URL_NOT_ALLOWED`, a redirect to a private address refused at the hop, an oversize response refused while streaming, the timeout enforced, `GET`-only, and no media-download code path exists** (G27); @Usopp reports the Meta-app-token finding for Instagram in the channel before writing code. **Second to cut at the Oct 5 12:00 decision point.** | 3h |
| T-508 | First full eval run over all 12 brief cases **and the P-09 red-team cases**; file one defect per failure with the case id | @Nami | `test/eval-run-d2` | Report committed under `eval/reports/`; every failure has an issue with the case id and the observed state; G1–G9 and G19–G21 reported per gate; the injection cases are reported separately from the safety cases | 2.5h |
| T-611 | **Control arm**: run the same test set through the same model with **no corpus and no gates**, and report both arms side by side | @Nami | `test/control-arm` | The report carries, per arm, classification accuracy, abstention precision and recall, unsourced or unmatched quotes, and failures per category; the control arm's fabricated-quote count and abstention rate are stated as numbers; the harness labels the arms `tabayyan` and `control` and the word `baseline` appears nowhere in it (SPEC.md §6.5, G25) | 2h |
| T-509 | Daily status post, incl. API spend against the $30 cap | @Luffy | — | Posted in the channel by 23:00 | 0.5h |

Day 2 load: @Vegapunk 13h (**over budget — the 12:00 decision point is mandatory, see risks**), @Usopp 8h, @Robin 4h, @Nami 4.5h, @Luffy 0.5h

---

## Oct 6 — day 3: harden, deploy, submit

Goal by 23:59: deployed demo passing the gates on the live URL, plus the submission package.
**Deploy complete by 13:00. Code freeze 18:00.** After the freeze only documentation, video and deck work continues.

Fixed schedule, because the ordering is what makes the day survivable:

| Time | What |
|---|---|
| 09:00–10:00 | **T-606 secret scan over full history** — runs *before* any sign-off, so @Nami is not certifying G12 against unverified history |
| 09:00–13:00 | T-601 + T-602 deploy. **Hard deadline 13:00.** If deploy slips past 13:00 the 14:00 checkpoint becomes a deploy debugging session and buys nothing — escalate to @Luffy and the owner at 13:00, and cut T-603 |
| 13:00–14:00 | @Nami's first live pass (T-610) |
| 14:00 | **Live-demo eval checkpoint** (owner decision 12). @Nami posts what passes and what fails on the live URL |
| 14:00–15:00 | Repair window |
| 15:00–18:00 | T-605 final eval + G1–G27 sign-off on the live demo |
| 18:00 | Code freeze |
| 18:00–23:00 | T-607 video + deck, T-604 README, T-608 submission |
| 23:00 | **Submit.** Not 23:59 |

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-606 | **Runs first, 09:00.** Secret scan over full history, dependency licence list, final repo hygiene | @Luffy | `chore/submission-hygiene` | Scan clean on all history; licence list committed; no user data or keys anywhere in the tree (G12); the PDF is absent from the tree and SPEC.md §7's "removed from the tree, still reachable in history" wording is in the README | 1h |
| T-601 | Deploy API to Render (account from the owner): config, env vars in the Render dashboard only, CORS, rate limit. **Deadline 13:00** | @Vegapunk | `ops/deploy-api` | Live `GET /health` returns the committed `corpus_version`, `policy_version`, `policy_approved_by`, `tuning_version` and `card_schema_version`; a rate-limit test returns 429; `OPENAI_API_KEY` set in the dashboard and absent from the repo (G18). **Log inspection for G11 is the owner's, not this task's** — he reads the Render logs and posts the evidence in the channel (owner decision 12) | 2h |
| T-602 | Deploy web to Cloudflare Pages (account from the owner), pointed at the live API, end-to-end smoke test. **Deadline 13:00** | @Usopp | `ops/deploy-web` | Live URL runs Arabic text input → cards; the AI-not-a-fatwa and privacy notices visible; smoke steps written into the README | 2h |
| T-610 | **Live-demo eval checkpoint**, 13:00–14:00, reported at 14:00 | @Nami | `test/eval-live-checkpoint` | All 12 brief cases run against the **live** URL; pass/fail posted in the channel at 14:00 with the case ids; anything failing is triaged with @Luffy inside the 14:00–15:00 repair window. Fits the capacity freed by correcting @Usopp's Oct 6 load | 1.5h |
| T-603 | Audio/video input (P1): `POST /api/v1/transcribe`, ≤ 3 min, user reviews and edits the transcript before anything downstream runs, **claim timestamps from segments** | @Vegapunk | `feat/audio-input` | A 2-min Arabic clip returns an editable transcript with segments; a 4-min clip returns `413 MEDIA_TOO_LONG`; an upload without `consent` returns `400 CONSENT_REQUIRED`; a test proves the pipeline cannot run on an unconfirmed transcript; a test proves **no temporary file survives the request** and no transcript or segment text reaches a log (G22); each card carries `claim.time_span`, and **an edit that makes the mapping ambiguous yields `null` rather than a wrong timestamp** (SPEC.md §4.5). **First to cut if behind at 12:00** | 3.5h |
| T-604 | README: run and setup docs, architecture summary, privacy statement, AI-disclosure statement, source-verification documentation, **the `baseline` disclosure including the PDF-in-history sentence**, and **G14's status stated honestly** | @Robin | `docs/readme-run-setup` | A clean clone can be run from the README alone by someone who has not seen the repo; the privacy and AI-disclosure statements name that input text, audio and images go to an AI provider and that uploads are deleted (SPEC.md §8); the pre-Oct-4 `baseline` work is disclosed with the tag name and the extended-boundary artifacts (P-07, P-08) are named; the PDF sentence from SPEC.md §7 appears verbatim; **if `approved_by` is still `pending`, the README says G14 is not met and why** | 2.5h |
| T-605 | Full eval + safety regression on the **live** demo: all 12 brief cases, the red-team cases, G1–G27, sign-off. 15:00–18:00 | @Nami | `test/eval-final` | Report committed; every one of G1–G27 marked pass with evidence, or marked fail with the case id, **each citing the evidence of record named in SPEC.md §6.1** — G11 cites the owner's log post, G12 cites T-606, G14 cites the owner's PR record; cases 1 and 11 verified as SUPPORTED + CONTRADICTS on the live demo and case 6 as CANNOT_CONFIRM + NO_MATCHING_EVIDENCE; the control-arm comparison attached (G25); any fail escalated to @Luffy and the owner **immediately, not at 18:00** | 3h |
| T-607 | Demo video ≤ 2 min + deck (problem, solution, how it works, added value, technologies, results, continuation plan, screenshots) | @Usopp + @Robin | `docs/demo-assets` | Video under 2:00 and recorded against the live demo; deck covers all seven required sections; **the deck leads with the §1 contrast — closed approved corpus and designed abstention versus open web search** (owner decision 10); the results section carries the control-arm numbers; the continuation plan names share-to-app, the WhatsApp tipline and viral-claim matching | 3h |
| T-608 | Submission via the portal; keep the confirmation. Fallback: email info@IslamicAIch.org with proof of attempt and entry number | @Luffy | — | Confirmation saved and posted in the channel before 23:00, not 23:59 | 1h |
| T-612 | Screenshot/image input (P2): `POST /api/v1/image/extract`, consent required, image deleted after processing, text into the same review screen | @Usopp | `feat/image-input` | **Conditional — booked at 0h and started only if both P1 inputs are complete and signed off by 15:00 on Oct 6.** If started: an image returns editable Arabic text; an upload without `consent` returns `400 CONSENT_REQUIRED`; a test proves the image does not survive the request (G22); text read from an image is marked untrusted and a scripture-looking span in it still clears G2 against the corpus. **If not started, it is reported as cut in T-609 and moves to the continuation plan** | 0h (2.5h if taken) |
| T-609 | Final status post: what shipped, **what was cut**, known limits, G14's real status | @Luffy | — | Posted in the channel | 0.5h |

Day 3 load: @Vegapunk 5.5h, @Usopp **2h + shared 3h** *(corrected — his only solo task is T-602; the 3h this frees is what pays for T-610)*, @Robin 2.5h + shared 3h, @Nami 4.5h, @Luffy 2.5h

---

## Dependencies

```
P-04 manifest ──► owner fills data/raw/ ──► P-06 ingest ──► T-403 corpus v0 ──► T-404 ──┐
P-03 SOURCES ──► P-04                                                                   │
P-02 testset ─┬──────────────────────────► T-407 harness ──► T-508 ──► T-611 ──► T-605   │
P-09 redteam ─┘                                                                         │
P-07 card.schema.json ──┬──► T-407                                                      │
                        ├──► T-503 gates (against fixtures, does not wait on T-502)     │
                        └──► T-505 card UI                                              │
P-08 policy + tuning ───┬──► T-401 scaffold ──► T-405 classifier ──► T-502 ─────────────┤
                        └──► T-410 pinning test                                          │
T-402 loader ──► T-403 / T-404                                                          │
T-411 span detector ────────────────────────► T-502 composer ──► T-504 ─────────────────┤
T-406 web scaffold ──► T-505 card UI ◄── P-07 fixtures                                  │
T-506 corpus v1 ────────────────────────────► T-508                                     │
T-606 secret scan ─────────────────────────────────────────────────────────────┐        │
                      T-601 + T-602 deploy (by 13:00) ──► T-610 (14:00) ◄──────┴────────┘
                                                              └──► T-605 ──► T-607 ──► T-608
```

Hard sequencing rules:
- **P-07 `card.schema.json` must land before T-407, T-502 and T-505 start.** Otherwise @Nami, @Vegapunk and @Usopp each implement SPEC.md §4.1 prose in parallel on the same day and we get three divergent schemas by Oct 4 evening.
- **P-08 must land before T-401 and T-502.** The composer reads the policy file; it never re-expresses the §5 table in Python. This is also how a late Sharia specialist change stays a config edit.
- **T-411 must land before T-502.** The composer's alignment ratchet calls the span detector; without it, rule 1 of §5.4 has nothing to fire on and the misquote path is model judgment again — which is the exact failure @Nami demonstrated could pass every gate.
- **T-410 must land the same day as P-08**, so a policy edit is pinned from the moment the file exists.
- **T-606 must run before T-605**, so no gate is signed off against unverified history. It is the 09:00 task on Oct 6.
- **T-601 and T-602 must complete by 13:00 on Oct 6.** Past 13:00, the 14:00 checkpoint stops being an eval and becomes a deploy debugging session.
- **T-503 does not wait on T-502.** The gates are pure functions over a card and are built against the P-07 fixtures.
- **P-04 blocks on the owner, not on @Robin.** @Robin produces the manifest; nothing can be ingested until the owner has placed the files in `data/raw/`. P-06 is the first task that slips if that lands late.
- T-402 is the normalizer, so P-06 cannot compute `text_normalized` or `checksum_sha256`; T-403 does that on Oct 4.
- @Usopp works against the committed P-07 fixtures, not against a live API. T-505 must not wait on T-504.
- T-506 needs Sharia specialist approval, which is outside the team's control. See risks.
- @Vegapunk verifies **every** model id in SPEC.md §8 before starting T-405 and T-501, and reports in the channel.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **@Vegapunk is at 13h on Oct 5 and 10h on Oct 4** — the bottleneck, and worse than before, because fixing @Nami's findings added the presupposition path, the ratchet and the untrusted-input boundary | Day 2 slips, which pushes gates into Oct 6 and collides with the 13:00 deploy deadline | Everything movable has already moved: T-402 and T-404 to @Robin, T-411 to @Luffy, T-507 to @Usopp, T-503 decoupled from T-502 via the P-07 fixtures. What remains must be the same hands. **Mandatory 12:00 Oct 5 decision point:** if the morning's work is not done, T-507 link input is cut first, then T-501's refined span offsets degrade to claim-order only. T-405 may slip to Oct 5 morning. The call is made at 12:00, not at 20:00. **Raised to the owner as SPEC.md §12 Q6 — the honest answer may be fewer P1 inputs.** |
| Sharia specialist unavailable | G14 cannot pass; corpus and test set stay `pending` | Owner decision 13: `approved_by` is `sharia-reviewer-1` once approved, `pending` until then. G14 **passes only with real approval**; if still pending at submission we report G14 as not met and disclose it in the README and the deck (T-604, T-609). We do not soften it into a pass |
| Final Sharia review of §5 lands mid-build or late | A content change on Oct 5 or 6 hits the state machine at the worst possible time | Resolved by design: `content_policy.yaml` (P-08) makes a change a YAML edit plus the T-410 pinned literals plus fixtures, not a rewrite. The specialist reviews the file inline in the P-08 PR description rather than reading code |
| **SPEC.md §12 has 7 items open, 4 of them for the Sharia specialist** (PARTIAL, the CONTRADICTS label, paraphrase-behind-attribution, the near-miss ceiling) | T-411 and T-502 ship against a ceiling and a rule the specialist has not confirmed | Each has a restrictive working default so nothing blocks. All four are config values in `content_policy.yaml`, so a specialist correction is a YAML edit plus pinned-literal update, and the T-410 test makes forgetting the update a CI failure |
| The reference-pack PDF stays reachable in public history (`03109af`) | A judge cloning the repo can still fetch it | Owner decision 13: no rewrite. Mitigation is honesty, not removal — SPEC.md §7's wording goes verbatim into the README (T-604). Closed as a decision, not an open question |
| Model ids are unverified | T-405, T-501 and all generated text fail at the first call | **Every id in SPEC.md §8 is marked `pending verification` in the table an implementer reads.** @Vegapunk verifies all five before starting T-405 and reports in the channel. Model ids are config, so a correction is an env change. A non-resolving id is a blocker for @Luffy and the owner, never a silent substitution |
| **$30 API budget cap** | A mid-build cutoff with no credits and no eval runs | @Vegapunk reports spend in every daily status and escalates at $20. The control arm (T-611) is a second full pass over the test set and is counted against the cap, not treated as free. If the cap binds, the control arm runs once on Oct 5 and is not re-run on Oct 6 |
| Pre-Oct-4 work is read by judges as in-window work | Credibility damage, which costs more than the hours saved | `baseline` tag at the end of Oct 3, `baseline: true` on every pre-work corpus item, the pre-work table in this file, and the README disclosure (T-604). **The owner-authorized extension for P-07 and P-08 is named explicitly in SPEC.md §7** rather than left implicit |
| Corpus too thin, so most cases land on CANNOT_CONFIRM | Demo looks like it cannot answer anything | T-403 is scoped to the 12 cases specifically, not to breadth. Abstention is a correct outcome and we present it as one, but we need SUPPORTED and DISPUTED to appear at least once each in the demo |
| Retrieval returns a weak match and the card claims support | Reliability failure — the worst outcome in the evaluation | `retrieval_score_floor` below which retrieval returns empty; the G2 verbatim gate; the §5.4 ratchet, which refuses `CONFIRMS` when the score is below the floor; T-404 explicitly tests that a no-target case returns empty rather than a weak match |
| **A near-miss band is set wrong** | Too narrow: real misquotes pass as `UNRELATED`. Too wide: a correct paraphrase gets stamped "contradicts the source" | Two bands rather than one (SPEC.md §5.2): a wide band for marked spans, a tight `0.12` band for unmarked text compared only against the record the card cites. P-09 carries **both** failure directions as cases — an unmarked misquote that must be caught, and a correct paraphrase that must not be flagged — so either error is a CI failure rather than a demo-day discovery. The ceiling over both bands is specialist-owned (§12 Q4) |
| **Link input reaches the internal network (SSRF)** | A public unauthenticated endpoint fetching a user-supplied URL from inside Render | The shared outbound-fetch guard in SPEC.md §3 and gate G27, with the checks on the **resolved** address and re-run at every redirect hop. Written into the spec before T-507 starts rather than discovered on Oct 5 |
| Audio eats day 3 | Deploy and submission slip | T-603 is explicitly first to cut, with a 12:00 decision point, and it sits after the 13:00 deploy deadline in the schedule |
| Submission at 23:59 | Portal failure with no time to recover | T-608 targets 23:00, and the email fallback path is written into the task |

---

## Not yet planned

Deliberately excluded from the 3-day window and belonging to the continuation plan in the deck, not to
the build: `PARTIAL` alignment (SPEC.md §12 Q1), embedding retrieval, caching, any admin or
corpus-editing UI, platform share-to-app, a WhatsApp tipline, and matching repeated viral claims to
earlier results. Screenshot/image input (P2) has a task id — **T-612** — but is booked at 0h: it is below
the cut line and ships only if both P1 inputs are complete and signed off.

**Task-id note for reviewers:** there is no T-409. The policy-file task moved into pre-work as **P-08**
when owner decision 12 split `content_policy.yaml` from `tuning.yaml` and required both early enough
for the Sharia specialist to review. T-410 through T-412 and T-610 through T-612 are new in this PR.
