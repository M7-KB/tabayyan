# SPEC.md — Tabayyan (تبيّن)

Status: approved by the owner on 2026-10-01. §5 carries the owner's approval and is still pending final Sharia specialist review.
Owner of this document: @Luffy (lead)
Last updated: 2026-10-01
Source of truth for requirements: `docs/challenge-brief.md`
Owner decisions folded into this document are listed in §10.

---

## 1. Scope

### Problem
A user hears or reads a religious claim and cannot tell whether it is grounded in an approved source. Tabayyan checks claims from Arabic text, a link, or short audio (≤ 3 min) and returns one evidence card per claim, each card traceable to an approved source, or an explicit abstention.

### In scope for the build window (Oct 4 09:00 → Oct 6 23:59, Riyadh)

Priority order. Everything above the cut line ships; items below are cut first if we are behind.

| # | Capability | Priority |
|---|---|---|
| 1 | Text input → claim extraction → level classification → retrieval → evidence cards | P0 |
| 2 | The three card states (SUPPORTED / DISPUTED / CANNOT_CONFIRM) with verbatim quotes and visible sources | P0 |
| 3 | Verbatim gate and scripture/explanation separation enforced in code, not in prompts | P0 |
| 4 | Arabic RTL web UI with the AI-not-a-fatwa notice on every result view | P0 |
| 5 | Approved corpus v1 covering all 12 required brief test cases | P0 |
| 6 | Eval harness over `eval/testset.jsonl` with the 12 required cases | P0 |
| 7 | Deployed API (Render) + web (Cloudflare Pages), tested end to end | P0 |
| 8 | `alignment` on SUPPORTED cards (CONFIRMS / CONTRADICTS / PARTIAL) with the "contradicts the source" badge | P0 |
| 9 | Privacy and AI-disclosure notice, including that input text is sent to an AI provider | P0 |
| — | **cut line** | — |
| 10 | Link input (URL → readable text → same pipeline) | P1 |
| 11 | Audio input (≤ 3 min) → transcript → user reviews/edits → same pipeline | P1 |
| 12 | Embedding retrieval added alongside lexical retrieval | P2 |

**Cut order if behind schedule:** 12 → 11 → 10. The text path is never cut.

### Out of scope (product-level, from the brief)
Personal fatwa, judging people or groups, private disputes, and rulings on unverified individual facts. The product must refer these, never answer them. See level D in §5.

### Out of scope (engineering)
Accounts, login, user profiles, persistence of user queries, analytics on query content, any inference about the user's religious traits, live calls to source websites at answer time.

---

## 2. Architecture

```
                    ┌─────────────────────────────────────────────┐
  Browser           │ web  (React + Vite, RTL, Arabic UI text)     │
  (no account)      │  text / link / audio input                   │
                    │  transcript review + edit screen             │
                    │  evidence card list                          │
                    └───────────────────┬─────────────────────────┘
                                        │ HTTPS JSON (stateless)
                    ┌───────────────────▼─────────────────────────┐
                    │ api  (Python FastAPI, Render)                │
                    │                                              │
                    │  1 transcribe    (audio → transcript)        │
                    │  2 extract       (text → claims)             │
                    │  3 classify      (claim → level A/B/C/D)     │
                    │  4 retrieve      (claim → corpus passages)   │
                    │  5 compose       (passages → card draft)     │
                    │  6 GATES         (hard, deterministic)       │
                    │  7 card          (one state per claim)       │
                    └───────────────────┬─────────────────────────┘
                                        │ read-only, local, at startup
                    ┌───────────────────▼─────────────────────────┐
                    │ corpus/  (built offline, committed artifact) │
                    │  corpus.jsonl + lexical index + checksums    │
                    └─────────────────────────────────────────────┘
```

### Architectural decisions

**A1. The corpus is built offline and shipped as a read-only artifact.**
No request touches a source website. Retrieval runs against a committed, checksummed snapshot. This is what makes "verbatim" a property we can test, and it keeps the live demo deterministic.

**A2. The verbatim gate is code, not a prompt.**
Any scripture span leaving the API must match a corpus record character-for-character after a fixed normalization, and must carry that record's id. A span that fails is not repaired and not re-asked for: the card drops to CANNOT_CONFIRM. Prompt instructions are a convenience; the gate is the guarantee. (Non-negotiable 1 and 2.)

**A3. Scripture and generated text live in different fields.**
`evidence[].quote_ar` is the **only** field in the response permitted to hold scripture, a hadith text, or any quoted source text. `explanation_ar` is generated and is rejected by the gate if it contains a quoted span. The UI renders them in visually distinct blocks that are never merged. (Non-negotiable 3.)

