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

API INFO logging is configured automatically. One request summary reports request ID,
stage durations/outcomes, final states and failure categories; detailed stages use DEBUG. `/extract`
and `/check` responses include a server-generated `X-Request-ID`, also exposed
through CORS. Fixed stage/outcome labels and elapsed milliseconds correlate router,
composition, standalone extraction/classification and route failures. Correlation
propagates to parallel claim workers. No input, source text, model identifier, key,
provider body or exception text appears in these events. Validation failures use
fixed categories. Client-supplied request IDs are ignored and context resets after
each request. A route's elapsed time is observational, not an enforced deadline:
The enforced check deadline defaults to 60 seconds via `CHECK_DEADLINE_SECONDS`
(owner event `95cd2183a9bc20e7b241b27a8fbc7b920aacad0a744252e8b0bdd552837fa30f`,
superseding O4's 35-second default). Historical 503s remain unattributed without deployment
logs; these diagnostics must deploy before they can classify new live failures.

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
`store: false`, and no tools/conversation state. One HTTP client is shared for the
application lifetime and closed on shutdown. Router/extraction calls use explicit
`OPENAI_ROUTER_EFFORT=none` with a 15-second budget; composer/reasoning calls use
`OPENAI_COMPOSER_EFFORT=low` with a 25-second budget. Connect timeout is at most
5 seconds. Transient transport failures and HTTP 408/429/500/502/503/504 may retry
once within that budget. `Retry-After` seconds and HTTP dates are respected; if
the delay cannot fit, the call fails rather than retrying early. Refusals, incomplete
responses are never retried. Invalid JSON/sent-schema output may retry once inside
the same budget; transport and output retries share a maximum of two HTTP attempts.
Retrying a POST after a transport/read failure may bill both attempts. Returned
JSON is validated against the exact strict schema sent to the provider. String/array
lengths and patterns are removed from that schema and bounded locally before downstream
validation; enums, numeric safety thresholds and source-span checks remain fail closed.

GPT-6.1 Sol uses low effort if none was configured (no model substitution).
Startup uses a 16-token warm-up budget instead of the rejected 1-token request.
HTTP failures log status plus bounded OpenAI error.type/code/param identifiers,
never error.message or response text.

Startup warms the exact structured schemas with synthetic empty data, in parallel,
when both models are configured (router and decision schemas, plus the standalone
extraction/classification schemas). `OPENAI_SCHEMA_WARMUP=false` disables this for
offline tests; `HEALTH_ONLY=true` always skips it. Warm-up failure does not prevent
health service startup or prove readiness. Logs report only fixed failure categories,
never provider bodies or exception text. The server
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

`POST /api/v1/check` accepts `{"original_text":"..."}` without a prior `/extract`
call. The full original input (at most 12,000 Unicode code points) goes through one
strict router call for claims, exact source spans, premise, content level, domain
kind, topic IDs and proposed Quran references. There is no duplicate preflight,
second extraction, per-claim classification call or search-phrase model call.
Up to 50 accepted claims are composed in parallel (at most eight workers), in
source order. The composer selects candidate IDs and proposes a state; the existing
policy, provenance, scripture-span, grading, separation and alignment gates may
downgrade it, never upgrade it. Source text is copied by ID, never from model output.

Router claim spans are repaired, not trusted: a `source_text` that exists in the input
is located by search and its span corrected; a `source_text` absent from the input
marks the claim as ungrounded model text, whatever its origin, and the whole input
replaces it as one claim. Remaining shape problems (omitted multi-question context,
duplicate or mismatched claims, inconsistent term routing) get one model retry, then
fall back to one claim over the complete input (`router_validation`
`fallback_whole_input`). Shape problems never fail the request; only an unparseable
or unavailable provider response does. Evidence, state and referral gates are unchanged.

MCP discovery is off by default (`ENABLE_ISLAMIC_CONTENT_MCP=false`). When enabled,
it uses the approved endpoint. Network HadeethEnc runs only when no private hadith
path is configured and the router's input kind is
`hadith`, in parallel within a shared three-second budget (or the remaining request
budget, if shorter). Verse and term routes skip both. The HadeethEnc gate is the router
kind alone, not keywords in the query. Each adapter receives an isolated receipt scope;
late or failed batches cannot enter composition. Text-free request summaries record
`retrieval_mcp` and `retrieval_hadeethenc` timings, plus composer input scans,
gatekeeper checks, separation, dependencies, published answers, card validation, and
total post-provider time. The summary includes `active_stages` with elapsed
milliseconds for stages still running at the
HTTP deadline, including parallel composition workers and the evidence-copy
step immediately after `composer_gatekeeper`. These entries locate unfinished
work; they do not establish the cause of an earlier request from completed
timings alone. Successful private hadith startup logs the verified pinned
`sha256` and accepted record count after all artifact checks pass. The Render build
also checks the pinned hash and prints the checksum line before startup.
The summary also carries text-free integer totals (`proposed_refs` as the router's
raw nominations, `resolved_refs`, `lexical_hits_capped`
capped at 50, `compose_candidates`) and enum codes (`classifier:<status>` per claim,
then each card's abstain reason or state). These timings and counts identify work after
inference without logging user queries or source text.

BM25 indexes and queries use the `ar-search-v1` prefix aliases from #92. Overlap
counts each distinct query-word group once, even when several aliases match;
aliases never change corpus checksums, displayed text, or quote authorization.

Legacy `claims` requests remain accepted and are joined for the single router call;
when `original_text` is present it is authoritative. Client levels and deterministic
personal-case cues in client claims can only restrict the result. An entire request
with any level-D claim skips source dispatch and composition inference. Empty input
returns 400; invalid shapes return 422; router/infrastructure failures return 503.

The router owns topic selection: `search_queries` contains at most three closed
topic IDs. Under owner D1, low router confidence preserves the more restrictive
of the rule floor and explicit model level, plus nominations and queries. Only
deterministic personal-case rules or explicit model D / `level_d` restrict routing.
The composer still requires independent evidence confidence and all source gates.

The router's topic vocabulary contains at most three closed
`Topic` IDs and `safe_to_search` must be true. Code maps IDs through `TOPIC_QUERIES`
and rejects any full input or claim that appears in the built query. Unknown topics
authorize no source call. No free-text query is sent. Proposed Quran references and
private hadith search keys are resolved locally; only source-backed IDs authorize evidence.

SPEC 0.11 owner items O1/O2/O3/O5 remain open. Bayyinat is disabled; glossary matching
is off; term cards return CANNOT_CONFIRM with `term: null`, no evidence or definition,
and `glossary_link: "https://islamic-content.com/dictionary"` for the UI. Generated
explanations are dropped: both `explanation_ar` and `explanation_en` are null on the
one-pass path, which the card contract allows. Fixed referral/question fields remain.
No private text is sent for embeddings. O4's end-to-end deadline remains an owner
decision; V1's role-specific provider timeouts do not establish that guarantee.
This endpoint currently supports text only; upload segments/timestamps are deferred.

The composer reads state and alignment rules from policy. Models propose only
retrieved IDs, confidence and separate bridging prose. Evidence is copied from
loader-validated original records, with source reference and source grading.
Generated quotations or matching source excerpts are rejected. Quran near-misses
are associated only with the claim's original source span, including question
spans. Generated explanation and position fields require a completed detector scan;
error, timeout or unavailable scans fail the separation gate. Quran near-misses
against the whole index force CONTRADICTS; hadith near-misses instead show a sourced
wording notice. Unresolved detector/classifier/alignment, missing evidence, low
confidence and personal cases abstain with a referral and ready-to-ask question.
Unsupported glossary lookups carry `term: null`; the contract permits that only on
abstaining term cards. Approved translations are not attached in this first composer.
Arabic term labels must be exact substrings of loader-verified `text_ar`, selected
by a checked model proposal (or the extracted term itself). Definitions remain in
evidence. Both ordinary term fields require completed separation scans; known
scripture/quotes or scan failures abstain. English equivalents use checksummed
`text_en`; unverified extra `term_ar`/`term_en` record fields are ignored.
Every selected glossary evidence item requires a completed definition scan,
regardless of input kind or position in the selected records. Known hadith in
any selected glossary definition abstains because glossary records lack a
loader-verified hadith grading; comparison-record grades cannot authorize that quote.

`/health` reports card schema version 1 in verification mode.
Health returns `status: "ok"` when the nonempty corpus, policy, tuning and
required model configuration are available and any pending review is explicitly
accepted through `ALLOW_PENDING_REVIEW=true`. `review_mode` discloses
`owner_accepted_pending_review`, `pending_review`, `reviewed`, or `disabled`.
Pending item counts and policy reviewer fields remain visible. This configuration
check makes no provider/source calls and does not certify model performance,
source reachability or release approval. Missing models/corpus and health-only
mode stay degraded even when pending review is accepted.

Logs contain card counts/states only; no input, claims, source text or provider diagnostics. Services
and the local index are reused, while requests/results are not cached or stored.
Run the full Python suite and Node data-contract checks. Synthetic composer tests
exercise state rows, thresholds, whole-index twins, grading, isolation, errors and
the HTTP workflow; they do not establish religious accuracy or deployed readiness.
The request-scoped gatekeeper ships separately from the card contract below.

Abstention reasons follow known causes: after a completed scripture scan, a
confirmed personal-case classification retains `LEVEL_D_PERSONAL_CASE`; a
validated no-proposition question uses `NO_CHECKABLE_CLAIM`; no available
retrieval candidates uses `NO_MATCHING_EVIDENCE`. A failed/uncertain classifier
uses `LOW_CONFIDENCE` when candidates exist, and still prevents composition or
a supported/disputed result. An unresolved question subject is extracted as a
no-proposition question, rather than an invented topic. None of these reason
choices changes the evidence gates or expected evaluation states.

### Live-source card contract (SPEC §0.8)

Version 1 now accepts either the legacy local `corpus_id` or a live `source_ref`
`{source_id, record_ref, url}` on evidence and approved translations, never both.
Terms similarly use either `glossary_corpus_id` or `source_ref`. Local artifact
cards remain valid. An optional nullable `published_answer` contains exactly
`{source_id, title_ar, excerpt_ar, url}`; its excerpt is source text and must render
in the source block, separately from generated explanations. A published answer
also requires evidence carrying its provenance. Hadith grading stays mandatory.

This schema validates structure only. The gatekeeper must enforce same-request
origin, allowlisted source/URL, source_ref consistency and exact excerpt matching
against raw connector results. Synthetic contract tests do not establish those
properties. Consumers must support `source_ref` before live-source cards are enabled.

### Request-scoped quote gatekeeper (SPEC §0.4)

The text `/check` path now creates a fresh gatekeeper for each request. Its local
comparison index contains the loader-validated KFC Quran and Bukhari records;
eligible current-request source responses add to that index. The local index
must be available even when a connector returns evidence. Exact matches across
the full authorized set veto near-miss classification before either detector trigger runs.
Scripture records must pass the display reference/provenance checks and their own
hadith grading checks before entering that set. Rejected rows cannot suppress a
local Quran correction, even when independent FAQ evidence remains valid.
A separate embedded-text scan retains known rejected scripture. It cannot change
claim alignment or veto a local correction; instead it rejects affected excerpts
and glossary evidence, and replaces affected titles with the fixed source name.
Embedded scripture still requires an authorized own-record reference and grading.
Generated explanations, position labels/summaries and ordinary term fields also
use this completed safety scan; any finding or failed scan rejects ordinary text.
The separation check then looks each run of one to three consecutive words of the
text up in a chunk index built once per corpus (every record's 3-grams, or its whole
text when shorter), with the same glossary self-match exemption, instead of
re-tokenizing every record per explanation.
Hadith beyond the local records have comparison coverage only when returned by a
connector in the current request; this is partial coverage, not a full hadith index.

`SourceRequest.receive` is an internal connector boundary for parsed raw records;
neither HTTP callers nor models can supply it. Source requests are consumed once,
and a prior request's receipt is rejected. No live result enters a persistent
index or cache. Source/domain/HTTPS-host checks reject unknown, misleading or
disabled hosts. This module does not implement outbound HTTP/redirect/SSRF guards;
the connector transport must enforce those before handing it a response. icadb,
Bayyinat and unrecorded platform-result hosts stay disabled pending the spike.

Models select record handles only. Matching uses normalization, but displayed
quotes, provenance and grading are copied unchanged from the bound original.
This first adapter treats each connector text record as a source excerpt; arbitrary
model-written excerpts are not accepted. Failed quotes are dropped individually,
positions citing them are removed, and state/alignment are recomputed from survivors.
DISPUTED requires two surviving positions from different sources. No passing quote
means CANNOT_CONFIRM with a referral and ready-to-ask question.

Published-answer titles come from the same result as the excerpt. Unsafe scripture
or ungraded hadith in a title produces a neutral source-name fallback. An excerpt
with unverified/altered scripture or ungraded hadith is dropped. Embedded hadith
have their own source/grading shown as evidence, including on disputed cards.
Generated explanation scans fail closed on unavailable/failed detector runs.

The local index is built once. `QuoteGatekeeper.derive(request)` creates the
request-scoped gatekeeper by sharing the validated local records, their authorization
results and the two tokenized detector indexes, and processes only the records received
in that request; `SpanDetector.extend` adds those records without re-tokenizing the
corpus. Local records are never mutated after validation, so sharing them is safe, and
every verify/dependency/published-answer gate still runs per card. At the live corpus
size this removed about six seconds of per-request CPU (deep copies, one jsonschema
validation per record and two full tokenization passes) from the "retrieval" stage.
The app builds this index at startup when the private corpus loads, without touching
the provider, so the first request does not pay for it either.

Live connector fetching is not enabled by this PR. `/check` currently uses only the
mounted local artifact; a trusted connector adapter can supply a fresh SourceRequest
to CheckService when its separate transport and terms work is approved. Synthetic
tests cover request replay, source/metadata binding, titles, embedded grading, exact
twins, quote drops, positions and the real HTTP construction path. Production model
accuracy, the 12-case eval/CONTROL comparison and deployed readiness remain unmeasured.

## Arabic normalizer (normalizer portion of T-402)

R3 adds `corpus.retrieval_normalize.retrieval_token_groups` and
`retrieval_tokens` (`ar-search-v1`, MIT; no third-party Arabic package). These
search helpers retain each original ar-v1 word plus possible conjunction,
preposition and definite-article aliases, leaving at least three Arabic letters.
Groups let a matcher count one query word once; aliases are not independent
evidence. Initial letters may belong to the stem, so the original is retained.
R4/V3 opt in when building their indexes; legacy BM25 behaviour stays unchanged.
These helpers never rewrite question intent, display text, stored corpus keys,
checksums or the scripture comparison surface, and cannot authorize quotes.

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
`BM25Retriever.extend(records)` layers a request's received records on the shared
startup index instead of re-indexing the corpus: the base postings are shared read-only
(a term's postings are copied only when an added record extends them), and IDF and the
average length are computed over all records at query time, so scores, order and
overlap equal an index built from scratch over the same records.
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

Trigger B windows use an exact prefilter before any edit distance is computed. A near
miss within budget `b` differs in length by at most `b` and keeps at least
`len(window) - b` window tokens, so only records of a compatible length that share enough
of the window's rarest tokens (an inverted index over the detector's own comparison
tokens) are compared, in index order, so tie-breaking is unchanged; verbatim matches use a
dictionary lookup. The result equals the exhaustive scan for every window (randomized and
fixture tests compare the two). At about 9,700 records a 7-word question dropped from
2.4 s to under 10 ms and a 25-word explanation from 71 s to under 0.3 s. Marked spans
(Trigger A) keep the exhaustive scan because their UNRELATED distance is reported.
The window loop also checks the request deadline and raises `DeadlineExceeded` so a scan
abandoned by the HTTP deadline stops instead of occupying the CPU.

No model calls, logging, input storage, corpus ingestion, or HTTP endpoints are introduced.
Trigger B false-positive calibration remains unmeasured until licensed data exists (T-508a).
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
Oct 2 through Oct 6. The starting version for the Oct 4 evaluation window is
[`c2be3d45cee3321b0edadc7ff049ba33570eb6ad`](https://github.com/M7-KB/tabayyan/commit/c2be3d45cee3321b0edadc7ff049ba33570eb6ad),
the last commit on main's first-parent history before **2026-10-04 09:00 Riyadh
(06:00 UTC)**. Its commit time is 2026-10-04 00:10:59 Riyadh. This identifies the
pre-window work separately from later changes without changing the permitted Oct 2 start.
The existing `baseline` tag points to the earlier `daf18c6962064bdf85119d4566c9b9838585bcc8`
and is not the Oct 4 starting version. This disclosure follows the owner's Oct 5 instruction.

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

The page shows a development-preview banner until `GET /health` answers (`web/src/api/health.js`),
the input screen has the AI-not-a-fatwa notice as a pill under the tagline (always visible), a composer with
an icon-only send button, a collapsed privacy row under the composer (its short line is always visible), and
the source footer. The example chips render only when `strings.exampleChips` holds owner-approved entries; it is empty for now.
The upload consent checkbox gates the upload button. The upload form is hidden in this text-first build:
it sits behind `features.mediaUpload` in `web/src/config/features.js`, which is `false` by default. The audio
task sets it to `true`. With the flag off, the privacy notice covers text input only
(text first; audio/video and image input are not live yet, image input is P2). It says the text goes to
the AI provider, only the extracted search phrases go to approved sources (SPEC §0.6), we do not store
the text, and the provider may keep data briefly under its own policy. Submitting text calls
`POST /api/v1/extract`, shows the extracted claims for the user to confirm or edit, and only then calls
`POST /api/v1/check` (see "Text path wiring" below). The API origin comes from `VITE_API_BASE_URL`.

With `features.mediaUpload` on, a chosen clip is checked on the device (audio or video type, at most 25 MB)
and then handed to `transcribeStub` in `web/src/api/transcribe.js`. The stub returns labelled sample text and
never reads the file; it is replaced by the real `POST /api/v1/transcribe` call when Vegapunk's transcription
contract lands. The transcript opens on a review screen, where the user edits it, and nothing runs after it
until the user confirms. The privacy row then uses the clip wording (`strings.privacyLinesMedia`). Each
refusal or failure has its own Arabic message and a way back to the input screen. Fonts are self-hosted (`@fontsource/ibm-plex-sans-arabic`), so the page does not load
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

A published answer (`published_answer`, SPEC.md §0.5, §0.8) renders in its own block, `data-role="published-answer"`,
between the evidence and the generated explanation. It shows the link host as the source chip, the title, the verbatim
excerpt with the source line, and the link. Live evidence that carries `source_ref` instead of `corpus_id` renders the same
scripture block. The UI never shows a source name that the response does not carry.

Each scripture block sets the Arabic quote in Amiri Quran (`@fontsource/amiri-quran`, OFL 1.1; see SOURCES.md) and
ends with the source line from SPEC.md §0.7 (`strings.quoteSourceNote`), shown next to the source link.

The fixtures are synthetic. To preview them locally, run `npm run dev` and open `/#card-preview`. The
preview is compiled out of production builds. The state labels follow the SPEC.md §12 item 1 table; all
except `supported_contradicts` are provisional until owner and specialist approval.

Layout is mobile-first: the base rules are the 375px baseline, with a compact rule at 23.4375rem and below
and a desktop rule from 48rem that widens the reading column. Headless Chrome (puppeteer-core) on 2026-10-03
measured `scrollWidth` equal to the viewport at 375, 768 and 1280px, on the input screen and on the card preview
with a nested misquote notice (temporary fixture, not committed). No element extended past the viewport.
`web/src/__tests__/layout.test.js` only checks that the breakpoints exist. Label approval for the provisional
Arabic strings is still open (SPEC.md §12 item 1).

## Light and dark theme

The header toggle (`web/src/components/ThemeToggle.jsx`) switches between light and dark. With no saved choice the
page follows the system setting (`prefers-color-scheme`). A choice is saved only in `localStorage` under
`tabayyan-theme`; nothing is sent to a server. `web/index.html` sets `data-theme` before first paint, and
`web/src/theme.js` holds the same rule for the toggle.

Colours are tokens (`--c-*`) in `web/src/styles.css`. `:root` holds the light values, which are unchanged from the
previous palette. `:root[data-theme='dark']` holds the dark values from the owner brief (background `#0D1033`, surface
`#161B4A`, primary `#6A5AE0` with white text, accent `#38C8E8` for focus and rules, text `#FFFFFF`, muted `#B7BCE3`).
The four state badges have their own dark pairs. `web/src/__tests__/palette.test.js` reads the tokens from the CSS
and checks each text pair at 4.5:1 and each control or focus pair at 3:1 in both themes. Dark-theme borders
(`--c-border`, `#2A3170`) are decorative only: inputs and buttons use `--c-border-strong` for their edge.

Input-screen and card tokens: `--c-control-border` (borders, chip edges, icons, at least 3:1 in both themes),
`--c-gold` (arch line-art), `--c-send` with `--c-on-send` (send button), and `--radius-card` / `--radius-pill`.
Cards use `--c-control-border` and `--radius-card`; their layout is unchanged.

## Check client and results (T-504, part 1)

`web/src/api/check.js` builds and sends `POST /api/v1/check` (SPEC.md §3). In the one-page flow it sends
`{ original_text, locale }`: the text as the user typed it. The client sends no claims, levels or input kinds;
the server extracts and routes them. Every card is validated against `contracts/card.schema.json` with Ajv
(draft 2020-12) before it reaches the UI, including nested evidence and the misquote notice. A card that does
not validate is treated as `PIPELINE_DEGRADED`. `web/src/components/Results.jsx` shows loading, error (with
retry and edit), empty and card states; each error code has an Arabic message with a next step.

Ajv adds a runtime dependency to the web bundle. Arabic error copy is provisional until owner review.

## One-page flow (U1, feat/one-page-check)

`web/src/App.jsx` shows the input on top and the results below it. There is no claims page. A submit sends the
text once to `/check`. Each card starts with «فهمنا سؤالك هكذا:» (`UnderstoodClaim.jsx`), which shows how the
text was understood: `claim.text_ar`, the checkable premise, not the user's own wording. The user can edit that line and re-check only that card, in place. The edited text is sent
as `original_text`, and the card is replaced by the returned cards. A failed re-check keeps the card and the
draft. A re-check that returns no cards is `PIPELINE_DEGRADED`.

While a check runs, `web/src/components/CheckProgress.jsx` shows three stages and a cancel button. The stages
advance on a timer, because `/check` answers once. They are indicative and are not measured progress, and the
screen says so. Cancel drops the request and keeps the input text. A published-answer card shows the source
host, the excerpt, and the link «اقرأ الجواب كاملاً».

A term card with `glossary_link` (SPEC 0.11 O2) shows a link-only block: a link to the glossary and no copied
definition. A card with `explanation_ar: null` (SPEC 0.11 O3) hides the explanation block; the state, source
text, referral and «how to verify» remain.

The extract step (`web/src/api/extract.js`) is no longer called by the app. `EXTRACT_DEADLINE_MS` in
`config/api.js` is unused for the same reason. Both are kept until the server's one-pass `/check` is live; then
they can be removed.

Error states each give a next step: check errors have retry and edit actions, and `PIPELINE_DEGRADED` never shows
a partial result. Each check and re-check has a client deadline (`CHECK_DEADLINE_MS` defaults to 65 s in `config/api.js`,
build-time override `VITE_CHECK_DEADLINE_MS` in milliseconds).
At that deadline it shows the retryable message «لم يكتمل التحقق، حاول مرة أخرى» and keeps the input or
edited draft. An unfinished request is not labelled CANNOT_CONFIRM and does not imply missing evidence.
The response may include `retryable_results` alongside validated `cards`. Each unfinished item has
`claim_id`, `text_ar`, `code: CHECK_INCOMPLETE`, `retryable: true`, and `message_ar`. The client validates
that shape and uses fixed Arabic UI copy rather than displaying server diagnostic text. Completed cards
remain visible; unfinished claims appear in a separate status list with retry and edit actions. Retry
resubmits the original input, keeping completed cards and their open edits mounted during loading,
failure, timeout and cancellation. Only a successful response replaces the prior results.
HTTP 503 `CHECK_INCOMPLETE` uses the same incomplete message. If a card
re-check is incomplete, its previous card and edited draft stay visible until a complete retry succeeds.
The deadline ends loading even when the transport ignores abort. A newer attempt replaces an older one, and a late response from a timed-out, cancelled
or superseded attempt is dropped. Shared JSON posting and error codes live in `web/src/api/http.js`;
`CheckError` is an alias of its `ApiError`. The API origin comes from `VITE_API_BASE_URL`
(`web/src/config/api.js`), with no trailing slash. An empty value means same-origin requests. The preview banner
hides when `GET /health` returns 200 with a `status` field.

The client no longer checks that each card answers a confirmed claim, because the client no longer confirms
claims. That guard moves to the server's one-pass `/check`.

Tests: `web/src/__tests__/one-page-flow.test.jsx` covers submit, layout, the understood line, staged progress,
cancel, late responses, the empty, error and network states, edit and re-check in place, the empty-edit guard,
the client deadline and the preview banner. `check.test.js` covers the request shape and card validation.
`card.test.jsx` covers the glossary link-only fallback and the dropped explanation.
`extract.test.js` and `health.test.js` cover their own clients. All stub `fetch` per endpoint.

Live check on 2026-10-05 (before this change): `POST /api/v1/extract` and `POST /api/v1/check` on the Render API
returned 200, and the returned card validates against `contracts/card.schema.json`. The one-pass request is not
live until the server's V2 change is deployed; the current server still requires a `claims` list.

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
First-person family references (including English relative possessives) force D
when combined with case or ruling intent, such as contract validity, inheritance,
a private dispute, explicit first-person framing, advice requests or intervention
in a relative's conduct. A family reference alone still receives model classification;
general ethics and hadith questions are not forced to D by that word alone.
Arabic ability/possession framings and explicit personal worship/contract cues
continue to force D. Missing or uncertain model classification still refers.
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
- Plan: owner-selected paid instance through Oct 22 (owner decision 29); manual deployment.
  The blueprint omits `plan` so it does not pin the service to Free. Confirm the paid
  instance in Render before applying the blueprint; this repository change does not upgrade it.
- Branch: `main`.
- Build command: `python -m pip install .`, then `curl --fail` fetches the private Qur'an artifact
  `quran-kfc-v30-20261005.jsonl.xz` from `M7-KB/tabayyan-private-data` into `corpus/private/`,
  sending the read-only `PRIVATE_DATA_TOKEN` as a bearer token. An HTTP error stops the build.
  The build does not decompress or hash the file. A bad download can still finish the build; at startup
  the loader checks the manifest SHA-256 over the decompressed bytes and fails closed, leaving the runtime degraded.
- Dashboard env vars: `PRIVATE_DATA_TOKEN` (read-only; enter only in Render),
  `PRIVATE_CORPUS_PATH=corpus/private/quran-kfc-v30-20261005.jsonl.xz` (the path the build writes, relative to the repo root),
  `ALLOW_PENDING_REVIEW=true` (owner decision 30), `CORS_ORIGINS=[]` until the web origin exists,
  `PYTHON_VERSION=3.11.9`. `BUILD_SHA` is optional: when unset, `/health` reports the first seven
  characters of `RENDER_GIT_COMMIT`. Enter values only in Render.
- Corpus prerequisite: `HEALTH_ONLY=false`. `HEALTH_ONLY=true` skips all artifact reads, so the
  corpus does not load under it. The first deploy used `HEALTH_ONLY=true`. Health-only mode needs no
  `OPENAI_API_KEY`; the full API needs the provider keys.
- Health path: `/health`.
- Live health-only API: <https://tabayyan-api.onrender.com> (degraded, `corpus_items: 0`, build `f696a50`).
- Live web preview: <https://tabayyan.pages.dev> (development preview; verification is not active yet).
  Cloudflare Pages: root directory `web`, build command `npm run build`, output directory `dist`,
  `NODE_VERSION=22`, `VITE_API_BASE_URL` set to the Render API URL (no trailing slash).
- Smoke test after deployment (replace the URL):

```sh
curl --fail --silent --show-error https://YOUR-SERVICE.onrender.com/health
curl --silent --show-error --write-out '\n%{http_code}\n' -X POST https://YOUR-SERVICE.onrender.com/verify
```

Expect health HTTP 200 with `status: degraded`, `corpus_items: 0`,
`policy_approved_by: pending`, null version fields and the deployed `build` SHA;
`POST /verify` must return HTTP 404. These are the health-only expectations.
With `HEALTH_ONLY=false`, `corpus_status: loaded` is the success state; any other
`corpus_status` means the corpus did not load, and `corpus_error` gives the safe reason.

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
with no commentary copied. T11 records owner approval and binds the correction to
`quran:33:40`; its `g9_countable` is true and `blocked_reason_en` is null.
Its `needs_sharia_review: false` follows the schema's relation to `reviewed_by: owner`.
The owner approves test-set changes; other records retain pending review metadata.
T03 and T10 remain path stand-ins, excluded from G9 by `g9_countable: false`.
Countability does not establish a passing live evaluation. Sourced behavior and
corpus prerequisites remain separate requirements; this is not a
passing evaluation or the final 80–100-item set. See [eval/TESTSET_NOTES.md](eval/TESTSET_NOTES.md).

Run the complete local data-check suite with `node --test tests/*.test.mjs`
(Node.js 24, no packages). The explicit directory keeps frontend Vitest tests in
their own runner (`npm test` from `web/`).
These checks validate the draft's contract, exact T11 input and corpus binding,
Ramadan input digests and review safeguards; they do not run the model
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

T03 and T10 still carry `g9_countable: false`. T11's owner-approved data is countable and
requires `quran:33:40`, but the synthetic stub has no loaded Quran corpus. In that run T11's
required-ID assertion and case remain `not_evaluated`, its report excludes it from G9 and
execution/accuracy metrics, and G9 fails. Approving the input does not establish source
availability or a successful correction. The Python fixtures assert this for both unavailable
corpus and validated corpus missing the verse; no synthetic evidence is labelled as 33:40.
The run also fails if a brief case id is removed from the file. A
filtered `--only` run reports G9 as `not evaluated` rather than claiming coverage it does not have.

`eval/stubs/contract_pass.json` is a stub card source, not product behaviour: every card starts as
a `contracts/fixtures` card and the bundle only patches structural fields, so each Arabic string in
it is the fixtures' own synthetic placeholder text. No scripture, corpus record or glossary mapping
is authored there, and a passing stub run is evidence about the harness only. The harness runs
against the real API through `--api-base`; T-508 is the first full run and T-611 adds the control
arm.

## Plain-model CONTROL adapter (T-611)

`python -m eval.control` is an eval-only direct model client. Nami must review the
adapter before its first live run. It sends the exact unchanged question text with
the separate disclosed prompt:

> You are a helpful assistant. Answer the user's question in the user's language.

This follows the owner routing of 2026-10-05, Buzz event
`16253d6812979a1a337c342346571753123f901fbd45bf6454e6b4503551f242`, overriding
the earlier "same prompts" wording in SPEC §6.5. No corpus, source tools, gates,
Tabayyan API calls, JSON answer schema, or sourcing instructions are used.
The only network request is to the model provider. CONTROL answers never reach the UI.

After review, set `OPENAI_API_KEY` and select the same reason model used by the
comparison deployment through `OPENAI_MODEL_REASON` or explicit `--model`:

```bash
python -m eval.control --testset eval/testset.jsonl \
  --only T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12 \
  --output eval/private/control-brief.json
```

Question files may use the public testset shape (`case_id`, `input.text`) or private
held-out shape (`id`, string `input`). Private inputs and raw reports stay under
ignored `eval/private/`; after explicit owner approval, deliver H01–H10 to Nami by DM only.
Raw answers can themselves
repeat question details, so do not publish raw reports. Public comparison reports
contain aggregate rates and clearly labelled plain-model examples only, with the
adapter's comparison caveat. Reusing an output file is refused before any call.

Each private report logs the exact prompt and hash, question-file hash, requested
and returned model identifiers, request settings, latency, provider status and usage.
Errors have fixed labels and omit provider diagnostics. No retries are made; timeout
defaults to 60 seconds per request. Refusals and partial answers are preserved for
review. Exit `0` means requests completed, `1` means a request failed, and `2` means
setup failed. These are transport outcomes, never safety scores or release gates.
Classification accuracy, abstention precision/recall, fabricated-source rate and
unmatched quotes remain `null` until Nami evaluates them. A provider refusal is not
automatically a correct abstention. No inference results are claimed by this adapter PR.

**Comparison caveat:** this compares whole systems with different prompts and does
not isolate retrieval's effect. Verify the returned model against the deployment's
model before interpreting differences. Quote verification may read the private Quran
artifact in a separate evaluation step; it never supplies context to CONTROL.
Provider `store: false` disables response application-state storage; it does not
establish zero retention. See the [official Responses migration guide](https://developers.openai.com/api/docs/guides/migrate-to-responses)
and the existing provider privacy disclosure above.

## Private corpus file and pending review

The built JSONL artifact is no longer uploaded as a Render Secret File. The build fetches it
from the private repository (see First Render API deployment) with the read-only `PRIVATE_DATA_TOKEN`,
and `PRIVATE_CORPUS_PATH` points at the path the build writes. The file stays XZ-compressed below
1,000,000 bytes (Render's 1 MB cap, owner decision 29). Commit only
`corpus/manifest.json` with exactly `{"sha256": "<64 lowercase hex digits>", "corpus_version": "v1"}`;
the SHA-256 is over the complete **decompressed JSONL bytes**, including line endings,
not the compressed bytes. XZ and gzip are recognized by magic bytes; plain JSONL remains
supported for local use. The v30 handoff compresses to **975,592 bytes** with stdlib
LZMA preset 9 (9,576,033 decompressed bytes; manifest SHA-256 unchanged).
`CORPUS_MANIFEST_PATH`
can override that public manifest path. The read token is the only credential for this path;
it is entered in Render and never committed.
The v30 checksum-only manifest is committed. Keep real artifacts under `corpus/private/` locally; built JSONL,
raw files and indexes are ignored and checked for accidental tracked files in CI.
The guard covers alternate JSONL names and backups, corpus build directories, data JSONL,
and index/embedding/database extensions even when force-added. Public corpus code/docs,
`approved_sources.json` and the checksum-only `manifest.json` are allowed.

Startup bounds file reads and decompression to 64 MiB, rejects compressed artifacts at or above
1,000,000 bytes, and caps the XZ decoder's memory at 128 MiB. It validates the same
decompressed bytes it hashed. Malformed/truncated streams, XZ trailing data, expansion
beyond the limit, and hashes of compressed bytes fail closed. All rows must pass before any
records reach app state. Missing files, hash mismatch or an invalid row leave `corpus_items: 0` and
`corpus_version: null`. `/health` distinguishes `corpus_status: not_configured`, `loaded`,
`unavailable` and `disabled` (health-only); `corpus_error` is a safe row/field reason on failure,
null otherwise. That reason is logged once at startup. `HEALTH_ONLY=true` skips all artifact/config
reads. The application logs no private path, parser exception or source text. `/health` stays degraded until the pipeline is integrated.

KFC rows require both `aya_text_emlaey` and `aya_text_unicode`, with their separate
UTF-8 checksums and matching `corpus_id`, `ref`, `sura_no` and `aya_no`. Retrieval
and claim matching use the standard spelling; evidence and corrections copy the
same row's Uthmani display bytes, including its end-of-ayah mark. Display spelling
also enters the safety scan so generated explanations cannot reproduce it.
Pair checks bind the manifest-authorized row; they do not independently verify the
publisher's original file or establish permission beyond the source register.

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
public-display permission for collection and grading sources. KFC and Dorar hadith permit
matched public display under the 2026-10-05 owner scope below. Sources or grading records
without recorded display permission stay out of deployed artifacts; `ALLOW_PENDING_REVIEW`
cannot bypass that permission. SPEC section 12 item 5 is resolved; no specialist approval
is required for this display decision.
Bukhari and Dorar publisher policy URLs remain pending; owner-decision self-links are separate
evidence and cannot replace `license_url`.

Run `python -m pytest`, `ruff check .`, `ruff format --check .`,
`node --test tests/*.test.mjs` and `python -m corpus.check_public_tree` from the repo root.
Tests use synthetic non-scriptural fixtures; no private artifacts or credentials are used by public CI.

## Owner display scope and Quran-only artifact (2026-10-05)

The 6,236-record private v30 artifact is built and verified. Its committed checksum-only
manifest and [handoff](docs/QURAN_V30_HANDOFF.md) record both raw and derived hashes,
field mapping, licence limits and deployment prerequisites. The field-binding PR must
land before this artifact is used for live display.

The owner permits matched verses, hadith, gradings and short excerpts in the deployed
challenge app with visible source and link; no bulk display, download or file redistribution.
See [SOURCES.md](SOURCES.md#owner-public-display-decision-2026-10-05) for evidence and limits.
KFC and Dorar display flags are true; source binding and grading checks still apply.
The local artifact is KFC standard-Unicode Hafs v30 only: match `aya_text_emlaey`,
display `aya_text_unicode` of the same `(sura_no, aya_no)` record, unchanged including
the end-of-ayah mark. Hafs Smart and the four local Bukhari records are dropped.
There is no local hadith index; same-request Dorar results provide partial coverage,
so unmarked hadith outside those results may go undetected. Until the live Dorar
connector lands, hadith claims abstain with referral. The binding implementation and
Render switch remain separate reviewed work. Records keep `approved_by: pending`,
with `ALLOW_PENDING_REVIEW=true`; owner review is recorded in handoff metadata.

### Direct Islamic Content MCP connector

The default `ISLAMIC_CONTENT_MCP_URL=https://mcp.islamiccontent.org/mcp` enables
request-local Arabic library discovery on `/api/v1/check`. An explicit empty value disables
it. Other URLs are refused. The application calls MCP directly; no model-side MCP
or generated search summary supplies evidence. Server classification runs first;
personal cases, unavailable classification and term lookups skip discovery.
An additional structured-model step selects at most three topic IDs from a
closed vocabulary in `api/search_phrases.py`, derived from the challenge brief's
generic domains and glossary. An independent code mapping supplies each fixed
Arabic search phrase; no model-provided phrase or user substring is transmitted.
Unknown IDs, names, private-context tokens, invalid/unavailable proposals and
queries containing a complete claim skip discovery. The model's safety flag
cannot bypass the closed mapping. Full input/claims never serve as fallback
queries. Queries remain request-local. This conservative vocabulary limits
retrieval coverage: unlisted topics abstain through existing evidence gates;
additions require code review. Topic selection quality still requires live eval.

One search selects at most two Arabic library item IDs. Each selected item is
read in the same request. Only the publisher's bounded `[COMMENTARY]` section,
with the exact same canonical item URL, can enter `SourceRequest`. Search titles,
wrapper instructions, attribution blocks, attachment URLs and model prose are
never quotes. The gatekeeper checks source identity, verbatim text and embedded
scripture against the local Quran and current-request evidence. The local Quran
comparison set is retained. No response or user query is cached or written.

`IslamicContentConnector.verse(surah, ayah, request)` also reads one QuranEnc
verse/translation through the hosted `get_quran_verses` tool. It copies the raw
Arabic and English lines from the source's `[EXACT]` section as source evidence,
outside generated explanations. This explicit-reference method is not yet
automatically selected by `/check`. It never replaces the local KFC Quran.

The fixed-host TLS transport pins a public DNS address, refuses redirects,
compression, oversized responses, mismatched RPC IDs, duplicate JSON keys and
MCP errors. Search and item reads share a ten-second deadline, including DNS,
connect, TLS, headers and body. Failed batches contribute no partial evidence.
Missing source text falls back to the existing abstention/referral path; valid
local Quran evidence can still be checked.

Coverage limitation verified against the hosted tool list: dedicated Byenah and
IslamEnc general-content tools are absent. The hosted Quran tool links to
IslamEnc, and its library tool links to IslamContent/IslamHouse. These are not
evidence of Byenah or general IslamEnc question coverage. Those paths remain
unavailable and must abstain; no guessed endpoints or scraped pages are used.
Term definitions remain unavailable. Provider outages and production quality
metrics still require live evaluation; synthetic tests do not establish them.

### HadeethEnc item connector and Render Dorar smoke

`api.hadeethenc.HadeethEncConnector.receive(item_id, source_request)` fetches one
Arabic item from the official API and adds its raw text, source link, reference,
and unchanged grade to that request's quote gate. Missing grading means drop.
`grader_ar` identifies HadeethEnc; it never impersonates Dorar. If separately
received Dorar evidence is supplied in the same request, each evidence item keeps
its own grading and source; the adapter never replaces or ranks them.

`api.hadeethenc_discovery.HadeethEncDiscovery.discover(query, source_request)`
adds bounded discovery through the [official category and item-list API](https://github.com/islamhouse-dev/hadith-api).
It reads Arabic category metadata, selects one category by normalized title-word
overlap, reads only its first page (20 items), and fetches at most two matching
items through the existing adapter. Only IDs returned by that page are used.
Titles and category metadata never become evidence; only full item responses
enter the request's gatekeeper. Every accepted item carries internal
`grading.grading_source_id: hadeethenc`, alongside the unchanged grade and link.
The public card retains its existing three grading fields.

This is lexical category browsing, not semantic search. It may miss relevant
items in another category or page; missing, malformed, duplicate, ungraded or
unavailable results provide no evidence and must abstain. At most four calls
occur per discovery invocation, each with the existing transport deadline and
byte cap, with no retry or automatic pagination. The host/path pairs are fixed.
Call only for non-personal hadith retrieval before the source request is consumed.
The default `/check` route calls this adapter for minimized phrases containing
an explicit hadith topic (`حديث`, `الحديث`, `احاديث`, `الاحاديث`, `hadith`,
or `hadeeth`). The approved fixed topic mapping supplies that routing cue; no model-written
phrase reaches either adapter. MCP library discovery
runs alongside it; health/extraction routes never call source APIs. Both adapters
share the same request-local source scope before quote checking consumes it.
Personal cases, term lookups, unavailable classification and failed phrase
extraction reach neither source. Each adapter's existing request limits remain:
MCP has one shared ten-second deadline, while HadeethEnc has up to four source
requests with individual transport deadlines. These and sequential model calls
can exceed the eval client's default thirty-second wait. Independent outages
contribute no evidence from the failing adapter; existing quote/state gates and
expected states are unchanged. This wiring has offline transport/route coverage;
Render reachability and live model quality require a separate deployed check.
No HadeethEnc response or user query is saved. Explanations remain model prose
under the existing separation gate; quoted source bytes never adapt to the asker.

Transport uses exact fixed hosts and paths, public-only DNS results pinned to the
connection IP with source-host TLS verification, no redirects/proxies/retries,
a 256 KiB response limit, and a shared 10-second deadline. The remaining budget
is applied at TCP connect, TLS handshake, request send, and every socket receive,
including receives inside header parsing and buffered body reads. Slow drips do
not renew the budget. DNS resolution uses the system resolver and cannot be
interrupted by this transport; exhausted DNS time prevents a connection.

After the reviewed owner Render switch, run **once in the Render Shell**:

```sh
python -m api.dorar_smoke
```

It refuses to call outside Render (`RENDER=true`), makes one Dorar request with
the non-user search key `test`, and prints only environment, attempt status,
HTTP status and whether an object-shaped JSON response was returned. It stores
no response text. A successful JSON probe does not establish usable hadith or
grade parsing, retrieval quality, or end-to-end card correctness. This command
ran once from Render on 2026-10-05 (owner decision 31): `dorar.net` returned HTTP 403 with no
JSON (`attempted: true`, `json_response: false`). Dorar is disabled. Hadith comes from HadeethEnc
only; until a HadeethEnc result returns, hadith claims abstain with referral.

## Bounded connector spike (2026-10-05)

R4's [private matcher integration](docs/PRIVATE_INDEX_MATCHERS.md) describes
in-memory Bayyinat/glossary candidate retrieval with BM25 and 1024-dimensional
OpenAI embeddings. No query/index cache is written, level D does not retrieve,
and candidate scores never authorize evidence. V5 opts these matchers into the
one-pass API with a checksummed v2 owner handoff. Live/held-out retrieval evaluation
still requires the owner's artifacts and deployment.

R2's [private short-index handoff](docs/PRIVATE_SHORT_INDEX_HANDOFF.md) describes
loading owner-collected Bayyinat/glossary files with trusted SHA-256 values and
source permission gates. No public source data is added. Loaders do not enable
the API automatically; actual coverage awaits owner collection and inspection.
Set `PRIVATE_SHORT_INDEX_DIR` to the directory containing `manifest.json` and
the v2 JSONL files. Set `PRIVATE_BAYYINAT_SHA256` and/or `PRIVATE_GLOSSARY_SHA256`
to trusted checksums supplied separately by the owner. An unset checksum leaves
that source disabled. No private artifact paths or hashes are inferred, and this
change does not fetch files during the build. The owner supplies them privately.
Set `OPENAI_MODEL_EMBED=text-embedding-3-large` explicitly; the live adapter reads
the model and key from settings, and refuses any other embedding model for this
1024-dimensional index contract.
The complete-manifest, scoped-permission, checksum and review gates run before
startup embeddings. A configured invalid artifact or embedding failure disables
that source and degrades health; `/health` reports fixed source statuses/counts.
The owner-authorized pending-review mode is `ALLOW_PENDING_REVIEW=true`.
Completeness is per source: the owner assembles the directory with
`tools/source-collector/build-short-index.mjs --glossary RUN [--bayyinat RUN] --output DIR`,
which verifies each JSONL against its run manifest and writes one manifest listing only
the two files with per-source `status`. A `partial` source (a run stopped at its page
cap) loads only with `PRIVATE_SHORT_INDEX_ALLOW_PARTIAL=true`, and `/health` reports it
as `partial` with its count; each source loads independently of the other. The Render
build fetches `short-index/{manifest.json,glossary.jsonl,bayyinat.jsonl}` from the private
data repository into `data/private/short-index/` (missing files are reported, not fatal),
so `PRIVATE_SHORT_INDEX_DIR=/opt/render/project/src/data/private/short-index`.

Only routed doubts use Bayyinat and only routed term requests use the glossary.
Level D skips both. Retrieval has a 3-second cap within the configured request
deadline; failures produce retryable unfinished results. Candidates are bound to
the current request and still pass the existing verbatim, embedded-scripture,
grading, alignment and confidence gates. Query embeddings are transient.
Private candidates retain the measured lexical overlap floor; only resolved
router Quran references receive the existing D2 question exception.
Bayyinat indexes title, question, keywords and detailed answer; display copies
the summary unchanged, or the first paragraph of the detailed answer up to
400 characters with no added ellipsis. A leading section label («الجواب
التفصيلي», «الخلاصة», ...) is skipped, the excerpt stops before «المراجع» or
«الآيات التي وردت», and the cap falls on a sentence end (or the last whitespace)
inside the limit. Paragraphs end at a blank line; internal line breaks are
copied as line feeds. Glossary indexes term, short explanation
and verbatim translation-list items; its display field is terminological meaning.
The list has no verified English-equivalent mapping. Until that contract exists,
term cards retain abstention and the glossary link; no `term_en` is generated or
inferred from language names. Private contents never enter the public repo.

The owner-run [R1 collection command](docs/OWNER_SOURCE_COLLECTION.md) collects
Bayyinat and the approved dictionary into private JSONL with SHA-256 manifests.
Agents do not run it. The tool is separate from the API/build; live extraction
coverage awaits the owner's output and page inspection. R2 loaders and R4
matchers remain separate work. Private collection does not authorize public
redistribution; source permission evidence remains in SOURCES.md.

The [HadeethEnc owner-run command](docs/OWNER_SOURCE_COLLECTION.md#hadeethenc-owner-run-private-index-r2)
creates JSONL plus a SHA-256/count manifest from the official API. Owner decision
D4 permits one owner-run fetch, stored only in the private repo, with verbatim
fields and attribution to HadeethEnc.com; it supersedes the earlier collection
restriction in [SOURCES.md](SOURCES.md#hadeethenc-owner-run-private-index-2026-10-06-decision-d4).
Agents do not run it. Inspect the report and empty-field counts before handoff.
Pagination ambiguity or a non-string item field makes the manifest partial. Resume
recovers an interrupted final JSONL append; corruption earlier in the file is refused.
Null optional attribution, grade, reference or explanation is retained as an empty
field and counted in the manifest; it does not authorize evidence display.

The [measured source/API spike](docs/CONNECTOR_SPIKE_20261005.md) records two OpenAI
calls and bounded direct probes, endpoint shapes, one-sample local latency and terms
links. [TOOLS.md](TOOLS.md#bounded-connector-spike-and-quran-handoff-2026-10-05)
records verified provider model use. Dorar returned 403 from the local machine and from Render
(2026-10-05), so Dorar is disabled. The five-call terminology follow-up identifies
icadb collection metadata but no verified term response; cases 7, 8 and 12 retain
the owner's abstention with a glossary link. MCP language access worked, terminology coverage
is unverified, and web-search citations alone do not provide raw verbatim evidence.


### Check deadline and unfinished results

`/check` has a 60-second orchestration and HTTP deadline by default, configured
with `CHECK_DEADLINE_SECONDS` (a finite positive number of seconds). Provider retries
share its remaining budget. Completed evidence cards stay in `cards`; unfinished claims are returned in
`retryable_results` as `{claim_id, text_ar, code: "CHECK_INCOMPLETE", retryable: true,
message_ar}`. They have no evidence state and are never converted to CANNOT_CONFIRM.
A routing timeout, before claims are known, returns HTTP 503 with error code
CHECK_INCOMPLETE. The client defaults to 65 seconds, with build-time override
`VITE_CHECK_DEADLINE_MS` (finite positive milliseconds; invalid values use 65000).
Keep the client at least five seconds above the configured server deadline.
This margin does not increase provider or retrieval budgets or relax evidence gates.
Running synchronous operations cannot be forcibly interrupted; the response stops
waiting at the deadline and cancels queued work. Provider calls inherit the absolute
deadline, and late worker results are discarded without persistence. CPU-bound stages
cooperate: the scripture-span scan checks the deadline per window and raises
`api.deadline.DeadlineExceeded`, which the composer's separation and embedded-quote
scans propagate rather than swallow; the one-pass service reports such a claim as
`CHECK_INCOMPLETE` (or a routing-stage 503), so a worker still running at the
deadline releases the single vCPU for the next request instead of starving it.

The HTTP deadline owner shares request-local progress with claim workers. Each
validated card is registered immediately on completion. If the outer timer wins
before the orchestration response is serialized, it snapshots those cards and
returns known unfinished claims in retryable_results. A generic 503 is used only
before claims are known. The snapshot is sealed, ignores late results, and exists
only in request memory; it is never cached or logged.

### Local Quran nominations and question intent

The router's proposed_quran_refs are resolved only by verse key in loader-validated
local KFC records and added to each claim's candidates, even without BM25 overlap.
Each claim sends its nominations plus the top `COMPOSE_POOL` (three) lexical hits to
compose; the top fifty hits are counted for diagnostics only.
Nominations retain their measured retrieval score. For non-stated question cards, a
resolved KFC nomination cited by the composer skips only the lexical alignment
threshold (owner D2); candidate-ID, source-binding, span, confidence and alignment
proposal gates still run. Stated quotes retain the lexical threshold.
Router schema failures repair individual fields with conservative defaults; unknown
topics and malformed/out-of-range Quran refs are dropped individually (owner D3).
Repair validation has a fixed attempt cap; fallback claim and premise fields are
bounded to 12,000 characters, including legacy claim lists joined with newlines.
If a fallback input exceeds that limit, only its first 12,000 characters are kept;
the fallback truncates without adding a notice to the response.
Request summary codes record fixed router field names and alignment gate outcomes,
never model values, source text or user text. Provider failures remain distinct.
Missing or wrong-source nominations are ignored. Level D skips this retrieval.
For a single question_subject, code retains the full original input, including
context before and after the question mark. Valid complete spans are never shortened.
Multiple questions retain complete supplied spans only when those spans cover all
non-whitespace input context; ambiguous subject-only spans or omitted conditions
fail closed before retrieval. Punctuation is not used to guess context boundaries. Presuppositions
still follow the misconception path. Referral ready_to_ask_question_ar includes the
user's original question, without a generated answer or generic substitute.

The closed MCP Topic Literal has 60 fixed public subject IDs covering the brief's
Quran, hadith, creed, fiqh, history, ethics, doubts, dialogue and terminology domains.
The three-topic cap, complete-claim overlap veto and level-D dispatch prohibition
remain enforced. No free-form model/user query reaches MCP.

The [reference-pack translation](docs/challenge-brief.md#reference-pack-pages-815-association-platforms-and-external-sources-working-translation) records pages 8–15 of the public challenge document. It distinguishes the association books platform `byenah.com` from the Osoul Center Bayyinat web edition `bayenat.net`, which the owner-run collector targets. The owner authorized publication of the translation; the reference PDF will be supplied separately under `docs/reference/`.

The [owner collection guide](docs/OWNER_SOURCE_COLLECTION.md) documents Bayyinat `/ar/categories/{cat}` and `/ar/category/{cat}/{id}` routes, exact glossary headings, bounded same-host redirects and offline `--from-html` re-extraction with snapshot hashes. Output uses the owner-approved v2 fields. V5 runtime loading selects `expected_format_version=2`, preserving fields and translation list items unchanged; v1 offline callers remain supported. The translation section uses «ترجمة هذا المصطلح متوفرة باللغات التالية» and keeps its list items verbatim. The synthetic collector-to-loader test covers approved routes and refusal to fetch English selectors.

## Local HadeethEnc index and D7 (2026-10-06)

Set `PRIVATE_HADITH_PATH=/opt/render/project/src/data/private/hadeethenc.jsonl`
in Render. The build command uses the existing `PRIVATE_DATA_TOKEN` to fetch
`hadeethenc/hadeethenc.jsonl` and `hadeethenc/manifest.json` from the private repo.
No publisher collection runs in the build. The loader checks the uncompressed
bytes at startup against owner SHA-256
`1e0a79c49b0287a6ea33826dde1996bd465c81490f59c0050444b6241f9b2ae6`,
10,302,934 bytes, 3,574 records and the complete manifest. Version: 2026-10-06.
No raw fields, paths or parser payloads enter diagnostics. Health adds
`hadith_status`, `hadith_error`, `hadith_items` (display-eligible rows) and
`hadith_version`. A configured but invalid file disables hadith evidence and
marks health degraded. Remove the env var to enable the existing network
HadeethEnc fallback under its shared three-second budget.

Local BM25 indexes hadith text only. Router `proposed_hadith_phrases` are bounded
internal search keys; they never reach a response, log, evidence field or network
query. Hadith composition uses one ID-only `OPENAI_MODEL_REASON` decision with
`meaning: yes/no/unsure` and confidence. Missing metadata, weak/ambiguous grades,
unknown IDs, low decision confidence, no/unsure, and levels C/D cannot support D7.
Only publisher labels صحيح / حسن (also bracketed) qualify; no grade is inferred.

Code copies source text, attribution, reference, grading and link verbatim.
Exact source text retains CONFIRMS. A meaning-only match has SUPPORTED /
SAME_MEANING / `supported_same_meaning`, a referral, and `hadith_caution_ar`.
The UI label for that key is «لم نجد لفظك حرفياً؛ هذا حديث صحيح بمعنى قريب».
User wording remains input, never the displayed hadith. MCP stays disabled unless
`ENABLE_ISLAMIC_CONTENT_MCP=true`; its endpoint still must match the allowlist.
These are engineering gates, not a claim of live semantic accuracy; deployment
and Nami's fabricated/weak-hadith red team remain required.

## Twelve brief cases: sourced answers instead of false abstentions (2026-10-06)

The one-pass check now returns the behaviour the brief's twelve cases expect
whenever the matching approved source is loaded, and abstains honestly otherwise.
The invariant is unchanged: every quote, grading and reference on a card is copied
by ID from a loader-validated local record or a record received in the same request.

- **Explanations are shown.** A card with evidence keeps the model's bridging
  explanation, cut to three sentences in code, after the separation scan. If the
  scan rejects the explanation (a reproduced source chunk, a quote marker, or an
  incomplete scan), a fixed note replaces it and the verified evidence stays; a
  position label or summary that fails still abstains the card. Abstaining cards
  carry a fixed sentence that says what was not found: a hadith request states that
  no authentic matching hadith was found and nothing is attributed; an unspecified
  matter asks which matter is meant and asserts no agreement or disagreement; a
  personal case gives the general information that such matters go to a qualified
  fatwa body. None of these sentences quotes a source or states a ruling.
- **Misquoted excerpts are corrected deterministically.** A marked quotation (quote
  marks, ornate brackets or an attribution formula) is also compared with windows
  inside longer records: an exact window anywhere in the index is VERBATIM, a window
  within the ordinary word budget is a NEAR_MISS (five tokens or more). A Quran near
  miss on the claim decides the card without a model call: the correct ayah is copied
  by ID with its surah and ayah, the state is SUPPORTED / CONTRADICTS, and a fixed
  sentence says the quoted wording differs and nothing is built on it. Unmarked text
  keeps the whole-record scan.
- **Fewer drop conditions.** The policy's state rules decide the state from verified
  evidence; the model's proposed state is advisory except its own CANNOT_CONFIRM. The
  lexical overlap floor applies to stated quotations only; a question's evidence is
  selected by ID and judged by the alignment proposal and its confidence, which also
  covers private Bayyinat candidates. The compose pool is five records. A glossary
  record whose term or approved equivalent the text names is a candidate even without
  lexical overlap, and a term label may equal the record's term. A glossary record
  without a publisher-supplied equivalent still shows its definition as evidence; the
  term block appears only with an equivalent (the card schema's term rule allows a
  null term on such a card). The local hadith path applies the overlap floor before
  the meaning decision.
- **Web.** A re-check that returns some cards and some unfinished claims keeps the
  cards instead of reporting an error.

`tests/test_twelve_cases.py` drives the twelve inputs (and the misquote shape with a
synthetic record) through the HTTP path with a scripted model and synthetic records,
asserting state, alignment, referral, explanation, term and that every displayed quote
equals a loaded record. No glossary or doubt text is in the public tree: cases 1-4, 9
and 10 cite Bayyinat and cases 7, 8 and 12 cite the glossary only when the owner's
private v2 indexes are configured (`PRIVATE_SHORT_INDEX_DIR`, `PRIVATE_BAYYINAT_SHA256`,
`PRIVATE_GLOSSARY_SHA256`, `OPENAI_MODEL_EMBED`); without them those cases ground on the
loaded Quran and HadeethEnc records or abstain with a referral and the glossary link.

### Publisher answers from the private indexes (2026-10-06, owner decision)

A record received from the owner's private Bayyinat or glossary index that answers
the asked question is the approved doubts or terminology source for it: a Bayyinat
answer matched by title, question text and keywords (BM25 plus embedding) that the
model selects, or a glossary record whose term the text names. Such a card is
SUPPORTED with the publisher's «الخلاصة» (or 400-character first paragraph) as the
published answer, or the glossary definition as evidence, at any level including C,
without a second position and without a model alignment proposal (the proposal only
chooses the label: CONTRADICTS for a false premise, otherwise CONFIRMS). The card
schema's level C rule allows this only when a published answer is present. A model
CANNOT_CONFIRM that still selects such a record does not abstain the card. Every quote
is still copied from the record by ID through the gatekeeper; the model writes no
definition or answer. A term card shows the glossary link block only when no
definition is shown; its term block uses the publisher's `text_en` or the publisher's
own English translation list item verbatim (a bare language name is not an
equivalent), and an unattested label drops the term block, never the definition.
«فهمنا سؤالك هكذا» shows the user's own words for questions; a router premise is a
retrieval key only. Web: the same-meaning hadith badge has a label, long hadith
references collapse behind «المراجع», a glossary definition is labelled
«الجمهرة: <term>», and a fresh submission never shows an earlier question's cards.

Freeze fixes (2026-10-06):

- **One state per card.** A card that displays published evidence is SUPPORTED or
  DISPUTED; a CANNOT_CONFIRM card has no evidence and no published answer, on every
  abstain path (the card schema enforces `evidence: []` and `published_answer: null`
  for CANNOT_CONFIRM). A misquote notice is a correction, not evidence, and stays.
- **Title-matched publisher answer.** When a received Bayyinat record's title names
  the asked subject (at least 60 % of the question's content words, interrogatives
  dropped, at least two words, inflected forms counted by a shared four-letter stem),
  the model's low confidence, evidence gap, CANNOT_CONFIRM, undetermined alignment or
  a provider failure no longer abstains the card: the publisher's answer is shown as
  SUPPORTED with the fixed no-explanation note instead of generated prose, and the
  proposal's alignment (if any) only chooses the label. Without a matching title the
  block stands. The record is still copied by ID through the gatekeeper.
- **Labels.** A Bayyinat card is labelled «بينات: <question title>» and a glossary
  card «الجمهرة: <term>» (the page path is the link, not the label). The published
  answer is shown once per card: the evidence block of the same record is not repeated.
- **Quran nominations.** The router prompt states that `proposed_quran_refs` is
  independent of the input kind, and `"33:40"`-style strings are repaired to
  surah/ayah pairs; a nominated ayah still resolves only in loaded KFC records.
- **Complete questions.** NO_CHECKABLE_CLAIM is kept only when the input's subject is
  a placeholder («هذه المسألة», «كذا»); a complete question the model marked as
  term_lookup is checked as a question.
- **CPU.** The scripture scan of one displayed excerpt runs once per request
  (verify, dependencies and published answer share it), and Bayyinat excerpts are
  capped at 400 characters; a Bayyinat card no longer scans the whole detailed answer
  several times.
