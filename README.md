# Tabayyan (تبيّن)

Arabic-first web app that checks religious claims from typed text, a link, a short audio or video clip
(≤ 3 min), or a screenshot. Each claim returns one evidence card in exactly one state: SUPPORTED,
DISPUTED, or CANNOT_CONFIRM.

**Tabayyan is an AI tool. It is not a fatwa.**

General-purpose fact-checkers verify against open web search and nearly always produce an answer.
Tabayyan verifies only against a **closed, approved corpus** fixed per domain by the challenge brief,
names which evidence state applies, keeps source text and generated explanation in separate fields and
separate UI blocks, and **abstains and refers** when the corpus does not hold the evidence. Abstention is
a designed output here, not a failure mode.

## Text extraction (T-501)

`POST /api/v1/extract` accepts `{"text":"...","max_claims":10}`. Text is limited
to 12,000 Unicode code points; `max_claims` is an integer from 1 to 50. The server
validates strict structured extraction output, exact original source substrings,
claim origins and term/no-checkable-claim consistency before returning anything.
Assertions retain their original wording. Questions may yield a presupposition
or question subject; term/explanation requests yield one `term_lookup` claim.
English claims retain English text in the legacy `text_ar` field.

Set `OPENAI_API_KEY`, `OPENAI_MODEL_EXTRACT=gpt-6-luna` and
`OPENAI_MODEL_REASON=gpt-6.1-sol` in the environment, then start the API using the
setup below. These IDs are documented by OpenAI; project access still needs a live
check. No model is silently substituted. `/health` makes no provider calls, and
`HEALTH_ONLY=true` registers no extraction endpoint. Missing model configuration,
provider refusal, timeout, malformed JSON or invalid source spans return
`503 PIPELINE_DEGRADED`; empty/unintelligible input returns `400 NO_CLAIMS`;
unsupported detected language returns `422 TEXT_NOT_SUPPORTED_LANG`. Invalid
request shape returns `422 INVALID_REQUEST`, without echoing input.

Classification uses the full original input as well as each extracted claim;
deterministic D guards run before classification inference. `classifier_status`
distinguishes a rule-forced personal case from unavailable/low-confidence
classification, both of which retain restrictive D. Consumers must inspect this
status before selecting personal-case wording. Scripture detection scans original
input against the entire loaded scripture index and reports
`span_detector_status`; an absent index is `index_unavailable`, never a clean run.
All returned spans use half-open Unicode code-point offsets into the original
input, not JavaScript UTF-16 offsets. Use `Array.from(text)` before slicing in JS.
An unmarked detector window has `marker: null`. These are advisory user-input
spans, not verified quotes; `/check` must recompute all safety decisions.