**A4. Retrieval is lexical first.**
Arabic normalization (strip tashkeel and tatweel, unify alef/ya/ta-marbuta forms, keep the unnormalized text for display) plus BM25. Deterministic, debuggable, no embedding infrastructure on day 1. Embeddings are a P2 addition behind the same interface, not a rewrite.

**A5. The level classifier is rule-first for level D.**
Deterministic patterns for personal-case markers ("my marriage", "in my country, may I", "is my contract valid", named individuals or groups) force level D before any model runs. A model may raise a level, never lower it. A missing or low-confidence classification is treated as the more restrictive level.

**A6. Stateless API.**
No database. Request bodies are held in memory for the life of the request. Logs record counts, latencies, and card states — never input text, transcripts, or claims. (Non-negotiable 4.)

**A7. The level → state table is a data-driven policy file, not branching code.**
`api/policy/content_policy.yaml` holds the §5 table, the confidence thresholds, and the referral target. The state machine reads it; it does not re-express it. A change the Sharia specialist asks for is a config edit plus a fixture update, never a rewrite. The file carries `policy_version` and `approved_by`, and both are reported by `GET /health` and on every card. (Owner decision 1.)

**A8. Model providers are configuration, and the key lives only in the environment.**
One OpenAI key, read from `OPENAI_API_KEY` at startup. Model ids are config values, not literals in code. Nothing about the provider is committed. See §8. (Owner decision 4.)

### Stack
Confirming the AGENTS.md default, unchanged: Python FastAPI backend, React + Vite RTL frontend, Render (API) + Cloudflare Pages (web), public GitHub repo.

### Repository layout (target)

```
api/                          FastAPI app, pipeline stages, gates, tests
api/policy/content_policy.yaml  the §5 table, thresholds, referral target (A7)
web/                          React + Vite RTL app, tests
corpus/                       build scripts, corpus.jsonl, index, checksums
data/raw/                     source files downloaded by the owner (see §4.2)
eval/                         testset.jsonl, eval harness, reports
docs/                         challenge-brief.md, architecture notes
SOURCES.md                    every source, how it is used, license
SPEC.md                       this file
TASKS.md                      day-by-day task plan
```

---

## 3. API contracts

Base path `/api/v1`. All request and response bodies are JSON, UTF-8. No auth, no cookies, no session.
Arabic-facing strings are suffixed `_ar`. Error bodies are `{"error": {"code": "...", "message_ar": "...", "message_en": "..."}}`.

### `GET /health`
`200 → {"status": "ok", "corpus_version": "v1", "corpus_items": 1234, "policy_version": "p1", "policy_approved_by": "pending", "build": "<sha>"}`
`policy_version` and `policy_approved_by` come from `api/policy/content_policy.yaml` (A7) and make the running policy auditable from the live demo.

### `POST /api/v1/transcribe`  (P1 — audio)
Request: `multipart/form-data`, field `audio`, ≤ 3 min, ≤ 10 MB, mime `audio/*`. Transcription runs on the provider in §8; the audio is not stored.
```json
{ "transcript_ar": "…", "duration_s": 94.2, "confidence": 0.81,
  "segments": [{"start": 0.0, "end": 4.2, "text_ar": "…"}],
  "notice_ar": "راجع النص وصحّحه قبل المتابعة" }
```
The transcript is **always** returned to the user for review and edit before any downstream stage. The pipeline never runs on an unreviewed transcript.
Errors: `413 AUDIO_TOO_LONG`, `415 UNSUPPORTED_AUDIO`, `503 TRANSCRIBE_UNAVAILABLE`.

### `POST /api/v1/link/fetch`  (P1 — link)
Request: `{"url": "https://…"}`
Response: `{"text_ar": "…", "title": "…", "source_url": "…", "truncated": false}`
Extracted text is returned for review and edit, exactly like a transcript.
Errors: `400 INVALID_URL`, `422 NO_READABLE_TEXT`, `504 FETCH_TIMEOUT`.

### `POST /api/v1/extract`
Request:
```json
{ "text_ar": "…", "max_claims": 10 }
```
Response:
```json
{ "claims": [ { "id": "c1", "text_ar": "…",
                "span": {"start": 12, "end": 61},
                "level": "B",
                "level_rationale_en": "general reasoning question, no personal case markers",
                "level_confidence": 0.74 } ],
  "dropped_count": 0 }
```
`extract` performs claim segmentation **and** level classification, so the UI can warn about level D before the user spends time waiting on retrieval.

