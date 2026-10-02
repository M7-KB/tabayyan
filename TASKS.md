# TASKS.md — Tabayyan (تبيّن)

Status: PR #5 merged to `main` at `81c9030` (2026-10-02 10:34, owner-merged). Day 1 is underway; PRs
#6–#9, #13, #14, #17 and #18 are open/in review. Owner of this document: @Luffy (lead)
Last updated: 2026-10-02
Times are Riyadh. **Build window: Oct 2 → Oct 6 23:59**, on organizer permission to start early (SPEC.md
§10 item 15). There is no separate pre-work category and no `baseline` tag — everything below is simply a
day in the plan. The word `baseline` does not appear anywhere in this repository.
Owner decisions driving this plan: SPEC.md §10. Still open: SPEC.md §12 (specialist wording/boundaries
only).

Conventions, from `AGENTS.md`: one task = one branch = one PR, small PRs, tests ship with code, the README
section you touched is updated in the same PR, never push to main, never merge.
Review routing: request @Nami's review by @mention in the **#review** channel with the PR link; @Nami
replies as a PR comment starting with `APPROVE` or `REQUEST CHANGES`. GitHub review requests do not work
here — all agents share the owner's token. **The owner merges only after `APPROVE`** (owner decision 13).
Corpus and test-set PRs also need Sharia specialist approval; the owner obtains it and records it in the
PR, and the `approved_by` / `reviewed_by` field is set to `sharia-reviewer-1` in that same PR.

**Load caps (owner, 2026-10-02, SPEC.md §10 item 16): no agent books more than 8h on any single day.**
**At most three agents' sessions run concurrently** — this is read as a staggering rule, not a rule about
which calendar day an agent may have a task: when more than three agents have same-day tasks with no
dependency between them, the fourth and fifth start as soon as one of the first three's sessions frees up,
in the order the dependency table implies. Flagged explicitly in case the owner meant literal day-level
exclusion instead — correct in the channel if so.

Estimates are in agent-hours. `AT` = acceptance test: what must be demonstrably true for the PR to be
mergeable.

## Ownership decisions, 2026-10-02 (@Luffy, from the owner's request)

- **`SOURCES.md` has exactly one owning branch: P-03 (`docs/sources-v0`).** P-04 (`data/corpus-notes`)
  must not ship its own copy — it rebases onto P-03 once P-03 merges and references the already-committed
  file. This was Nami's PR #6 finding 5 (P-04 shipped `SOURCES.md`, leaving P-03 homeless and the two
  branches conflicting); the task rows below are updated to say so explicitly, not just the dependency
  diagram.