Every model call uses `api.model.StructuredModel`. The OpenAI implementation uses
the Responses API with separate developer instructions and JSON-encoded
`untrusted_data` in the user message, a strict JSON schema, local validation,
`store: false`, no tools/conversation state and a 30-second timeout. The server
does not persist queries or log input/provider errors. Input goes to OpenAI;
`store: false` does not by itself remove provider abuse-monitoring retention.
See [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[data controls](https://developers.openai.com/api/docs/guides/your-data),
[extraction model](https://developers.openai.com/api/docs/models/gpt-6-luna) and
[classification model](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

Run `python -m pytest` for the full suite. HTTP transport fixtures exercise the
actual adapter and endpoint without billing, including model separation,
refusals, invalid spans, input injection boundaries, no-checkable claims,
segmentation limits, original-context routing and classifier failure statuses.
These tests verify boundary behavior, not live model accuracy. The extraction
adapter does not implement alignment, explanations or transcription.

## Text verification (T-502)

`POST /api/v1/check` accepts `{"claims":[{"id":"c1","text_ar":"...","level":"A"}],
"input_kind":"claim","locale":"ar"}`. Pass the original question/statement as
`text_ar` so the server can recompute its origin and detect altered scripture.
When submitting `/extract` results, also pass `original_text` with the full input:
the server re-extracts it to preserve question origins, personal-case context and
original scripture spans. The eval HTTP client supplies this field automatically.
Client levels and kinds are advisory: the server re-extracts, reclassifies and
re-detects, retaining the more restrictive route. Claims have unique IDs, at most
50 claims and a combined limit of 12,000 code points. Empty claims return 400;
invalid shapes return 422; infrastructure or card-schema failures return 503.
This endpoint currently supports text only; upload segments/timestamps are deferred.

The composer reads state and alignment rules from policy. Models propose only
retrieved IDs, confidence and separate bridging prose. Evidence is copied from
loader-validated original records, with source reference and source grading.
Generated quotations or matching source excerpts are rejected. Quran near-misses
against the whole index force CONTRADICTS; hadith near-misses instead show a sourced
wording notice. Unresolved detector/classifier/alignment, missing evidence, low
confidence and personal cases abstain with a referral and ready-to-ask question.
Unsupported glossary lookups carry `term: null`; the contract permits that only on
abstaining term cards. Approved translations are not attached in this first composer.

`/health` reports card schema version 1 in verification mode. Logs contain card
counts/states only; no input, claims, source text or provider diagnostics. Services
and the local index are reused, while requests/results are not cached or stored.
Run the full Python suite and Node data-contract checks. Synthetic composer tests
exercise state rows, thresholds, whole-index twins, grading, isolation, errors and
the HTTP workflow; they do not establish religious accuracy or deployed readiness.
The live-source contract and request-scoped gatekeeper ship separately after this PR.

## Arabic normalizer (normalizer portion of T-402)

Python 3.11+, standard library only for the normalizer. Install the API development dependencies
using the setup below, then run the full Python suite from the repository root:

```sh
python -m pytest
```

Import `normalize_arabic` from `corpus.normalize`. Version `ar-v1` composes Unicode NFC,
strips Arabic marks and tatweel, folds alef/ya/ta-marbuta variants, and collapses Unicode
whitespace. Presentation forms, format characters and digits retain their original form.
This general retrieval key does not provide the adversarial comparison required by the span
detector. T-411 owns a separate hardened function covering the four Unicode bypass classes;
it must not use `ar-v1` as its security comparison surface.

Use the result only as an indexing/matching key. Keep `text_ar` unchanged for display and calculate
its checksum from the original text using the corpus loader's documented encoding. Normalization is
lossy: equal keys do not authorize religious evidence or settle alignment. The normalizer implements no quote checker,
alignment, span detector or corpus download. Loader and validator usage is below.
Tests use synthetic non-scriptural text and include idempotence across
every Unicode scalar in blocks.

The normalizer and its tests were developed on October 2, 2026, with organizer permission to start
development that day (see Disclosure below). TASKS.md records the implementation and the pending
T-503a quote-safety follow-up: equal normalized keys must never authorize a quotation.

## Lexical retrieval (T-404)

`api.retrieval.Retriever` defines `retrieve(query, top_k=5, domain=None)` and
`candidates(query, top_k=None, domain=None)`. `BM25Retriever` indexes ar-v1 keys
with Unicode word boundaries and case folding. Okapi BM25 (`k1=1.5`, `b=0.75`,
positive Robertson IDF) determines ranking and the raw `retrieval_score` field.
Scores are not probabilities. Ties sort by `corpus_id`; domain filtering keeps
global index statistics unchanged.

A separate `overlap_score` gates `retrieve()`: distinct matched query terms
`/ max(retrieval_overlap_min_terms, distinct query terms)`. The denominator
minimum defaults to 1, so a full one-word or two-word lookup reaches 1.0.
`retrieval_overlap_floor` defaults to 0.25; this is an initial engineering
threshold, not real-corpus calibration or evidence confidence. Corpus size,
document frequency, repetition and unrelated lengths cannot increase it.
Raw `retrieval_score_floor: 8.0` is retained as legacy metadata but is not enforced
by this retriever. The lead's Oct 4 decision keeps it out of card gating until
calibration and the corresponding SPEC/composer change. Downstream consumers
must distinguish rank scores from overlap gating.

```python
from pathlib import Path
from api.config import load_config
from api.retrieval import BM25Retriever

_, tuning = load_config(Path("api/policy/content_policy.yaml"), Path("api/tuning.yaml"))
retriever = BM25Retriever.from_artifact(tuning)  # requires an approved local artifact
matches = retriever.retrieve("user claim", top_k=5)
# Each match has corpus_id, retrieval_score, overlap_score, and a detached original record.
```

`from_artifact` calls the public corpus validator/loader and propagates rejection.
Direct `BM25Retriever(records, tuning)` construction is an adapter for records
already validated by a loader, including a future private-artifact loader; it
does not grant licence or specialist approval. Original `text_ar` and provenance
are copied unchanged, isolated from caller mutations. Lexical matching never
authorizes a quotation, evidence state, or alignment; downstream gates still
check the original retrieved record. Empty queries, no overlap and below-floor
matches return an empty list, including when the floor is zero.

Run `python -m pytest` for the full Python suite. The retrieval tests use twelve
synthetic, non-religious query cases with expected top-five targets or abstention,
plus formula, floor-boundary, normalization, provenance and failure tests. These
are engineering fixtures, not the twelve brief safety cases or a real-corpus
evaluation. The overlap settings still need real-corpus calibration. Tests include
non-verbatim questions, partial quotations and short lookup reachability. No raw
source text, index artifact, query logging, model
call, endpoint or input persistence is added by this module.

`candidates(query, top_k=None, domain=None)` exposes all positive-overlap records
in BM25 order, without the floor or deduplication. T-411 can inspect below-floor
near-misses and twins through this public protocol, without private index access.
An explicit positive `top_k` limits candidate count; the default is unlimited.
Candidates retain detached original records and never authorize evidence.

## Claim card contract (P-07)

[contracts/card.schema.json](contracts/card.schema.json) is the Draft 2020-12 version-1
structural contract. [contracts/fixtures/](contracts/fixtures/) contains four valid cards:
SUPPORTED with each alignment, DISPUTED, and level-D CANNOT_CONFIRM. The CONFIRMS card
includes a hadith-domain near-miss notice; the level-D card includes a Quran-domain notice.
The seven `invalid-*.json` files must be rejected (alignment, abstention reason, positions,
verification-line count, detector status, notice without a near-miss, and level-A disagreement).
All evidence text and source identities are synthetic, non-scriptural placeholders;
these fixtures grant no source or specialist approval.

Owner clarification (2026-10-03): `misquote_notice` is now `{ evidence, note_ar } | null`.
Its `evidence` uses the same schema as `evidence[]`, including source name/URL, corpus ID,
verbatim quote, reference and hadith grading. Quran references require `surah`/`ayah`;
hadith references require `collection`/`number`. The old flat notice is rejected.
This revises the unintegrated version-1 contract: consumers must migrate before integration.
The composer must drop the entire notice and abstain/refer if provenance or verbatim checks fail;
the UI renders corrected source text separately from the generated `note_ar`.

Install the development dependencies below and run `python -m pytest` for fixture validation
and mutation regressions using Draft 2020-12 with URI format checking. Non-`ran` detector
statuses require CANNOT_CONFIRM, ALIGNMENT_UNDETERMINED, and a failed detector gate.
A notice requires at least one NEAR_MISS span; level A allows only SUPPORTED or CANNOT_CONFIRM.
Schema validation does not establish original-text equality, corpus provenance, quote isolation,
notice domain eligibility, matching evidence IDs, or ordered character/time spans; the runtime gates
must check those against the approved corpus. The contract includes the §5.2 detector
status and gate result, nullable Trigger B markers, and §9 referral fallback text.

## Scripture-span detector (T-411)

`api.span_detector.SpanDetector` accepts the whole approved Qur'an/hadith index as `Record`
objects and a `DetectorConfig.from_files(policy_path, tuning_path)`. The reviewed loader must
validate provenance and grading before constructing that index; this module does not load or
approve corpus data. P-08 supplies the committed policy/tuning files.
Synthetic tests use `DetectorConfig.from_mappings` with the SPEC defaults.

Both marked spans and unmarked sliding windows use a separate `comparison_key`, word edit
distance, configured budgets, and a whole-index verbatim veto. Arabic presentation forms,
format characters, U+08CA–U+08D2 marks, and both Arabic-Indic digit sets are covered.
Punctuation delimits words; original offsets remain in the claim text. Expanded presentation
ligatures can give multiple comparison words the same original character span.

`detect(text)` returns `span_detector_status` and findings. Each finding's `card_span()`
produces the §4.1 fields, including a null marker for Trigger B. Short exact matches still
receive the veto; the minimum-window floor applies only to Trigger B near-misses.
Overlapping windows against equal/shorter records do not turn an exact quote into a misquote;
a short exact record cannot suppress a near-miss against a longer record.
Trigger B also scans inside marked spans, including spans classified UNRELATED after
commentary padding. Duplicate windows are removed only after matching the same record
and classification within an established marked match; marker overlap alone never skips a scan.
`effects(level, note_ar)` exposes the Qur'an forcing condition or a hadith/level-D notice
copied from the matched record. The composer must apply the detector status and state ratchets,
then validate every displayed notice/evidence quote against the original approved source,
including source and hadith grading. Comparison equality never authorizes display.

No model calls, logging, input storage, corpus ingestion, or HTTP endpoints are introduced.
The scan is exhaustive for the fixture index; full-corpus performance and Trigger B
false-positive calibration remain unmeasured until licensed data exists (T-508a).
Run the full checks with `python -m pytest`, `ruff check .`, `ruff format --check .`,
and `node --test tests/*.test.mjs`. Tests include the seven literal one-word misquotes
and four twin pairs from Nami's probe v2, plus synthetic config, offset, Unicode, and
failure cases; those probe strings are test inputs and grant no corpus approval.

## Planning

| Document | Contents |
|---|---|
| [SPEC.md](SPEC.md) | Scope, architecture, API contracts, data schemas, input kinds and the question → claim design for all 12 required brief cases, the A–D → card-state mapping with the `alignment` ratchet, the scripture-span detector, the policy/tuning split, untrusted-input rules, providers, referral target, clip privacy, acceptance criteria |
| [TOOLS.md](TOOLS.md) | P-10 AI-tool inventory under merged PR #14; T-501 configured models and runtime dependency ranges recorded separately from live use and deployed versions; Robin reconciles by Oct 5 20:00 Riyadh |
| [TASKS.md](TASKS.md) | Day-by-day task plan for Oct 2–6 |
| [AGENTS.md](AGENTS.md) | Team, non-negotiable rules, workflow, file-access boundary |
| [CODEOWNERS](CODEOWNERS) | `api/policy/` is owned by the project owner (gate G24) |
| [docs/challenge-brief.md](docs/challenge-brief.md) | Challenge requirements: content levels, approved references, required test cases, evaluation weights |

## Status

PR #5 was owner-merged at `81c9030` without the required independent `APPROVE`.
This skipped step is recorded in the plan; the owner must obtain `APPROVE` before merging.
[PR #14](https://github.com/M7-KB/tabayyan/pull/14) assigns SOURCES.md to P-03 and
TOOLS.md to Robin for central collection. Reviewed #13/#17 land first; #6 then rebases
and passes standalone CI. Tools inventory is checked under G13 before submission and at freeze.

The content-level policy in [SPEC.md §5](SPEC.md) is still pending final Sharia specialist review, which
is why it ships as two config files — `api/policy/content_policy.yaml` (specialist-owned, pinned by a
test, CODEOWNERS) and `api/tuning.yaml` (engineering-owned thresholds) — rather than as branching code. A
change the specialist asks for is a config edit plus a pinned-literal update, not a rewrite.
`GET /health` reports `policy_approved_by`, so the running policy is auditable from the live demo. While
it reads `pending`, release gate G14 is **not met**, and that is reported rather than softened.

Items still awaiting the owner's or the specialist's decision are listed in [SPEC.md §12](SPEC.md), each
with a working default chosen in the restrictive direction.

## Disclosure

**Development started Oct 2, 2026, with the organizers' permission**, ahead of the Oct 4 window named in
the brief; the owner holds their notice on file. The full plan is in [TASKS.md](TASKS.md), day by day from
Oct 2 through Oct 6. There is no `baseline` tag and no pre-Oct-4 boundary — that earlier plan was
superseded once the early start was permitted.

The corpus-free comparison arm in the eval reports is called `control`.

The reference-pack PDF was **removed from the tree but remains reachable in this repository's public
history at commit `03109af`**. There is no history rewrite.

A Qur'an text archive (`data/raw/kfgqpc_hafs_smart_4/`) was committed directly to `main` on Oct 2, 2026
(commit `78c7988`), before its licence was confirmed. Owner decision 24 (2026-10-02): removed from the
tree, no history rewrite. **It remains reachable in this repository's public history**, same disclosure
as the reference-pack PDF above, at a different scale — this archive is the full Qur'an text, not one
PDF. This decision does not grant ingestion or redistribution permission. The package identifies itself
as KFGQPC Hafs Smart (`hafs_smart_v8`); redistribution clearance remains pending in P-03
([PR #17](https://github.com/M7-KB/tabayyan/pull/17)). A raw file is added back to `data/raw/` only once
its licence is confirmed and recorded in P-03's `SOURCES.md` (SPEC.md §4.2). Because raw directories are
ignored by default, the cleared-source PR must add an explicit per-source negation to `.gitignore` and
stage only the licensed files; never force-add an uncleared file.

## Privacy

No accounts. No stored queries. Text, audio and images you submit are sent to an AI provider for
processing and are not stored by us; audio and images are deleted immediately after processing. Cards
judge statements, never people: no speaker is named or identified, and there is no voice fingerprinting.
Uploading a clip requires an explicit consent tick. A TikTok or YouTube link shows only its title and
caption as editable text, plus a plain outbound link to the original — there is no embedded player and
no thumbnail, so nothing from the platform ever loads on the result screen.

API setup and run instructions are below; full application setup is tracked in TASKS.md, T-604.

## Web scaffold (T-406)

React + Vite, Arabic RTL (`lang="ar"`, `dir="rtl"`). Node 24. From the `web/` directory:

```sh
npm ci
npm test
npm run dev
npm run build
```

The page shows a temporary development-preview banner (remove it when T-504 wires the check endpoint),
the input screen has the AI-not-a-fatwa notice (always visible), the privacy notice before submit, and
the upload consent checkbox that gates the upload button. The privacy notice covers text and audio/video
only, because those are the input kinds the UI accepts; image input is P2. No API calls yet: submit
handlers are empty until T-504, and the UI does not read `VITE_API_URL` yet. Fonts are self-hosted (`@fontsource/ibm-plex-sans-arabic`), so the page does not load
third-party font CDNs.

## Card UI (T-505)

`web/src/components/card/` renders one evidence card per claim: state badge keyed on
`state_label_key`, the user's claim in `data-role="user-text"`, scripture in `data-role="scripture"`,
generated explanation in `data-role="explanation"`, plus positions, misquote notice, referral, term and a
collapsible "how to verify" block. An approved English translation renders inside the scripture block in
`data-role="translation"`, after the Arabic quote and source link, with its own source link (`translation.source_url`).
It is omitted when the evidence has no translation. Card tests load the P-07 fixtures in `contracts/fixtures/`.

The misquote notice reads the nested `misquote_notice = { evidence, note_ar }` shape from PR #36 (f532439). Its
`evidence` is shown with the same scripture block as `evidence[]`: source name, reference, grading (grade and grader),
the grading source link (`grading.grading_source_url`, labelled separately from the collection source link), quote and source link.
The notice is not shown when `evidence` is missing, or when a hadith notice does not have complete grading (`grade_ar`,
`grader_ar` and an https `grading_source_url`, all non-empty). The legacy flat
`{ corpus_id, quote_ar, note_ar }` shape is never rendered. The P-07 fixtures use the nested shape, so the
`supported_confirms` preview shows a notice.

The fixtures are synthetic. To preview them locally, run `npm run dev` and open `/#card-preview`. The
preview is compiled out of production builds. The state labels follow the SPEC.md §12 item 1 table; all
except `supported_contradicts` are provisional until owner and specialist approval.

Layout is mobile-first: the base rules are the 375px baseline, with a compact rule at 23.4375rem and below
and a desktop rule from 48rem that widens the reading column. Headless Chrome (puppeteer-core) on 2026-10-03
measured `scrollWidth` equal to the viewport at 375, 768 and 1280px, on the input screen and on the card preview
with a nested misquote notice (temporary fixture, not committed). No element extended past the viewport.
`web/src/__tests__/layout.test.js` only checks that the breakpoints exist. Label approval for the provisional
Arabic strings is still open (SPEC.md §12 item 1).

## Check client and results (T-504, part 1)

`web/src/api/check.js` builds and sends `POST /api/v1/check` (SPEC.md §3). It sends only the claim id,
the confirmed text, and an optional level; the server decides the final level and input kind. Every card is
validated against `contracts/card.schema.json` with Ajv (draft 2020-12) before it reaches the UI, including
nested evidence and the misquote notice. A card that does not validate is treated as `PIPELINE_DEGRADED`.
`web/src/components/Results.jsx` shows loading, error (with retry and edit), empty and card states; each error
code has an Arabic message with a next step.

Not wired yet: the input screen has no claims to send. `/check` takes claims from `/extract` (T-501), which
is not on main, and the client does not segment or classify text itself. The submit handlers stay empty and
the development-preview banner stays on until a live card works end to end. Tests use the P-07 fixtures and
mocked `fetch`; no live call was made. Ajv adds a runtime dependency to the web bundle. Arabic error copy is provisional until owner review.

## API scaffold (T-401)

Python 3.11+. From the repository root:

```sh
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -e '.[dev]'
python -m pytest
ruff check .
ruff format --check .
uvicorn api.main:app --no-access-log
```

Set `OPENAI_API_KEY` in the process environment for normal startup; no `.env` file is loaded automatically.
With `HEALTH_ONLY=true`, startup requires neither an API key nor policy/tuning files;
only degraded health is available, with API documentation and verification unavailable.
`.env.example` lists empty key/model settings. Model IDs are environment configuration, with no
model calls in this scaffold. Set `CORS_ORIGINS` to a JSON array of exact frontend origins; the default
allows none. Set `BUILD_SHA` to the deployed commit SHA. Disable server access logs as shown above
because paths and query strings can contain user text. No request body or exception details are logged
by application code or included in error responses.

P-08 provides `api/policy/content_policy.yaml` and `api/tuning.yaml`; override their locations with
`CONTENT_POLICY_PATH` and `TUNING_PATH` when needed. Normal startup fails on a missing API key, missing/invalid config, or
any word-budget tier exceeding the policy ceiling, zero budgets, or decreasing budgets across
length bands. The schema validates confidence floors and the Trigger B minimum window. Startup errors
identify the config path and field without echoing values. This reads metadata and limits only; it does
not implement alignment or span detection. `span_detector_status` and `misquote_notice` are runtime
claim/card fields per SPEC.md, not tuning keys; they arrive with the detector/card contract tasks.

The policy file transcribes SPEC §§5.1–5.5 and §9: level/state rows, state guards, the ordered
alignment ratchet, detector prerequisites, markers, user-text isolation and referral copy. State
guards run before alignment; level D stays CANNOT_CONFIRM even with a detected near-miss. The
scaffold currently loads metadata and budget limits only. Pipeline utilities consume these files
separately; the HTTP routes do not yet run the classifier, composer, detector or gates.
T-410 separately owns independent literal pinning; P-08 tests real-file startup integration.

T-502's preparatory retrieval regressions in `tests/test_composer_retrieval_contract.py`
reject high raw BM25 scores below the overlap floor, accept low raw scores above
that floor, and include the exact-floor boundary. These test retrieval prerequisites;
card alignment still requires the composer and its other safety gates. The policy
YAML now pins `overlap_score_at_least: retrieval_overlap_floor`, as approved by the
owner on Oct 4. A literal regression rejects replacement with the raw-score gate;
the legacy raw-score tuning field remains ranking metadata.

### Content level classifier (T-405)

`api/classifier.py` provides `LevelClassifier(model=adapter, policy_path=..., tuning_path=...)`.
Call `classify(claim_text, context=original_input)`; keyword-only `context` is required.
Omitting it raises `TypeError`, so extraction cannot silently discard personal-case cues.
Arabic normalization is applied only to deterministic routing keys, never to displayed text.
Routing keys remove Unicode format characters (including U+200D, U+200C and U+061C).
Every Arabic cue word accepts conjunction, preposition and article clitics, including
stacked forms and lam/article contraction. This conservative cue matcher is not a
full morphological analyzer; ambiguous matches may refer. Original text and model data
remain unchanged. Personal-case and judgment cues force D without a provider call.
Other rules establish a minimum
level; a model can raise it but cannot lower it. Hostility is not a routing cue.

The classifier reads P-08's restrictive level order and `level_confidence_min`.
The new classification threshold is independent of `card_confidence_min` (card evidence only).
Missing, malformed,
failed or below-floor model classifications resolve to D. `level_confidence` retains the model's
confidence (zero on missing/invalid output), rather than claiming certainty about that fallback.
The result contains `level`, `level_confidence`, a fixed English `level_rationale_en`,
and `classifier_status`: `rule_forced`, `model_validated`, `low_confidence` or `unavailable`.
The composer must check status before level-D personal-case policy: low confidence or
unavailable classification keeps the restrictive state but must not tell a user that their
question was a personal fatwa. T-502 owns that integration; this utility does not make cards.
First-person family/possessive cues and Arabic ability/possession framings force D,
including English relative possessives.
It does not establish authenticity, retrieve sources or choose a card state.

Provider adapters implement the shared `api/model.py` `StructuredModel.complete_json` interface:
fixed instructions, separately serialized untrusted data, and `LevelProposal.model_json_schema()`.
The provider must enforce that JSON schema, and the classifier validates it again locally.
Adapters must not merge data into instructions or log payloads/provider errors. Keys and model
IDs come from environment configuration. This utility ships without a live provider adapter or
HTTP integration; no inference calls are made in its tests.

The offline regression suite exercises the brief inputs and T14–T18 with a stub that always
proposes A, testing deterministic floors independently of model agreement. T11 remains skipped
because its owner-provided misquote input is missing. Separate tests cover model escalation,
low confidence, invalid JSON, failure handling, original-context retention, and tone invariance.
These checks are routing tests, not model accuracy measurements or religious approval.

Policy `p1` remains `approved_by: pending`, so G14 is not met. The owner must record specialist
approval before changing that field. SPEC §12 still lists four specialist decisions: Arabic state
label wording (including the three provisional labels added Oct 3), the hadith narration-by-meaning
boundary, ceiling 4 and Trigger B minimum 3. Tuning
`t1` uses the SPEC defaults (confidence 0.5/0.6, retrieval floor 8.0, word budgets 1/2/3); these are
initial engineering values, not measured performance. T-508a owns calibration against the real index.

`GET /health` exposes the policy approval and tuning versions read from those files. The private file
loader reports the loaded count and corpus version after full validation.
It still reports `status: degraded` while verification endpoints and the card schema are not integrated;
loading data is not evidence that the pipeline is ready. It is a scaffold liveness response, not a
release-readiness claim. Verification,
transcription and ingestion routes are not implemented by this PR. Errors use the SPEC envelope
`error: {code, message_ar, message_en}` with fixed text that does not echo input.

## First Render API deployment (T-420)

- Service type: Python web service `tabayyan-api-v0`, using [render.yaml](render.yaml).
- Plan: Free; manual deployment.
- Branch: `main`.
- Dashboard env vars: `HEALTH_ONLY=true` (no `OPENAI_API_KEY` required),
  `CORS_ORIGINS=[]` until the web origin exists, `BUILD_SHA` (deployed commit),
  `PYTHON_VERSION=3.11.9`. Enter values only in Render.
- Health path: `/health`.
- Live health-only API: <https://tabayyan-api.onrender.com> (degraded, `corpus_items: 0`, build `f696a50`).
- Live web preview: <https://tabayyan.pages.dev> (development preview; verification is not active yet).
  Cloudflare Pages: root directory `web`, build command `npm run build`, output directory `dist`,
  `NODE_VERSION=22`, `VITE_API_URL` set to the Render API URL. The UI does not read `VITE_API_URL` yet.
- Smoke test after deployment (replace the URL):

```sh
curl --fail --silent --show-error https://YOUR-SERVICE.onrender.com/health
curl --silent --show-error --write-out '\n%{http_code}\n' -X POST https://YOUR-SERVICE.onrender.com/verify
```

Expect health HTTP 200 with `status: degraded`, `corpus_items: 0`,
`policy_approved_by: pending`, null version fields and the deployed `build` SHA;
`POST /verify` must return HTTP 404.

## Source register (P-03)

See [SOURCES.md](SOURCES.md) for one readiness status per candidate source, uses and licence
evidence. The [dated owner decision](SOURCES.md#owner-licence-decision-2026-10-03-night)
permits challenge-app ingestion for kfc-mushaf, sahih-bukhari and dorar-hadith,
with redistribution prohibited. Raw files and built corpus never enter the public repo.
Machine-readable licence gates await the separate backend change. P-04 supplies
the separate acquisition manifest and allowlist. SOURCES.md preserves the public raw-package
history disclosure after the tree cleanup in PR #13.

For the owner's Oct 4 noon selection, see the
[minimal corpus clearance checklist](docs/MINIMAL_CORPUS_CHECKLIST.md): owner-selected
KFC verses (no tafsir), Bukhari 8, 7556, 63, 1399 with separate Dorar grading,
glossary terms and required demo behavior when
permission is missing. This checklist grants no ingestion or content approval.

The [Jamhara evidence section](SOURCES.md#jamhara-permission-evidence-2026-10-03)
consolidates the Oct 3 owner report and policy check. Both Jamhara entries remain
**needs owner action**; English equivalents require separately cleared source evidence.
T07 and T08 abstain with referral when cleared evidence is missing. Proposed minimum
corpus selections belong to the separate [checklist PR #33](https://github.com/M7-KB/tabayyan/pull/33).

Run the standalone register contract checks with `node --test tests/*.test.mjs`.
CI checks headers, unique IDs, required license fields and the closed domain enum.

The [dated organizer reply](SOURCES.md#partner-approval-for-challenge-use-2026-10-03)
records partner approval for challenge use; the later owner decision prohibits
redistribution of the three selected sources while allowing challenge-app ingestion.
Use the [specialist selection/test plan](docs/SPECIALIST_SELECTION_TEST_PLAN.md) and
[owner download list](docs/OWNER_DOWNLOAD_LIST.md) for five Ramadan claims from Dorar's
fake-hadith section as test inputs only, expected CANNOT_CONFIRM with referral,
and the per-item file handoff. Owner-confirmed pairs: 8=JDqeTpYd,
7556=f5wEbcxS, 63=QPGgH3Qa, 1399=pUrPIlDN. Exact files, grading content,
missing item URLs and specialist review remain pending. Muslim remains approved
but is marked not in current selection in the manifest. Bukhari 8 is proposed as the altered-hadith base; only the specialist
approves the altered text. The handoff stays unsent in OUTBOX while the specialist
is unavailable; documentation work proceeds. Only the owner downloads; these documents add no corpus or
executable test inputs and grant no licence or specialist approval.
The plan separates hadith NEAR_MISS notices from semantic contradiction variants
and explicitly records T11's conditional Quran correction policy under SPEC 5.2–5.4.
Both altered-word slots leave their final level/state/alignment as open specialist
questions; missing cleared evidence always requires abstention and referral.

## Manual source collection (P-04)

Follow [docs/DOWNLOAD_MANIFEST.md](docs/DOWNLOAD_MANIFEST.md) for the owner download checklist,
formats and local paths. [SOURCES.md](SOURCES.md) records the three-source challenge-app
ingestion permission and no-redistribution restriction. Other permissions remain pending.
Current loader gates need the separately assigned backend change; this docs PR does
not enable ingestion or pending-review runtime use.
[corpus/approved_sources.json](corpus/approved_sources.json) lists candidate sources by domain;
it does not grant licensing or Sharia approval. P-03 owns the source register.

Source IDs match the register and SPEC (including `kfc-mushaf`). Domains use the nine SPEC values;
translations remain separate records linked to the Arabic verse through `translation_of`.

Run all standalone checks with Node.js 24 (no packages to install):

```sh
node --test tests/*.test.mjs
```

The source checks reuse the register contract helper, require register/allowlist ID equality,
validate the pinned domains and check corpus source IDs against the allowlist when records exist.
An absent corpus does not establish corpus readiness or approval. CI runs both source suites.

## Corpus loader and validator (T-402 remainder)

`corpus.loader.load_corpus()` reads the local `corpus/corpus.jsonl` artifact and returns records only
after all eight SPEC §4.2 rules pass. It requires complete hadith grading, registered source/domain,
SHA-256 of unchanged UTF-8 `text_ar` bytes, reproducible `ar-v1` normalization, matching licence fields,
unique IDs, specialist approval and resolvable translation links/English glossary text. It never
downloads, repairs or rewrites records. A missing or empty corpus is an error, not readiness.

```sh
python -m corpus.validate
python -m pytest
```

The validator cross-checks `corpus/approved_sources.json` and the explicit machine-readable table in
`SOURCES.md`. For public-distribution validation, its allowlist row must have `license_status: confirmed`,
`ingestion_allowed: true` and `redistribution_allowed: true`; its exact licence and licence URL must
match the register. The private-use mode described below does not require redistribution; it still
requires confirmed ingestion. Unrelated candidate rows remain pending. Only an owner-cleared
source PR changes these flags and records permission for derived corpus/application display. This
validator trusts that reviewed metadata; it cannot prove the permission document or textual provenance.

Offline review of a licence-cleared artifact may use `python -m corpus.validate --allow-pending-review`
to admit `approved_by: pending`. This option never waives licence checks. `load_corpus` has the
analogous explicit `allow_pending_review` keyword, default false. The owner records actual specialist
approval in the content PR; a string in a fixture is not sign-off. Use `--corpus`, `--sources` and
`--register` for explicit offline paths. The loader's analogous keyword paths support tests/integration.

CI validates an artifact when present and reports its absence explicitly otherwise. No corpus records
ship with this task. P-06 raw ingestion and T-403 filling remain blocked on owner files, permissions
and specialist review; format-specific raw importers belong to P-06. Tests use only synthetic prose
and synthetic metadata and cover the eight rejection rules, original-text preservation and runtime
rejection of pending approval.

Review fixes follow the SPEC contract in PR #24: hadith grading has its own registered,
licence-cleared `grading_source_id` and an HTTPS URL on that source's host and approved
section. Collection approval never authorizes a grading reference. Each record's
`source_url` must also use its registered source host. Every present `text_en` requires
`checksum_en_sha256` over its original UTF-8 bytes, including whitespace and Unicode
composition; no normalization is applied. Tests reject unrelated hosts, misleading suffixes,
URL boundary bypasses, uncleared grading sources and English edits with stale checksums.
These checks bind metadata and detect edits; specialist review still verifies actual provenance.

## Required safety cases (P-02)

[eval/testset.jsonl](eval/testset.jsonl) contains twelve brief records, T13, the executable
neutral twin of hostile T09, and five owner-supplied Ramadan claims (T14–T18).
The Ramadan claims are exact test inputs only, including intentional partial quotes;
all five require `CANNOT_CONFIRM` with referral and have no corpus evidence binding.
Their grading reference is a link to [Dorar page 4](https://dorar.net/fake-hadith/4),
with no commentary copied. All records await Sharia specialist approval. T03 and T10 are
path stand-ins; T11 is a blocked verse placeholder. Their `g9_countable: false` fields exclude
them from G9 coverage. Sourced behavior and corpus bindings remain pending; this is not a
passing evaluation or the final 80–100-item set. See [eval/TESTSET_NOTES.md](eval/TESTSET_NOTES.md).

Run the complete local data-check suite with `node --test tests/*.test.mjs`
(Node.js 24, no packages). The explicit directory keeps frontend Vitest tests in
their own runner (`npm test` from `web/`).
These checks validate the draft's contract, exact Ramadan input digests and review safeguards; they do not run the model
or establish source readiness. The single tools register belongs to P-10, PR #18.

T09 and T13 refer to each other in both pairing metadata and review rubrics. The
All records explicitly provide `needs_sharia_review`, `g9_countable`, `blocked_reason_en`
and `paired_case_id`, following the proposed contract in PR #28 at `63ab1a3`.
That SPEC dependency and Nami's harness support remain pending; these data checks
alone do not close the evaluation requirement.

## Eval harness (T-407)

[eval/run.py](eval/run.py) reads [eval/testset.jsonl](eval/testset.jsonl), gets cards for every
case from one card source, validates each card against
[contracts/card.schema.json](contracts/card.schema.json), runs the hard assertions of SPEC.md
§4.3 per case, and then evaluates the §6.1 release gates as properties over every card in the run.
Soft assertions (`rubric_en`, `forbidden_behaviors`) are carried into the report for review and
are never counted as passes.

Use `--corpus PATH --sources PATH --register PATH` to supply the exact corpus loaded by the
service and its approval metadata. The existing corpus loader validates it; invalid artifacts are
setup errors. The report pins artifact, source metadata and register hashes. Required corpus IDs
present in that artifact must appear in card evidence. Absent IDs or unavailable corpus make the
case `not_evaluated` and not countable, with a reason; G9 fails for such a brief case and metrics
exclude it. Evidence IDs returned by a card never establish corpus availability. This input does
not implement the deferred full-corpus quote gates (G1/G2/G6/G16).

Schema-invalid cards fail G23 and their case, stop deeper traversal, and leave later cases reported.
Dependent gates report a schema prerequisite failure; contract properties and pair comparisons
are not evaluated on invalid shapes. Non-object extract/check responses are client errors.
A `NO_MATCHING_EVIDENCE` card carrying evidence fails `must_not_fabricate` (owner, 2026-10-04).

```bash
pip install -e '.[dev]'
python -m eval.run --stub eval/stubs/contract_pass.json          # stub card source
python -m eval.run --api-base https://your-api --arm tabayyan    # live API
python -m eval.run --stub eval/stubs/contract_pass.json \
  --json eval/reports/run.json --markdown eval/reports/run.md
```

Exit codes: `0` everything checked passed, `1` a case, gate or contract property failed, `2` the
run could not be set up. `--only T09` adds the pair partner automatically, because a pair
comparison is itself a hard assertion. `--arm` is `tabayyan` or `control`; the corpus-free arm is
always `control` (§6.5), and the control run itself is T-611.

Two reporting rules make the output usable as gate evidence:

- A gate whose evidence needs the approved corpus is reported `not evaluated` with the reason,
  never `pass`. At this head that is G1, G2, G6 and G16; G21 is `not evaluated` until the P-09
  red-team cases land, and G25 until the control arm runs. Where part of such a gate is decidable
  from the card alone — a quote field repeated in a generated field, the user's input inside a
  quote field — that part can still fail.
- `unmatched_quotes` is reported as `null` with a reason, not as `0`, while there is no corpus to
  match against.

G9 fails today, by design: T03, T10 and T11 carry `g9_countable: false`, so three of the twelve
brief cases are not covered. The run also fails if a brief case id is removed from the file. A
filtered `--only` run reports G9 as `not evaluated` rather than claiming coverage it does not have.

`eval/stubs/contract_pass.json` is a stub card source, not product behaviour: every card starts as
a `contracts/fixtures` card and the bundle only patches structural fields, so each Arabic string in
it is the fixtures' own synthetic placeholder text. No scripture, corpus record or glossary mapping
is authored there, and a passing stub run is evidence about the harness only. The harness runs
against the real API through `--api-base`; T-508 is the first full run and T-611 adds the control
arm.

## Private corpus file and pending review

The owner uploads Robin's built JSONL artifact as a Render Secret File and sets
`PRIVATE_CORPUS_PATH` to its mounted path in the service environment. Commit only
`corpus/manifest.json` with exactly `{"sha256": "<64 lowercase hex digits>", "corpus_version": "v1"}`;
the SHA-256 is over the complete file bytes, including line endings. `CORPUS_MANIFEST_PATH`
can override that public manifest path. No URL/read token is needed. No actual manifest is supplied
until the private artifact exists. Keep real artifacts under `corpus/private/` locally; built JSONL,
raw files and indexes are ignored and checked for accidental tracked files in CI.
The guard covers alternate JSONL names and backups, corpus build directories, data JSONL,
and index/embedding/database extensions even when force-added. Public corpus code/docs,
`approved_sources.json` and the checksum-only `manifest.json` are allowed.

Startup reads at most 64 MiB and validates the same bytes it hashed. All rows must pass before any
records reach app state. Missing files, hash mismatch or an invalid row leave `corpus_items: 0` and
`corpus_version: null`. `/health` distinguishes `corpus_status: not_configured`, `loaded`,
`unavailable` and `disabled` (health-only); `corpus_error` is a safe row/field reason on failure,
null otherwise. That reason is logged once at startup. `HEALTH_ONLY=true` skips all artifact/config
reads. The application logs no private path, parser exception or source text. `/health` stays degraded until the pipeline is integrated.

`ALLOW_PENDING_REVIEW=false` is the default. Only the owner-managed judging service may set it true.
`/health` always reports `allow_pending_review` and `pending_review_items` (the loaded count).
Future cards using pending evidence must visibly disclose the lack of specialist review in Arabic
with specialist-reviewed copy; see SPEC section 4.2. Enabling it permits only literal `pending` in addition
to `sharia-reviewer-1`; no `approved_by` value is changed. **G14 remains NOT MET** while review is pending.
Licensing, grading, integrity and downstream verbatim checks still apply. This flag implements no
quote or card generation and cannot authorize display of generated religious content.

The source register records scoped owner-reported challenge-app ingestion for `kfc-mushaf`,
`sahih-bukhari` and `dorar-hadith`; redistribution remains prohibited. All other permissions remain
unchanged. `python -m corpus.validate --private-use --allow-pending-review --corpus <private-path>`
checks such artifacts offline. Without `--private-use`, public-distribution validation still requires
redistribution permission. Runtime uses the explicit file loader and additionally checks
public-display permission for collection and grading sources. All current sources have `public_display_allowed: false`,
so use-only sources must stay out of the deployed artifact until the owner and specialist
resolve SPEC section 12 item 5. `ALLOW_PENDING_REVIEW` cannot bypass this permission.
Bukhari and Dorar publisher policy URLs remain pending; owner-decision self-links are separate
evidence and cannot replace `license_url`.

Run `python -m pytest`, `ruff check .`, `ruff format --check .`,
`node --test tests/*.test.mjs` and `python -m corpus.check_public_tree` from the repo root.
Tests use synthetic non-scriptural fixtures; no private artifacts or credentials are used by public CI.