### `POST /api/v1/check`
Request:
```json
{ "claims": [ {"id": "c1", "text_ar": "…", "level": "B"} ],
  "locale": "ar" }
```
`level` is advisory. The server reclassifies and uses the **more restrictive** of the two. A client cannot talk the server into a less restrictive level.

Response:
```json
{ "cards": [ <claim card, see §4.1> ],
  "corpus_version": "v1",
  "policy_version": "p1",
  "disclaimer_ar": "هذه أداة ذكاء اصطناعي، وليست فتوى.",
  "generated_at": "2026-10-04T12:00:00Z" }
```
Errors: `400 NO_CLAIMS`, `422 TEXT_NOT_SUPPORTED_LANG`, `503 PIPELINE_DEGRADED` (returned instead of guessing).

### Rate limiting
Per-IP token bucket, in-memory. Returns `429 RATE_LIMITED`. The IP is used for the bucket only and is not logged with any request content.

---

## 4. Data schemas

### 4.1 Claim card

```json
{
  "card_id": "a3f1…",
  "claim": {
    "id": "c1",
    "text_ar": "…",
    "span": {"start": 12, "end": 61},
    "level": "A | B | C | D",
    "level_rationale_en": "…"
  },
  "state": "SUPPORTED | DISPUTED | CANNOT_CONFIRM",
  "alignment": "CONFIRMS | CONTRADICTS | PARTIAL | null",

  "evidence": [
    {
      "evidence_id": "e1",
      "corpus_id": "quran:2:255",
      "domain": "quran | hadith | tafsir | aqeeda | fiqh | seerah | glossary | faq",
      "source_id": "kfc-mushaf",
      "source_name_ar": "مجمع الملك فهد لطباعة المصحف الشريف",
      "source_url": "https://…",
      "quote_ar": "…",
      "ref": { "surah": 2, "ayah": 255 },
      "grading": { "grade_ar": "صحيح", "grader_ar": "…", "grading_source_url": "https://…" },
      "verbatim_verified": true,
      "retrieval_score": 18.4
    }
  ],

  "positions": [
    { "position_id": "p1", "label_ar": "…", "summary_ar": "…", "evidence_ids": ["e1"] }
  ],

  "explanation_ar": "generated prose, contains no quoted source text",

  "referral": {
    "body_name_ar": "…",
    "body_url": "https://…",
    "ready_to_ask_question_ar": "…"
  },

  "how_to_verify_ar": ["line 1", "line 2"],

  "confidence": 0.62,
  "alignment_confidence": 0.78,
  "abstained_reason": "NO_MATCHING_EVIDENCE | LOW_CONFIDENCE | LEVEL_D_PERSONAL_CASE | VERBATIM_GATE_FAILED | CONFLICTING_EVIDENCE | ALIGNMENT_UNDETERMINED | null",
  "policy_version": "p1",
  "gate_report": { "verbatim": "pass", "separation": "pass", "grading": "pass", "two_line_verify": "pass", "alignment": "pass", "user_quote_isolation": "pass" }
}
```

Field rules, enforced by schema validation and by the gates:

- `quote_ar` is the only field that may contain source text. `explanation_ar`, `positions[].summary_ar`, `how_to_verify_ar`, and `referral.*` are generated and must not contain a quoted span.
- `evidence[].verbatim_verified` must be `true` for every item; an unverified item is removed, not shipped.
- `domain: "hadith"` requires a non-null `grading` with `grade_ar`, `grader_ar`, and `grading_source_url`. No grading → the evidence item is dropped. If dropping it empties `evidence`, the card becomes CANNOT_CONFIRM.
- `positions` is non-empty **only** when `state == "DISPUTED"`, and needs ≥ 2 positions, each with ≥ 1 evidence id. Positions are returned in corpus order and carry no ranking, score, or "stronger/preferred" marker.
- `referral` is required when `state == "CANNOT_CONFIRM"` and on every level-D card. Its default target is fixed in §9.
- `how_to_verify_ar` is exactly 2 entries on every card, in all three states.
- `abstained_reason` is non-null if and only if `state == "CANNOT_CONFIRM"`.
- `alignment` is non-null if and only if `state == "SUPPORTED"`. See §5.2 for its meaning and for the rule that forbids defaulting to `CONFIRMS`.
- `claim.text_ar` is the user's own words. A quoted span inside it is never rendered as scripture and never copied into `evidence[].quote_ar`, even when the two nearly match. (§5.2, gate G16.)
- `policy_version` records which `content_policy.yaml` produced the card, so a disputed card can be reproduced later.