- **The tools register (`TOOLS.md`) is owned by @Robin, and she collects rows centrally — no one else
  edits the file directly.** `TOOLS.md` was added and then removed again within PR #6 (commits
  `9cbdcd4`/`571cf38`) after it collided with `README.md` in the same PR — dropping it left the brief's
  "Log of sources, tools and licenses" submission requirement (`docs/challenge-brief.md` line 97) with no
  owner. @Robin recreates it on its own small branch, separate from P-04, so it cannot collide with
  `README.md` again. **Each contributor reports their tool/model usage to @Robin** (PR description or a
  channel message) rather than editing `TOOLS.md` directly; @Robin is the only one who commits a row. A
  one-contributor-per-row convention across five parallel branches resolves conflicts by dropping rows,
  and a dropped row is an undeclared tool in a submission deliverable (Nami, PR #18) — centralizing commit
  ownership is what makes "never resolve a `TOOLS.md` conflict by dropping a row" enforceable rather than
  aspirational. @Robin also owns giving any unresolved entry (e.g. a not-yet-verified model id) an explicit
  owner and a cutoff no later than the Oct 5 submission, so nothing sits unresolved into the deadline.

---

## Oct 2 — day 1: merge the plan, scaffold independently

Goal: **PR #5 merged** (`81c9030`, done). In parallel, everything that needs no other day's output: API
scaffold, the card contract, the Arabic normalizer, the web scaffold, the corpus
manifest, the test set, and the red-team set. @Robin and @Vegapunk already started before this plan was
finalized.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| P-01 | SPEC.md and TASKS.md updated with @Nami's PR #3 and PR #5 findings, the owner's decision sets, and the five-day re-plan | @Luffy | `plan/initial` | Both files cover scope, architecture, API contracts, the three data schemas, input kinds, the A–D → state mapping with the alignment ratchet, the word-budget scripture-span detector (§5.2), the policy/tuning split, untrusted input, providers, referral target, clip privacy, acceptance criteria, and this five-day schedule; every @Nami finding fixed or listed in SPEC.md §12; `APPROVE` from @Nami by 14:00 | 6h |
| T-401 | API scaffold: FastAPI app, `GET /health`, settings from env (`OPENAI_API_KEY`, model ids), **loads `content_policy.yaml` and `tuning.yaml` and fails fast if any `tuning.yaml` `word_budget_table` tier exceeds `word_budget_ceiling`**, CORS, error envelope, `pytest` + `ruff` in CI | @Vegapunk | `feat/api-scaffold` | CI green; `GET /health` returns `status`, `corpus_version`, `corpus_items`, `policy_version`, `policy_approved_by`, `tuning_version`, `card_schema_version`, `build`; a test proves the app fails fast with a clear error when `OPENAI_API_KEY` is absent, and no key literal exists in the tree (G18); a test proves the budget-ceiling violation is a startup failure, not a warning (G24) | 3h |
| P-07 | `contracts/card.schema.json` — the machine-readable §4.1 card contract, including `misquote_notice`, plus one example fixture per state and per `alignment` value under `contracts/fixtures/` | @Vegapunk | `contract/card-schema` | The schema expresses every §4.1 field rule a schema can express: `alignment` non-null iff SUPPORTED, restricted to `CONFIRMS \| CONTRADICTS` (no `PARTIAL`); `abstained_reason` non-null iff CANNOT_CONFIRM; `how_to_verify_ar` exactly 2 entries; `positions` non-empty only when DISPUTED with ≥ 2 entries; `alignment_confidence` required in every state; `misquote_notice` present and schema-valid on a level-D fixture and on a hadith-domain near-miss fixture; `state_label_key` restricted to the four keys. Four valid fixtures validate; four deliberately-invalid fixtures are rejected. Schema and fixtures only — no Python, no pipeline code. Lands before T-407, T-502, T-505 | 2h |
| P-03 | `SOURCES.md`: every approved source from the brief, with URL, how it is used, license and license URL. **`SOURCES.md` has exactly one owning branch — this one** (owner, 2026-10-02 decision below) | @Robin | `docs/sources-v0` | Every domain row in the brief's approved-references table appears; no source lacks a license field; no unapproved source present; each row states whether its licence permits redistributing the raw file; the approved Qur'an translation and the islamic-content.com glossary each have their own row | 2.5h |
| P-04 | Approved-source allowlist (`corpus/approved_sources.json`) + **download manifest** for the owner: exact file, exact URL, per domain. **Does not ship its own copy of `SOURCES.md`** — rebases onto P-03 once P-03 merges and references the committed file. Unblocks the owner's downloads — goes first once P-03 is in | @Robin | `data/corpus-notes` | Allowlist derived from the brief and matching the merged SOURCES.md; the manifest names every file the owner must place in `data/raw/`, with its URL and licence note; covers the Qur'an translation and glossary sources; no download or scrape performed by @Robin; no `SOURCES.md` diff in this PR once P-03 is merged | 2h |
| T-406 | Web scaffold: React + Vite, RTL, Arabic UI text, text input, the one review/edit screen for all input kinds, AI-not-a-fatwa notice, privacy notice on the input screen, **consent checkbox on the upload control** | @Usopp | `feat/web-scaffold` | Builds clean; `dir="rtl"` and `lang="ar"` set; the AI-not-a-fatwa notice is on the result view and the privacy notice (SPEC.md §8) is on the input screen before submit, both covered by tests; the consent checkbox carries the exact Arabic string and submit is disabled until it is ticked (G22); no English in product-facing text | 4.5h |
| P-02 | `eval/testset.jsonl`: all 12 required brief cases in the §4.3 schema, following the §4.4 design table | @Robin | `data/testset-v0` | All 12 brief case ids present; each validates against the schema; each case carries the `input_kind` fixed in SPEC.md §4.4; the four owner-fixed expectations are exactly as written; case 12 carries `lang: "en"`; cases 7, 8, 12 expect `card.term` populated; `reviewed_by` set to `sharia-reviewer-1`, or `pending` with the blocker named | 3.5h |
| P-09 | **Red-team test cases** in `eval/testset.jsonl` with `origin: "team"` | @Nami | `test/redteam-v0` | At minimum: fabricate-a-hadith; hostile tone over a level-B subject; a personal fatwa framed as a general question; prompt injection inside pasted text **and** fetched link text; a misquoted verse behind an attribution formula; a misquoted verse with no marker at all (Trigger B must catch it); a correct paraphrase with no marker (must not be flagged); a hadith paraphrased by meaning behind an attribution formula (must **not** be flagged as contradicting — must produce `misquote_notice`, not `CONTRADICTS`); a correctly-quoted twin verse against a cited near-identical verse (the veto must hold); an English injection attempt. Each case states the expected state and why, validates against §4.3. Runs in CI beside the brief cases (G21) | 2h |
| T-408 | Daily status post: done / in progress / blocked / risks, plus API spend against the $30 cap | @Luffy | — | Posted in the channel by 23:00 | 0.5h |

Day 1 load: @Robin 8h (P-04 2h + P-03 2.5h + P-02 3.5h), @Vegapunk 5h, @Usopp 4.5h, @Nami 2h, @Luffy 6.5h — all ≤ 8h.

---

## Oct 3 — day 2: corpus, retrieval, classifier, span detector; first deploy by 21:00

Goal by 23:59: a real corpus slice, lexical retrieval, the level classifier, and the scripture-span
detector built and tested in isolation (not yet wired into a full card). A minimal API is live on Render
by 21:00 so Oct 4 onward iterates against a real deployment.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| P-06 | Corpus v0 ingestion from `data/raw/` into `corpus/corpus.jsonl`: authored fields only, derived fields left for T-403 | @Robin | `data/corpus-v0-ingest` | Every item carries `corpus_id`, `domain`, `source_id`, `source_url`, `text_ar`, `ref`, `license`, `license_url`, `retrieved_at`, `grading` for every hadith item, `text_en` + `translation_of` for every `quran_translation` item; `text_normalized`/`checksum_sha256` empty and recorded as T-403's job; every `source_id` is in the P-04 allowlist | 3h |
| P-08 | **`api/policy/content_policy.yaml` + `api/tuning.yaml`** — transcribe SPEC.md §5.1, §5.4, §5.5 and §9 into the two files, split specialist-owned from engineering-owned | @Robin | `data/content-policy-p1` | Both files parse; `content_policy.yaml` carries every row of §5.1, every rule of §5.4, `scripture_span_markers`, `word_budget_ceiling`, `hadith_near_miss_shows_notice_not_contradicts`, `contradicts_requires_confidence_floor`, `tone_affects_level: false`, the §9 referral strings, `policy_version: p1`, `approved_by: pending`; `tuning.yaml` carries the four numeric thresholds plus `word_budget_table` and `trigger_b_min_window_tokens`; no `word_budget_table` tier exceeds `word_budget_ceiling`; the PR description carries both files inline for specialist review | 1.5h |
| P-10 | `TOOLS.md` register skeleton — the brief's "log of sources, tools and licenses" requirement, on its own branch so it cannot collide with `README.md` again (moved off Day 1 to keep @Robin ≤ 8h — Nami, PR #14 finding 1) | @Robin | `docs/tools-register` | File exists with a README link; evidence-backed rows only — no provider model identifier logged until independently verified; @Robin is the only committer to the file, collecting each contributor's reported tool/model usage centrally rather than letting contributors edit it directly (Nami, PR #18 finding — a shared append-only table across parallel branches drops rows on conflict); any unresolved entry carries an explicit owner and a cutoff no later than Oct 5; no overlap with SOURCES.md's source-license rows | 0.5h |
| T-402 | Arabic normalizer + corpus loader + `corpus/validate.py` implementing all 8 validator rules in SPEC.md §4.2 | @Robin | `feat/corpus-loader` | Unit tests prove: a hadith item with no grading is rejected; an unknown `source_id` is rejected; a checksum mismatch is rejected; a normalizer-drift item is rejected; a `quran_translation` item without `translation_of` is rejected; the normalizer is idempotent | 3h |
| T-405 | Level classifier A/B/C/D: deterministic level-D rules first, model may raise but never lower, low confidence → more restrictive, tone is never a level input | @Vegapunk | `feat/level-classifier` | All 12 brief cases classify to their expected level; a unit test proves a model answer of "B" cannot override a rule-matched "D"; a test proves low confidence escalates restrictiveness; a test proves the hostile phrasing of case 9 classifies the same as a neutral phrasing of the same subject | 3h |
| T-411 | **Scripture-span detector** (SPEC.md §5.2): word-level edit distance against the `tuning.yaml` budget table, both triggers against the whole corpus index (Qur'an + hadith), the verbatim veto ahead of everything, `trigger_b_min_window_tokens` floor on Trigger B only, `span_detector_status` reported, Qur'an/hadith domain split feeding `misquote_notice` | @Vegapunk | `feat/span-detector` | Markers and the budget table come from policy/tuning files, never hard-coded; **@Nami's word-budget probe v2 rows ship as literal test cases**: each of her measured one-word misquotes (2, 3, 4, 4, 4, 6, 19 tokens) classifies `NEAR_MISS`; each of her four twin pairs (incl. Q 7:69/7:74) classifies `VERBATIM` via the veto, not `NEAR_MISS`; a hadith-domain `NEAR_MISS` behind an attribution formula does not set `CONTRADICTS` and populates `misquote_notice` instead; a quran-domain `NEAR_MISS` does set up the forcing condition for §5.4 rule 1; a correct paraphrase with no marker and outside budget returns `UNRELATED`; a 2-token window below `trigger_b_min_window_tokens` never fires Trigger B; `span_detector_status` is `ran` on a clean run and a non-`ran` status is produced when the detector is stubbed to raise. Deterministic — no model call anywhere in this module. Lands before T-502 | 3h |
| T-420 | **First deploy, by 21:00.** Minimal Render deployment of the Oct 2–3 scaffold: `GET /health` live, env vars in the Render dashboard, CORS | @Vegapunk | `ops/deploy-api-v0` | Live `GET /health` reachable from a public URL by 21:00, reporting the fields committed so far; `OPENAI_API_KEY` set in the dashboard, absent from the repo (G18). Superseded by T-601's full deploy on Oct 6 but gives every later day a real target to iterate against | 1h |
| T-407 | Eval harness skeleton: reads `eval/testset.jsonl`, calls the (not-yet-complete) API, validates cards against `contracts/card.schema.json` | @Nami | `test/eval-harness` | Runs end to end against a stub API; report lists every case with pass/fail per hard assertion; removing a brief case id from the file makes the run fail (G9); a stub card with `state: SUPPORTED` and `alignment: null` fails (G17); a stub card that does not validate against the schema fails (G23) | 3h |
| T-410 | **Policy pinning test**: SPEC.md §5.1 and §5.4 as literals in test code, independent of the YAML | @Nami | `test/policy-pin` | The pinned table and rules are written as literals, not read from `content_policy.yaml`; a test proves editing `allowed_states` for level C to include `SUPPORTED` fails CI; a test asserts `PARTIAL` is not an accepted `alignment` value; a test asserts the startup budget-ceiling check exists (G24) | 1.5h |
| T-412 | Daily status post | @Luffy | — | Posted by 23:00 | 0.5h |

Day 2 load: @Robin 8h (P-06 3h + P-08 1.5h + T-402 3h + P-10 0.5h), @Vegapunk 7h, @Nami 4.5h, @Luffy 0.5h — all ≤ 8h.

---

## Oct 4 — day 3: composer, gates, card UI on the real API; first full eval

Goal by 23:59: all three card states produced correctly, the alignment ratchet (both triggers, the
domain split, the confidence floor on `CONTRADICTS`) enforced in code, the hard gates running, the card
UI rendering real responses from the live deploy, and a first full eval run.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-501 | `POST /api/v1/extract`: input-kind detection, question → claim handling (presupposition extraction, question subject, term lookup, no-checkable-claim), claim segmentation, span offsets, untrusted-input prompt boundary | @Vegapunk | `feat/extract-endpoint` | Spans map back to exact substrings of the input; a multi-claim paragraph yields separate claims; `max_claims` honoured; brief case 1 yields `origin: "presupposition"`; a term request yields `origin: "term_lookup"`; no-checkable-proposition input sets `no_checkable_claim`; English input returns `detected_lang: "en"`; every model call puts input in a delimited data region and returns a strict JSON-schema-constrained object (G19, G21) | 4h |
| T-503 | Gates: verbatim match (both languages), scripture/explanation separation, hadith grading, two-line verify, user-quote isolation, alignment present, untrusted-input marker. A failing gate forces CANNOT_CONFIRM and is never repaired | @Vegapunk | `feat/response-gates` | A one-character-altered quote fails and the card drops to CANNOT_CONFIRM; a quoted span planted in `explanation_ar`/`explanation_en` fails; an ungraded hadith item is dropped; a non-verbatim `translation.text_en` fails (G2); the user's altered wording never reaches `evidence[].quote_ar` or `misquote_notice.quote_ar`, asserted as a property over all cards (G16); `gate_report` reflects each outcome. Built against the P-07 fixtures — does not wait on T-502 | 3h |
| T-502 | Card composer + state machine driven by `content_policy.yaml` and `tuning.yaml`, including the full alignment ratchet of §5.4 (both triggers, the domain split, the confidence floor on both `CONFIRMS` and `CONTRADICTS`) and the glossary/term path | @Vegapunk | `feat/card-composer` | Tests cover every row of §5.1 plus level C with one position → CANNOT_CONFIRM and level D with strong retrieval → CANNOT_CONFIRM; `abstained_reason` non-null exactly when CANNOT_CONFIRM; `alignment_confidence` present in every state; a stubbed model `CONFIRMS` yields `CONTRADICTS` on a quran-domain `NEAR_MISS` (marked or unmarked) but yields `CONFIRMS` + `misquote_notice` on a hadith-domain `NEAR_MISS`; a stubbed `CONFIRMS` **or** `CONTRADICTS` below `alignment_confidence_min` yields CANNOT_CONFIRM + `ALIGNMENT_UNDETERMINED`; no code path assigns `CONFIRMS` or `CONTRADICTS` directly from a model field (G17, G20, G23, G26) | 4h |
| T-505 | Card UI: the three states, the `alignment` badges, the four `state_label_key` labels, `misquote_notice` rendering, evidence block visually separate from explanation, source and grading visible without a click, the 2 verify lines, the referral block, `card.term` rendering, claim timestamp when present | @Usopp | `feat/card-ui` | Each state renders from a P-07 fixture; CONTRADICTS renders the badge `لا يطابق المصدر المعتمد` next to the correct verbatim text, introduced by `النص كما ورد في المصدر:` (G26); the claim block carries `data-role="user-text"` and the evidence block `data-role="scripture"` (G16); explanation and quote are in different containers; grading shown for every hadith; a `misquote_notice` card renders the notice without an alignment badge; RTL verified at mobile and desktop widths | 5h |
| T-403 | Corpus v0: fill `text_normalized`/`checksum_sha256`, extend coverage to the 12 brief cases | @Robin | `data/corpus-v0` | `validate.py` passes with all 8 rules active; each of the 12 cases has a plausible target item or explicitly abstains; case 11 carries the correct verbatim verse; cases 7/8/12 have glossary records with `text_en`; every `source_id` is in SOURCES.md | 2.5h |
| T-404 | Retrieval: normalization + BM25 over corpus v0, behind a `Retriever` interface, with `retrieval_score_floor` from `tuning.yaml` | @Robin | `feat/retrieval` | A fixture of 12 queries returns the expected `corpus_id` in the top 5 for every case that has a target; cases with no target return an empty result rather than a weak match; a test proves a score below the floor is returned as empty | 3h |
| T-508 | First full eval run over all 12 brief cases and the P-09 red-team cases | @Nami | `test/eval-run` | Report committed under `eval/reports/`; every failure has an issue with the case id and observed state; G1–G9, G16–G21 reported per gate; injection cases reported separately from safety cases | 2.5h |
| T-611 | **Control arm**: same test set, same model, **no corpus and no gates**, reported side by side | @Nami | `test/control-arm` | Per arm: classification accuracy, abstention precision/recall, unsourced quotes, failures per category; the harness labels the arms `tabayyan` and `control`, and the word `baseline` appears nowhere in it (SPEC.md §6.5, G25) | 2h |
| T-509 | Daily status post, incl. API spend against the $30 cap | @Luffy | — | Posted by 23:00 | 0.5h |

Day 3 load: @Vegapunk 7h, @Usopp 5h, @Robin 5.5h (T-403 2.5h + T-404 3h), @Nami 4.5h, @Luffy 0.5h — all ≤ 8h.

---

## Oct 5 — day 4: P1 inputs, red-team run, full eval, fixes; first portal submission by 22:00

Goal by 23:59: audio and link input live behind the gates, the full red-team run against them, fixes
from that run, and a first submission to the portal so a working entry exists ahead of Oct 6.

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-504 | `POST /api/v1/check` wired end to end, `503 PIPELINE_DEGRADED` on any stage failure, schema validation before the response leaves | @Vegapunk | `feat/check-endpoint` | A real Arabic input returns schema-valid cards; an English input returns Arabic cards with `explanation_en`; a forced stage failure returns 503; a card failing `contracts/card.schema.json` returns 503 (G23); client-supplied `level`/`input_kind`/`scripture_spans` cannot make the result less restrictive | 2h |
| T-603 | Audio/video input (P1): `POST /api/v1/transcribe`, ≤ 3 min, user reviews and edits the transcript before anything downstream runs, claim timestamps from segments | @Vegapunk | `feat/audio-input` | A 2-min Arabic clip returns an editable transcript with segments; a 4-min clip returns `413 MEDIA_TOO_LONG`; an upload without `consent` returns `400 CONSENT_REQUIRED`; the pipeline cannot run on an unconfirmed transcript; no temporary file survives the request and no transcript/segment text reaches a log (G22); an edit that makes the mapping ambiguous yields `time_span: null` rather than a wrong timestamp | 3.5h |
| T-506 | Corpus v1: tafsir, creed, general fiqh, seerah, glossary, Bayyinat Q&A, approved Qur'an translation; SOURCES.md completed. Not required for the 12 brief cases (T-403 already covers those) — this is depth beyond them, needed before T-605, not before T-508 | @Robin | `data/corpus-v1` | `validate.py` passes; G13 cross-check passes; every one of the 12 cases is still covered or deliberately abstaining; new raw files requested through the owner, never downloaded by @Robin; Sharia specialist approval recorded by the owner, or the blocker named | 4h |
| T-507 | `POST /api/v1/link/fetch` — article text **and** TikTok/YouTube official oEmbed (title/caption + plain outbound link only, no embed player, no thumbnail — owner, item E2), behind the shared outbound-fetch guard of SPEC.md §3 | @Usopp | `feat/link-input` | A fixture article yields readable Arabic text; a non-article URL returns `422 NO_READABLE_TEXT`; a YouTube and a TikTok URL return `kind: "platform_embed"` with `title`/`author_name` as editable text and `source_url` as a plain link, nothing else rendered from the platform; SSRF tests: `http://` refused, a URL resolving to loopback/RFC1918/`169.254.169.254` refused with `400 URL_NOT_ALLOWED`, a redirect to a private address refused at the hop, an oversize response refused while streaming, timeout enforced, `GET`-only, no media-download code path exists (G27); @Usopp reports the Meta-app-token finding for Instagram before writing code | 2.5h |
| T-508a | **Calibrate `trigger_b_min_window_tokens`** against a measured false-positive run over the real P-03/corpus-v1 index (SPEC.md §12 item 4) | @Nami | `test/trigger-b-floor` | A run over ordinary (non-claim) Arabic prose from the corpus's own domain measures the false-positive rate of Trigger B at the current floor of 3; the floor is adjusted if the measured rate is non-trivial, and the change plus its evidence lands in `tuning.yaml` and this report | 1h |
| T-508b | Red-team run against the now-live P1 inputs (audio, link) plus a full eval re-run; file one defect per failure | @Nami | `test/eval-run-d4` | Every P-09 case re-run against audio/link paths where applicable; every failure filed with case id and observed state; fixes tracked back to the owning agent same day | 1h |
| T-609a | Fixes from the T-508b run, as needed, each in its own small PR | @Vegapunk / @Usopp | per-fix branch | Each fix references its defect's case id and re-passes the case | 2h (buffer) |
| T-608a | **First portal submission, by 22:00.** Whatever is green at that point — at minimum text input end to end | @Luffy | — | Submission made via the portal (or the email fallback) with confirmation saved and posted in the channel before 22:00; superseded by the Oct 6 21:00 final submission (T-608) | 1h |
| T-513 | Daily status post | @Luffy | — | Posted by 23:00 | 0.5h |

Day 4 load: @Vegapunk 5.5h, @Usopp 2.5h (+ share of the fix buffer), @Robin 4h, @Nami 2h, @Luffy 1.5h — all ≤ 8h.
The fix buffer (T-609a) is split by whoever owns the defect; it is sized small because the flattened
schedule means no agent arrives at Oct 5 already over capacity, unlike the original 3-day plan.

---

## Oct 6 — day 5: harden, deploy, submit

Goal by 23:59: deployed demo passing the gates on the live URL, plus the submission package, updated by
21:00. **Full deploy complete by 13:00. Code freeze 18:00.** After the freeze only documentation, video
and deck work continues.

| Time | What |
|---|---|
| 09:00–10:00 | **T-606 secret scan over full history** — runs before any sign-off |
| 09:00–13:00 | T-601 + T-602 full deploy. **Hard deadline 13:00** — if it slips, escalate to @Luffy and the owner and cut T-612 |
| 13:00–14:00 | @Nami's first live pass (T-610) |
| 14:00 | **Live-demo eval checkpoint.** @Nami posts what passes and fails on the live URL |
| 14:00–15:00 | Repair window |
| 15:00–18:00 | T-605 final eval + G1–G27 sign-off on the live demo |
| 18:00 | Code freeze |
| 18:00–21:00 | T-607 video + deck, T-604 README, **T-608 updated submission** |
| 21:00 | **Submit the updated entry.** Not 23:59 |

| ID | Task | Owner | Branch | Acceptance test | Est |
|---|---|---|---|---|---|
| T-606 | Secret scan over full history, dependency licence list, final repo hygiene | @Luffy | `chore/submission-hygiene` | Scan clean on all history; licence list committed; no user data or keys anywhere in the tree (G12); the PDF is absent from the tree and SPEC.md §7's "removed from the tree, still reachable in history" wording is in the README | 1h |
| T-601 | Deploy API to Render: config, env vars in the Render dashboard only, CORS, rate limit. **Deadline 13:00** | @Vegapunk | `ops/deploy-api` | Live `GET /health` returns the committed `corpus_version`, `policy_version`, `policy_approved_by`, `tuning_version`, `card_schema_version`; a rate-limit test returns 429; `OPENAI_API_KEY` set in the dashboard, absent from the repo (G18). Log inspection for G11 is the owner's — he reads the Render logs and posts the evidence in the channel | 2h |
| T-602 | Deploy web to Cloudflare Pages, pointed at the live API, end-to-end smoke test. **Deadline 13:00** | @Usopp | `ops/deploy-web` | Live URL runs Arabic text input → cards; AI-not-a-fatwa and privacy notices visible; smoke steps written into the README | 2h |
| T-610 | Live-demo eval checkpoint, 13:00–14:00, reported at 14:00 | @Nami | `test/eval-live-checkpoint` | All 12 brief cases run against the live URL; pass/fail posted at 14:00 with case ids; failures triaged with @Luffy in the 14:00–15:00 window | 1.5h |
| T-612 | Screenshot/image input (P2) — conditional, booked at 0h, started only if both P1 inputs are complete and signed off by 15:00 | @Usopp | `feat/image-input` | If started: an image returns editable Arabic text; an upload without `consent` returns `400 CONSENT_REQUIRED`; the image does not survive the request (G22); text read from an image is marked untrusted and a scripture-looking span in it still clears G2. If not started, reported as cut in T-609 | 0h (2.5h if taken) |
| T-604 | README: run/setup docs, architecture summary, privacy + AI-disclosure statements, **"development started Oct 2 with organizer permission"**, the PDF-in-history sentence, G14's status stated honestly | @Robin | `docs/readme-run-setup` | A clean clone can be run from the README alone; privacy/AI-disclosure statements name that input text, audio and images go to an AI provider and are not stored; the Oct-2 organizer-permission disclosure and the PDF sentence from SPEC.md §7 appear verbatim; if `approved_by` is still `pending`, the README says G14 is not met and why; no mention of `baseline` anywhere | 2.5h |
| T-605 | Full eval + safety regression on the live demo: all 12 brief cases, red-team cases, G1–G27, sign-off. 15:00–18:00 | @Nami | `test/eval-final` | Every one of G1–G27 marked pass with evidence or fail with case id, each citing the evidence of record in SPEC.md §6.1; cases 1 and 11 verified SUPPORTED + CONTRADICTS on the live demo, case 6 as CANNOT_CONFIRM + NO_MATCHING_EVIDENCE; control-arm comparison attached (G25); any fail escalated to @Luffy and the owner immediately | 3h |
| T-607 | Demo video ≤ 2 min + deck (problem, solution, how it works, added value, technologies, results, continuation plan, screenshots) | @Usopp + @Robin | `docs/demo-assets` | Video under 2:00, recorded against the live demo; deck covers all seven required sections; leads with the §1 contrast (owner decision 10); results section carries the control-arm numbers; continuation plan names share-to-app, the WhatsApp tipline, viral-claim matching | 3h |
| T-608 | **Updated submission via the portal, by 21:00.** Keep the confirmation. Fallback: email info@IslamicAIch.org with proof of attempt and entry number | @Luffy | — | Confirmation saved and posted in the channel before 21:00, not 23:59 | 1h |
| T-609 | Final status post: what shipped, what was cut, known limits, G14's real status | @Luffy | — | Posted in the channel | 0.5h |

Day 5 load: @Vegapunk 2h, @Usopp 2h + shared 3h, @Robin 2.5h + shared 3h, @Nami 4.5h, @Luffy 4.5h — all ≤ 8h.

---

## Dependencies

```
P-04 manifest ──► owner fills data/raw/ ──► P-06 ingest ──► T-402 normalizer ──► T-403 ──► T-404 ──┐
P-03 SOURCES ──► P-04                                                                              │
P-02 testset ─┬──────────────────────────────────────────► T-407 harness ──► T-508 ──► T-611 ──► T-605
P-09 redteam ─┘                                                                                    │
P-07 card.schema.json ──┬──► T-407                                                                │
                        ├──► T-503 gates (against fixtures, does not wait on T-502)                │
                        └──► T-505 card UI                                                          │
P-08 policy + tuning ───┬──► T-401 scaffold (ships Oct 2 with its own test fixture, swaps to the    │
                        │     real P-08 once it lands) ──► T-405 classifier ──► T-502 ──────────────┤
                        └──► T-410 pinning test                                                     │
T-411 span detector ────────────────────────────────────► T-502 composer ──► T-504 ────────────────┤
T-406 web scaffold ──► T-505 card UI ◄── P-07 fixtures                                              │
T-506 corpus v1 (depth beyond the 12 cases) ───────────────────────────────────────────► T-605     │
T-508a floor calibration ──► T-508b red-team run                                                    │
T-606 secret scan ─────────────────────────────────────────────────────────────┐                   │
                      T-601 + T-602 deploy (by 13:00) ──► T-610 (14:00) ◄──────┴───────────────────┘
                                                              └──► T-605 ──► T-607 ──► T-608
```

Hard sequencing rules:
- **P-07 `card.schema.json` must land before T-407, T-502 and T-505 start.** Otherwise three agents
  implement §4.1 prose in parallel and we get three divergent schemas.
- **P-08 must land before T-502, not before T-401.** T-401 (Oct 2) ships its own minimal test fixture for
  the budget-ceiling fail-fast check; it swaps to the real `content_policy.yaml`/`tuning.yaml` once P-08
  lands Oct 3. The composer (T-502, Oct 4) is what actually reads the policy file as its source of truth,
  and never re-expresses the §5 table in Python.
- **T-411 must land before T-502.** The composer's alignment ratchet calls the span detector; without it,
  §5.4 rule 1 has nothing to fire on.
- **T-410 must land the same day as P-08**, so a policy edit is pinned from the moment the file exists.
- **T-506 must land before T-605, not before T-508.** T-403 already covers the 12 required cases, so
  T-508 (the first full eval) does not need corpus v1's broader depth. T-506 just has to be in before the
  Oct 6 final eval.
- **T-606 must run before T-605**, so no gate is signed off against unverified history.
- **T-601 and T-602 must complete by 13:00 on Oct 6.** Past 13:00, the 14:00 checkpoint stops being an
  eval and becomes a deploy debugging session.
- **T-503 does not wait on T-502.** The gates are pure functions over a card, built against the P-07
  fixtures.
- **P-04 blocks on the owner, not on @Robin.** @Robin produces the manifest; nothing can be ingested until
  the owner has placed the files in `data/raw/`. P-06 is the first task that slips if that lands late.
- T-402 is the normalizer, so P-06 cannot compute `text_normalized`/`checksum_sha256`; T-403 does that
  once T-402 exists.
- @Usopp works against the committed P-07 fixtures, not against a live API. T-505 must not wait on T-504.
- T-506 needs Sharia specialist approval, outside the team's control. See risks.
- @Vegapunk verifies **every** model id in SPEC.md §8 before starting T-405 and T-501, and reports in the
  channel.

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| **The "at most three agents concurrently" rule may mean something stricter than staggered kickoff** | A day's table above books 4–5 agents, which would need re-splitting across more days if the owner means literal day-exclusion | Flagged explicitly in this document's header; raised in the channel; the schedule re-splits if corrected |
| Sharia specialist unavailable | G14 cannot pass; corpus and test set stay `pending` | `approved_by` is `sharia-reviewer-1` once approved, `pending` until then. G14 **passes only with real approval**; if still pending at submission we report G14 as not met and disclose it (T-604, T-609) |
| Final Sharia review of §5 and §5.2's Qur'an/hadith split lands mid-build | A content change hits the state machine at the worst possible time | `content_policy.yaml` makes a change a YAML edit plus the T-410 pinned literals plus fixtures, not a rewrite |
| **SPEC.md §12 has 4 items, all for the Sharia specialist** (the CONTRADICTS label wording, the hadith narration-by-meaning boundary, `word_budget_ceiling`, `trigger_b_min_window_tokens`) | T-411 and T-502 ship against defaults the specialist has not confirmed | Each has a restrictive working default. All are config values, so a specialist correction is a YAML edit plus pinned-literal update, and T-410 makes forgetting the update a CI failure |
| The reference-pack PDF stays reachable in public history (`03109af`) | A judge cloning the repo can still fetch it | No rewrite. Mitigation is honesty — SPEC.md §7's wording goes verbatim into the README (T-604) |
| Model ids are unverified | T-405, T-501 and all generated text fail at the first call | Every id in SPEC.md §8 is marked `pending verification`. @Vegapunk verifies all five before T-405/T-501 and reports in the channel. A non-resolving id is a blocker for @Luffy and the owner, never a silent substitution |
| **$30 API budget cap** | A mid-build cutoff with no credits and no eval runs | @Vegapunk reports spend in every daily status, escalates at $20. The control arm (T-611) is a second full pass and is counted against the cap |
| Corpus too thin, so most cases land on CANNOT_CONFIRM | Demo looks like it cannot answer anything | T-403 is scoped to the 12 cases specifically. We need SUPPORTED and DISPUTED to appear at least once each in the demo |
| Retrieval returns a weak match and the card claims support | Reliability failure — the worst outcome in the evaluation | `retrieval_score_floor`; the G2 verbatim gate; the §5.4 ratchet refuses `CONFIRMS` when the score is below the floor |
| **The word-budget table or `trigger_b_min_window_tokens` is set wrong** | Too narrow: real misquotes pass as `UNRELATED`. Too wide: a correct paraphrase gets stamped "contradicts the source", or ordinary prose trips Trigger B | P-09 carries both failure directions as cases; T-508a measures the floor against the real index rather than guessing. The ceiling over the table is specialist-owned (§12 item 3) |
| **Link input reaches the internal network (SSRF)** | A public unauthenticated endpoint fetching a user-supplied URL from inside Render | The shared outbound-fetch guard in SPEC.md §3 and gate G27, checks on the resolved address, re-run at every redirect hop |
| Audio eats day 4 or 5 | Submission slips | T-603 sits early (Oct 5) rather than last, and the fix buffer (T-609a) absorbs overflow before Oct 6 |
| First submission (Oct 5 22:00) is skipped under time pressure | No fallback entry exists if Oct 6 goes wrong | T-608a is a named task with its own acceptance test, not an optional nice-to-have |
| Submission at 23:59 | Portal failure with no time to recover | T-608 targets 21:00, well inside the deadline, and the email fallback path is written into the task |

---

## Not yet planned

Deliberately excluded from the build window and belonging to the continuation plan in the deck: `PARTIAL`
alignment (SPEC.md §5.3), embedding retrieval, caching, any admin or corpus-editing UI, platform
share-to-app, a WhatsApp tipline, matching repeated viral claims to earlier results, and the dropped
platform embed/thumbnail (owner, item E2 — a plain outbound link replaces it; no task reintroduces it
without a new owner decision). Screenshot/image input (P2) has a task id — **T-612** — but is booked at
0h: it ships only if both P1 inputs are complete and signed off by Oct 6 15:00.

**Task-id note for reviewers:** task IDs are unchanged from PR #5 wherever the task itself is unchanged —
only the day it lands on moved, as part of the five-day re-plan. T-502 (composer) and T-407 (eval harness
skeleton) carry the same ids as before; their acceptance tests are updated only where this revision's
§5.2/§5.4 changes required it. T-412 and T-513 are new daily-status slots (the old T-408/T-509/T-609
pattern didn't have enough ids for five days); T-420, T-508a, T-508b, T-609a and T-608a are also new.
There is still no T-409 — see the PR #5 history for why.
