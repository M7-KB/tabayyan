# SPEC.md — Tabayyan (تبيّن)

Status: draft for owner review
Owner of this document: @Luffy (lead)
Last updated: 2026-10-01
Source of truth for requirements: `challenge-brief.md` (see "Open questions" — AGENTS.md refers to it as `docs/challenge-brief.md`)

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
| — | **cut line** | — |
| 8 | Link input (URL → readable text → same pipeline) | P1 |
| 9 | Audio input (≤ 3 min) → transcript → user reviews/edits → same pipeline | P1 |
| 10 | Embedding retrieval added alongside lexical retrieval | P2 |

**Cut order if behind schedule:** 10 → 9 → 8. The text path is never cut.

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

### Stack
Confirming the AGENTS.md default, unchanged: Python FastAPI backend, React + Vite RTL frontend, Render (API) + Cloudflare Pages (web), public GitHub repo.

### Repository layout (target)

```
api/            FastAPI app, pipeline stages, gates, tests
web/            React + Vite RTL app, tests
corpus/         build scripts, corpus.jsonl, index, checksums
eval/           testset.jsonl, eval harness, reports
docs/           challenge-brief.md, architecture notes
SOURCES.md      every source, how it is used, license
SPEC.md         this file
TASKS.md        day-by-day task plan
```

---

## 3. API contracts

Base path `/api/v1`. All request and response bodies are JSON, UTF-8. No auth, no cookies, no session.
Arabic-facing strings are suffixed `_ar`. Error bodies are `{"error": {"code": "...", "message_ar": "...", "message_en": "..."}}`.

### `GET /health`
`200 → {"status": "ok", "corpus_version": "v1", "corpus_items": 1234, "build": "<sha>"}`