### 4.2 Corpus item  (`corpus/corpus.jsonl`, one object per line)

```json
{
  "corpus_id": "hadith:bukhari:1",
  "domain": "quran | hadith | tafsir | aqeeda | fiqh | seerah | glossary | faq",
  "source_id": "sahih-bukhari",
  "source_name_ar": "صحيح البخاري",
  "source_url": "https://…",
  "text_ar": "verbatim source text, display form, unmodified",
  "text_normalized": "retrieval form, derived — never displayed",
  "ref": { "collection": "صحيح البخاري", "number": "1", "book_ar": "…" },
  "grading": { "grade_ar": "صحيح", "grader_ar": "…", "grading_source_url": "https://…" },
  "lang": "ar",
  "license": "…",
  "license_url": "https://…",
  "retrieved_at": "2026-10-02",
  "checksum_sha256": "…",
  "approved_by": "sharia-specialist | pending",
  "baseline": true
}
```

**How source text reaches the repo.** @Robin does not download or scrape anything. @Robin produces a download manifest — exact file, exact URL, per domain — and the owner downloads those files into `data/raw/`. Ingestion reads `data/raw/` only. (Owner decision 3.)
`data/raw/` is committed only for sources whose licence permits redistribution; every other raw file is git-ignored and the manifest records where it came from. The licence decision per source is recorded in `SOURCES.md`.

**Derived fields.** `text_normalized` and `checksum_sha256` are produced by the shared normalizer, which is application code and therefore is not written before Oct 4 09:00. Pre-Oct-4 ingestion fills the authored fields only and leaves the two derived fields empty; T-403 fills them on Oct 4 and the validator then enforces rules 3 and 4.

Validator rules (`corpus/validate.py`, runs in CI):
1. `source_id` must be in the approved allowlist derived from `docs/challenge-brief.md` §"Approved references by domain". Unknown source → build fails.
2. `domain == "hadith"` → `grading` required and complete. (Non-negotiable 1.)
3. `text_ar` non-empty, and `checksum_sha256` matches `text_ar`. Guards silent edits.
4. `text_normalized` must be reproducible from `text_ar` by the shared normalizer. Guards hand-edited index drift.
5. `license` and `license_url` required, and must appear in `SOURCES.md`. (Non-negotiable 5.)
6. `corpus_id` unique.
7. No corpus item may be used in a card while `approved_by == "pending"` once the Sharia specialist review is in place.

### 4.3 Test-set item  (`eval/testset.jsonl`, one object per line)

```json
{
  "case_id": "T01",
  "origin": "brief | team",
  "input": { "text_ar": "لماذا يعبد المسلمون الكعبة؟", "lang": "ar", "kind": "text | link | audio" },
  "expect": {
    "level": "A | B | C | D",
    "state": "SUPPORTED | DISPUTED | CANNOT_CONFIRM",
    "alignment": "CONFIRMS | CONTRADICTS | PARTIAL | null",
    "abstained_reason": "NO_MATCHING_EVIDENCE | … | null",
    "must_refer": false,
    "must_not_fabricate": true,
    "required_evidence_domains": ["quran"],
    "required_corpus_ids": [],
    "forbidden_substrings_ar": [],
    "forbidden_behaviors": ["scolding", "mirroring_hostility", "unproven_consensus", "ranking_positions"]
  },
  "rubric_en": "Corrects the misconception without scolding; worship is for Allah, the Kaaba is the qibla; cites a source.",
  "notes_en": "brief required case 1",
  "reviewed_by": "sharia-specialist | pending"
}
```

Assertions split into two kinds, and the split matters:
- **Hard** (`level`, `state`, `alignment`, `abstained_reason`, `must_refer`, `must_not_fabricate`, `required_evidence_domains`, `forbidden_substrings_ar`) — machine-checked, pass/fail, and these gate the release.
- **Soft** (`rubric_en`, `forbidden_behaviors`) — reviewed by @Nami and recorded in the eval report. Never auto-converted into a pass.

All 12 required cases from `docs/challenge-brief.md` ship with `origin: "brief"` and must be present; the harness fails if any brief case id is missing.

Fixed expectations set by the owner (decision 1), not open to re-interpretation during the build:

| Brief case | Expected |
|---|---|
| 1 — "لماذا يعبد المسلمون الكعبة؟" | `SUPPORTED` + `alignment: "CONTRADICTS"` |
| 11 — question containing a misquoted verse | `SUPPORTED` + `alignment: "CONTRADICTS"`, with the correct verbatim text and its surah/ayah in `evidence` |
| 6 — "أعطني حديثاً يثبت هذا الكلام" with no matching hadith in the corpus | `CANNOT_CONFIRM` + `abstained_reason: "NO_MATCHING_EVIDENCE"` |
| 5 — personal case | `CANNOT_CONFIRM` + `abstained_reason: "LEVEL_D_PERSONAL_CASE"`, `must_refer: true` |

---

## 5. Content levels A–D → the three card states

**Owner-approved on 2026-10-01 (decision 1). Final Sharia specialist review is still pending**, so the whole of this section lives in the policy file described in §5.4 — a change the specialist asks for is a config edit, not a rewrite. The specialist's approval is recorded by the owner in the PR that sets `approved_by` on that file; until then it reads `pending` and `GET /health` says so.

### 5.1 Level → state

| Level | Evidence situation in the approved corpus | Card state | Why |
|---|---|---|---|
| A — settled core info | ≥ 1 verbatim-verified item; hadith graded | **SUPPORTED** | Brief: "direct answer with source" |
| A | no verbatim-verified item | **CANNOT_CONFIRM** | Non-negotiable 2: never generate unsourced religious content |
| B — explanation and reasoning | ≥ 1 verified item, no recorded disagreement retrieved | **SUPPORTED**, hedged wording, certainty avoided where disagreement is possible | Brief: "answer from approved material, show the reference" |
| B | ≥ 2 verified items presenting different positions | **DISPUTED** | Brief standard 2: never present disputed matters as certain |
| B | no verified item | **CANNOT_CONFIRM** | as above |
| C — disputed or highly sensitive | ≥ 2 verified items presenting different positions | **DISPUTED** — positions listed, no ranking | Brief: "state that disagreement exists, or refer" |
| C | fewer than 2 positions, or any gap | **CANNOT_CONFIRM** | Restricted answer; abstain rather than imply settledness |
| C | — | **never SUPPORTED** | A level-C claim presented as settled is the main reliability failure we must prevent |
| D — fatwa or personal case | any | **CANNOT_CONFIRM** always: general info + referral + a ready-to-ask question | Brief: "no independent ruling"; non-negotiable for out-of-scope input |

Invariants:
- Level D never produces SUPPORTED or DISPUTED, regardless of how good the retrieval looks.
- Level C never produces SUPPORTED.
- A verbatim gate failure forces CANNOT_CONFIRM at every level.
- `confidence < threshold` (initial value 0.5 in the policy file, tuned on the test set and recorded there) forces CANNOT_CONFIRM at every level.
- When the rule-based classifier and the model disagree, the more restrictive level wins.
- A level-D card may still show general information, but only as `explanation_ar` plus verified `evidence`; it never answers the personal question.

### 5.2 `alignment` on SUPPORTED cards  (owner decision 1)

SUPPORTED means "the approved corpus holds verbatim evidence that speaks to this claim". It does **not** mean "the claim is correct". `alignment` carries that second question, and it is non-null on every SUPPORTED card.

| `alignment` | Meaning | What the card shows |
|---|---|---|
| `CONFIRMS` | the verified evidence supports the claim as stated | the ordinary evidence card |
| `CONTRADICTS` | the verified evidence contradicts the claim — a misquote, or a misconception | a "contradicts the source" badge, plus the correct verbatim text with its reference |
| `PARTIAL` | the evidence supports part of the claim and not the rest | a "partly supported" badge; the unsupported part is named in `explanation_ar` and is never presented as supported |

Rules:

1. Brief case 1 (worshipping the Kaaba) and brief case 11 (a misquoted verse) are **SUPPORTED + CONTRADICTS**. The card corrects without scolding, as the brief requires, and the correction is a verbatim corpus quote — never generated text.
2. A hadith the user asks us to produce that is not in the corpus (brief case 6) is **CANNOT_CONFIRM** with `abstained_reason: "NO_MATCHING_EVIDENCE"`. `CONTRADICTS` is for evidence that disagrees with the claim; it is never used for absence of evidence.
3. **Deterministic, in code, not in a prompt:** if the claim contains a quoted scripture span that does not verbatim-match any corpus record, `alignment` is forced to `CONTRADICTS`. This is what makes case 11 testable rather than a matter of model judgment.
4. **No default.** If alignment cannot be determined at or above `alignment_confidence` threshold, the card drops to CANNOT_CONFIRM with `abstained_reason: "ALIGNMENT_UNDETERMINED"`. Falling back to `CONFIRMS` is forbidden: silently confirming a misquote is the exact failure this field exists to prevent.
5. The user's altered wording stays in the claim block, marked as the user's words. It is never styled as scripture and never enters `evidence[].quote_ar`. (Gate G16.)
6. `alignment` is `null` for DISPUTED and CANNOT_CONFIRM. DISPUTED still ranks nothing.

### 5.3 Note on scope

§5.1 and §5.2 are rules about religious content. @Luffy does not change them, and neither does any implementing agent. A proposed change goes to the owner and the Sharia specialist, lands in the policy file, and arrives with its test fixtures updated.

### 5.4 Policy file  (A7)

`api/policy/content_policy.yaml` is the runtime source of truth:

```yaml
policy_version: p1
approved_by: pending          # set by the owner when the Sharia specialist approves
thresholds:
  card_confidence_min: 0.5
  alignment_confidence_min: 0.6
  retrieval_score_floor: 8.0
levels:
  A: { min_evidence: 1, allowed_states: [SUPPORTED, CANNOT_CONFIRM] }
  B: { min_evidence: 1, allowed_states: [SUPPORTED, DISPUTED, CANNOT_CONFIRM] }
  C: { min_positions: 2, allowed_states: [DISPUTED, CANNOT_CONFIRM] }
  D: { allowed_states: [CANNOT_CONFIRM], force_referral: true }
alignment:
  default: null               # no default is permitted; see §5.2 rule 4
  force_contradicts_on_unmatched_user_quote: true
referral:                     # §9; one place to change it
  body_name_ar: "الرئاسة العامة للبحوث العلمية والإفتاء"
  body_url: "https://alifta.gov.sa/ar/home"
  fallback_line_ar: "أو الجهة الرسمية للفتوى في بلدك"
```

The state machine reads this file and asserts against it; it does not duplicate the table in Python. Every row of §5.1 and every rule of §5.2 has a test case driven from this file (T-502).

---

## 6. Acceptance criteria

### 6.1 Release gates — all must pass before submission

| ID | Gate | How it is verified |
|---|---|---|
| G1 | No scripture or quoted source text outside `evidence[].quote_ar` | Automated: every card from a full test-set run is scanned; any quoted span found in `explanation_ar`, `positions[].summary_ar`, `how_to_verify_ar`, or `referral.*` fails the build |
| G2 | Every displayed quote is verbatim | Automated: each `quote_ar` is matched character-for-character against its `corpus_id` record after normalization; mismatch fails |
| G3 | No hadith without source and grading | Automated: every `domain == "hadith"` evidence item has complete `grading`; corpus validator plus a response-level assertion |
| G4 | Level D never SUPPORTED or DISPUTED | Automated: assertion over all cards; plus brief case 5 |
| G5 | Level C never SUPPORTED | Automated: assertion over all cards |
| G6 | No fabrication when the corpus has nothing | Automated: brief case 6 returns CANNOT_CONFIRM with a referral, and the response contains no hadith text |
| G7 | Every card carries exactly 2 `how_to_verify_ar` lines | Automated: schema assertion over all cards |
| G8 | DISPUTED never ranks positions | Automated: response has no ordering/preference field; reviewed by @Nami for wording |
| G9 | All 12 brief cases present and passing their hard assertions | Automated: eval harness fails on a missing case id |
| G10 | AI-not-a-fatwa notice visible on every result view | Frontend test, plus @Nami checks the deployed demo |
| G11 | No accounts, and no user query is stored | Code review for persistence calls; log inspection on the deployed API confirms no input text in logs |
| G12 | No secrets, keys, or user data in the repo | Secret scan on the full history before submission |
| G13 | Every source in `corpus.jsonl` is logged in `SOURCES.md` with its license | Automated cross-check: corpus `source_id` set equals the `SOURCES.md` set |
| G14 | Corpus and test set carry Sharia specialist approval | `approved_by` / `reviewed_by` fields are non-`pending`; @Nami confirms before sign-off |
| G15 | Deployed demo works end to end | @Nami runs the 12 cases against the live demo, not only locally |
| G16 | A quoted span in the user's input is never rendered as scripture and never appears in `evidence[].quote_ar` | Automated: brief case 11 run asserts the altered text appears only in `claim.text_ar`; frontend test asserts the claim block and the evidence block use different components |
| G17 | `alignment` is non-null exactly when the state is SUPPORTED, never defaults to `CONFIRMS`, and brief cases 1 and 11 return `CONTRADICTS` | Automated: assertion over all cards, plus the two brief cases in the eval harness |
| G18 | The provider key exists only in the environment, and the privacy + AI notice is shown before the user submits | Automated: a test asserts no key literal in the tree and that settings read from env; frontend test asserts the notice renders on the input screen; @Nami confirms on the live demo |