### `POST /api/v1/transcribe`  (P1 — audio)
Request: `multipart/form-data`, field `audio`, ≤ 3 min, ≤ 10 MB, mime `audio/*`.
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
  "abstained_reason": "NO_MATCHING_EVIDENCE | LOW_CONFIDENCE | LEVEL_D_PERSONAL_CASE | VERBATIM_GATE_FAILED | CONFLICTING_EVIDENCE | null",
  "gate_report": { "verbatim": "pass", "separation": "pass", "grading": "pass", "two_line_verify": "pass" }
}
```

Field rules, enforced by schema validation and by the gates:

- `quote_ar` is the only field that may contain source text. `explanation_ar`, `positions[].summary_ar`, `how_to_verify_ar`, and `referral.*` are generated and must not contain a quoted span.
- `evidence[].verbatim_verified` must be `true` for every item; an unverified item is removed, not shipped.
- `domain: "hadith"` requires a non-null `grading` with `grade_ar`, `grader_ar`, and `grading_source_url`. No grading → the evidence item is dropped. If dropping it empties `evidence`, the card becomes CANNOT_CONFIRM.
- `positions` is non-empty **only** when `state == "DISPUTED"`, and needs ≥ 2 positions, each with ≥ 1 evidence id. Positions are returned in corpus order and carry no ranking, score, or "stronger/preferred" marker.
- `referral` is required when `state == "CANNOT_CONFIRM"`.
- `how_to_verify_ar` is exactly 2 entries on every card, in all three states.
- `abstained_reason` is non-null if and only if `state == "CANNOT_CONFIRM"`.

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

Validator rules (`corpus/validate.py`, runs in CI):
1. `source_id` must be in the approved allowlist derived from `challenge-brief.md` §"Approved references by domain". Unknown source → build fails.
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
- **Hard** (`level`, `state`, `must_refer`, `must_not_fabricate`, `required_evidence_domains`, `forbidden_substrings_ar`) — machine-checked, pass/fail, and these gate the release.
- **Soft** (`rubric_en`, `forbidden_behaviors`) — reviewed by @Nami and recorded in the eval report. Never auto-converted into a pass.

All 12 required cases from `challenge-brief.md` ship with `origin: "brief"` and must be present; the harness fails if any brief case id is missing.

---

## 5. Content levels A–D → the three card states

**This table is a rule about religious content. It is a proposal only, and needs sign-off from the human owner and the Sharia specialist before any of it is implemented.** (Per my role: escalate, do not decide.)

| Level | Evidence situation in the approved corpus | Proposed card state | Why |
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

Additional proposed invariants:
- Level D never produces SUPPORTED or DISPUTED, regardless of how good the retrieval looks.
- Level C never produces SUPPORTED.
- A verbatim gate failure forces CANNOT_CONFIRM at every level.
- `confidence < threshold` (initial proposal 0.5, to be tuned on the test set and recorded here) forces CANNOT_CONFIRM at every level.
- When the rule-based classifier and the model disagree, the more restrictive level wins.
- A level-D card may still show general information, but only as `explanation_ar` plus verified `evidence`; it never answers the personal question.

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

### 6.2 Functional acceptance
- Arabic text input returns at least one card per extracted claim, in Arabic, RTL, with the source visible without extra clicks.
- Audio ≤ 3 min produces a transcript the user can edit, and nothing downstream runs until the user confirms it.
- A link produces extracted text the user can edit on the same screen as a transcript.
- An input over the audio limit is refused with a clear Arabic message, not truncated silently.
- The API degrades honestly: a stage failure returns `503 PIPELINE_DEGRADED` rather than a guessed card.

### 6.3 Quality bar
- `pytest` green for `api/`, frontend tests green for `web/`, both in CI on every PR.
- Every PR reviewed by @Nami. Corpus and test-set PRs additionally need Sharia specialist approval.
- The README section covering any touched area is updated in the same PR.

### 6.4 Submission checklist (from the brief)
Working solution · public repo with licenses and setup docs, no secrets or user data · tested live demo link · video ≤ 2 min · deck (problem, solution, how it works, added value, technologies, results, continuation plan, screenshots) · source and license documentation · portal submission with the confirmation kept.

---

## 7. Disclosure of pre-Oct-4 work

Only work done Oct 4 09:00 → Oct 6 23:59 Riyadh is evaluated, and prior work must be disclosed. Everything produced before Oct 4 is tagged `baseline` in the repo and listed in `TASKS.md` §"Pre-work". The `baseline: true` field on corpus items carries the same disclosure into the data. See the open question in §8 about how far pre-work may go.

---

## 8. Open questions for the owner

Blocking items are marked. These are in the channel message as well.

1. **(blocking, religious content)** Sign-off on the level → state table in §5, especially "level C never SUPPORTED" and "level D always CANNOT_CONFIRM". Needs the owner and the Sharia specialist. Nothing in §5 is implemented until then.
2. **(blocking)** Who is the Sharia specialist, and how do we reach them? Corpus and test-set approval is a hard dependency on Oct 4–5, and G14 cannot pass without it.
3. **(blocking)** How far may pre-Oct-4 work go? Confirmed allowed so far: test set and source list. Is offline corpus collection and ingestion also acceptable as disclosed `baseline` work, or must it wait for Oct 4?
4. **(blocking)** Which LLM provider and model for claim extraction, level classification, and explanation text, and which transcription service? Whose account and key? Given non-negotiable 4, confirm that sending user input to a third-party model is acceptable and what we state in the privacy notice.
5. Render and Cloudflare Pages accounts — do they exist, and who owns them? Needed before Oct 6 deploy tasks.
6. `challenge-brief.md` is at the repo root, but `AGENTS.md` points to `docs/challenge-brief.md`. Proposal: move it to `docs/`. Not done in this PR, which is plan-only.
7. The reference-pack PDF (`المرجعية والحزمة العلمية والبيانات.pdf`) cannot be opened in my environment. If it contains source, license, or glossary detail beyond `challenge-brief.md`, please share a text or Markdown copy — @Robin needs it for `SOURCES.md` and the corpus allowlist.
8. Referral target for CANNOT_CONFIRM and level D: which official fatwa body, and which URL, should the cards point to?