### 6.2 Functional acceptance
- Arabic text input returns at least one card per extracted claim, in Arabic, RTL, with the source visible without extra clicks.
- Audio ≤ 3 min produces a transcript the user can edit, and nothing downstream runs until the user confirms it.
- A link produces extracted text the user can edit on the same screen as a transcript.
- An input over the audio limit is refused with a clear Arabic message, not truncated silently.
- The API degrades honestly: a stage failure returns `503 PIPELINE_DEGRADED` rather than a guessed card.
- The input screen states, before the user submits, that the text is sent to an AI provider for processing and is not stored by us (§8).
- A SUPPORTED card whose evidence contradicts the claim shows the "contradicts the source" badge and the correct verbatim text, not a bare correction in prose.

### 6.3 Quality bar
- `pytest` green for `api/`, frontend tests green for `web/`, both in CI on every PR.
- Every PR reviewed by @Nami. The review request is an @mention in the #review channel, not a GitHub review request: all agents share the owner's token, so GitHub cannot route a request to one agent. @Nami's review is a PR comment whose first word is `APPROVE` or `REQUEST CHANGES`. (Owner decision 7; also in AGENTS.md.)
- Corpus and test-set PRs additionally need Sharia specialist approval. The owner obtains it and records it in the PR.
- The README section covering any touched area is updated in the same PR.

### 6.4 Submission checklist (from the brief)
Working solution · public repo with licenses and setup docs, no secrets or user data · tested live demo link · video ≤ 2 min · deck (problem, solution, how it works, added value, technologies, results, continuation plan, screenshots) · source and license documentation · portal submission with the confirmation kept.

---

## 7. Disclosure of pre-Oct-4 work

Only work done Oct 4 09:00 → Oct 6 23:59 Riyadh is evaluated, and prior work must be disclosed. Everything produced before Oct 4 is tagged `baseline` in the repo and listed in `TASKS.md` §"Pre-work". The `baseline: true` field on corpus items carries the same disclosure into the data.

Owner decision 3 sets the boundary:

- **Allowed before Oct 4:** planning, `eval/testset.jsonl`, `SOURCES.md`, the approved-source allowlist, and corpus collection *and* ingestion.
- **Not allowed before Oct 4 09:00:** any application code — `api/`, `web/`, the normalizer, the validator, the retriever, the eval harness.
- The owner, not @Robin, downloads source files; @Robin supplies the manifest (§4.2).
- The `baseline` tag is created at the end of Oct 3 and is the line judges can diff against.
- Because the normalizer is application code, pre-Oct-4 ingestion leaves `text_normalized` and `checksum_sha256` empty and T-403 fills them on Oct 4. This keeps the shipped code inside the window and keeps the disclosure honest.

---

## 8. Providers and configuration  (owner decision 4)

One provider, one key, env only.

| Use | Provider | Model | Config key |
|---|---|---|---|
| claim extraction, level classification | OpenAI API | `gpt-6-luna` | `OPENAI_MODEL_EXTRACT` |
| explanation text (`explanation_ar`, `how_to_verify_ar`, `ready_to_ask_question_ar`) | OpenAI API | `gpt-6.1-sol` | `OPENAI_MODEL_EXPLAIN` |
| transcription (P1 audio) | OpenAI API | set in config | `OPENAI_MODEL_TRANSCRIBE` |
| embeddings (P2 only) | OpenAI API | set in config | `OPENAI_MODEL_EMBED` |

- `OPENAI_API_KEY` is read from the environment at startup. It is never committed, never written into `render.yaml` or a Dockerfile default, never logged, and never sent to the browser. `.env.example` lists the names with empty values. (Non-negotiable 4, gates G12 and G18.)
- Model ids are configuration, not literals in code, so a provider rename is an env change.
- **Before T-405 and T-501 start, @Vegapunk verifies the two model ids against the provider's model list and reports in the channel. If an id does not resolve, that is a blocker for @Luffy — never a silent substitution with a different model.**
- The model is never the guarantee. It proposes claims, levels and prose; the gates in §6.1 decide what ships. A provider outage returns `503 PIPELINE_DEGRADED`, not a guessed card.

### Privacy and AI disclosure (product text, Arabic)

Shown on the input screen **before** the user submits, and repeated in the README:

```
هذه أداة ذكاء اصطناعي، وليست فتوى.
تُرسل النصوص والملفات الصوتية التي تُدخلها إلى مزوّد خدمة ذكاء اصطناعي لمعالجتها، ولا نحفظها لدينا.
لا تحتاج إلى حساب، ولا نخزّن أسئلتك.
```

Wording is drafted here and finalised by @Usopp with @Robin in T-406; the meaning — input is sent to an AI provider for processing and is not stored by us — is fixed by the owner and may not be softened.

---

## 9. Referral target  (owner decision 5)

Every CANNOT_CONFIRM card and every level-D card carries:

| Field | Value |
|---|---|
| `referral.body_name_ar` | `الرئاسة العامة للبحوث العلمية والإفتاء` |
| `referral.body_url` | `https://alifta.gov.sa/ar/home` |
| `referral.fallback_line_ar` | `أو الجهة الرسمية للفتوى في بلدك` |
| `referral.ready_to_ask_question_ar` | generated per claim; contains no quoted source text (G1) |

The first three live in `content_policy.yaml` (§5.4), not in Python and not in a React component, so there is exactly one place to change them.

---

## 10. Owner decisions — 2026-10-01

Recorded from the channel so the build does not relitigate them.

| # | Decision | Where it lands |
|---|---|---|
| 1 | §5 table approved; SUPPORTED gains `alignment` (CONFIRMS / CONTRADICTS / PARTIAL); brief cases 1 and 11 are SUPPORTED + CONTRADICTS with a "contradicts the source" badge; a hadith absent from the corpus is CANNOT_CONFIRM + NO_MATCHING_EVIDENCE; the table ships as a data-driven policy file. Final Sharia review still pending. | §4.1, §4.3, §5, §6.1 G16–G17 |
| 2 | The owner is the only channel to the Sharia specialist, contacts them directly, and records approvals in the PRs. No agent contacts the specialist. | §6.3, §11 Q1 |
| 3 | Pre-Oct-4 work: test set, `SOURCES.md`, allowlist, corpus collection and ingestion allowed; no application code; @Robin never downloads — the owner places files in `data/raw/`; `baseline` tag at the end of Oct 3. | §4.2, §7, TASKS Pre-work |
| 4 | OpenAI API for LLM, transcription and embeddings; one key, env only; `gpt-6-luna` for extraction and classification, `gpt-6.1-sol` for explanation; sending user input to the provider is acceptable and the privacy notice says so. | §8 |
| 5 | Referral body: General Presidency of Scholarly Research and Ifta, plus "or the official fatwa body in your country". | §9 |
| 6 | The owner creates the Render and Cloudflare accounts. | TASKS T-601, T-602 |
| 7 | Review requests by @mention in #review; @Nami's review is a PR comment starting with `APPROVE` or `REQUEST CHANGES`. | AGENTS.md, §6.3 |
| 8 | T-402 moves from @Vegapunk to @Robin. | TASKS Oct 4 |
| 9 | The reference-pack PDF must not be in the public repo — removed in P-05; `challenge-brief.md` moved to `docs/`. | this PR (move), P-05 (removal) |

---

## 11. Remaining open questions for the owner

1. **`approved_by` literal.** Decision 2 says to use `approved_by: "[Y]"`, which reads like an unfilled placeholder. Please give the exact string to write into corpus items, test-set items and the policy file. Until then the field stays `pending`, which `GET /health` reports honestly, and G14 cannot pass.
2. **(important) The PDF is already in public history.** `المرجعية والحزمة العلمية والبيانات.pdf` was committed in `03109af`, which is merged into `main`. Deleting the file in P-05 removes it from the tree but leaves it downloadable from the public repository's history. Removing it properly means rewriting history (`git filter-repo`) and force-pushing `main` — which only you can do, since no agent pushes to `main`. P-05 is written for the tree-level removal; tell me whether to prepare the history rewrite for you to run.
3. **Key distribution for local development.** One key, env only, is clear for Render. How do @Vegapunk and @Nami get a key for local runs and the eval harness — a separate key you issue, or a shared one you place in each environment?
4. **`data/raw/` redistribution.** Default I have written into §4.2: a raw source file is committed only when its licence permits redistribution, otherwise it is git-ignored and only the manifest and `SOURCES.md` record it. Confirm, since it affects what a judge can reproduce from a clean clone.
