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
lossy: equal keys do not authorize religious evidence or settle alignment. No quote checker, alignment,
span detector or corpus download is implemented here. Loader and validator usage is below.
Tests use synthetic non-scriptural text and include idempotence across
every Unicode scalar in blocks.

The normalizer and its tests were developed on October 2, 2026, with organizer permission to start
development that day (see Disclosure below). TASKS.md records the implementation and the pending
T-503a quote-safety follow-up: equal normalized keys must never authorize a quotation.

## Planning

| Document | Contents |
|---|---|
| [SPEC.md](SPEC.md) | Scope, architecture, API contracts, data schemas, input kinds and the question → claim design for all 12 required brief cases, the A–D → card-state mapping with the `alignment` ratchet, the scripture-span detector, the policy/tuning split, untrusted-input rules, providers, referral target, clip privacy, acceptance criteria |
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

Set `OPENAI_API_KEY` in the process environment; no `.env` file is loaded automatically.
`.env.example` lists empty key/model settings. Model IDs are environment configuration, with no
model calls in this scaffold. Set `CORS_ORIGINS` to a JSON array of exact frontend origins; the default
allows none. Set `BUILD_SHA` to the deployed commit SHA. Disable server access logs as shown above
because paths and query strings can contain user text. No request body or exception details are logged
by application code or included in error responses.

**Integration prerequisite:** install reviewed P-08 files at `api/policy/content_policy.yaml` and
`api/tuning.yaml` (or set `CONTENT_POLICY_PATH` and `TUNING_PATH`). They belong to a separate task and
are deliberately not recreated here. Startup fails on a missing API key, missing/invalid config, or
any word-budget tier exceeding the policy ceiling, zero budgets, or decreasing budgets across
length bands. The schema validates confidence floors and the Trigger B minimum window. Startup errors
identify the config path and field without echoing values. This reads metadata and limits only; it does
not implement alignment or span detection. `span_detector_status` and `misquote_notice` are runtime
claim/card fields per SPEC.md, not tuning keys; they arrive with the detector/card contract tasks.

`GET /health` exposes the policy approval and tuning versions read from those files. Until the corpus
loader and card schema are integrated, it reports `status: degraded`, `corpus_items: 0` and null
artifact versions. It is a scaffold liveness response, not a release-readiness claim. Verification,
transcription and ingestion routes are not implemented by this PR. Errors use the SPEC envelope
`error: {code, message_ar, message_en}` with fixed text that does not echo input.

## Source register (P-03)

See [SOURCES.md](SOURCES.md) for candidate sources, uses and licence evidence. All 13 entries
remain pending: this register grants no ingestion or redistribution permission. P-04 supplies
the separate acquisition manifest and allowlist. The public raw-package history and
pending cleanup in PR #13 are disclosed in SOURCES.md.

Run the standalone register contract checks with `node --test tests/*.test.mjs`.
CI checks headers, unique IDs, required license fields and the closed domain enum.

## Manual source collection (P-04)

Follow [docs/DOWNLOAD_MANIFEST.md](docs/DOWNLOAD_MANIFEST.md) for the owner download checklist,
formats and local paths. [SOURCES.md](SOURCES.md) records licence evidence; all current permissions
are pending, so ingestion remains blocked until permission is clear.
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
`SOURCES.md`. For a cleared source, its allowlist row must have `license_status: confirmed`,
`ingestion_allowed: true` and `redistribution_allowed: true`; its exact licence and licence URL must
match the register. Existing candidate rows remain pending and cannot pass. Only an owner-cleared
source PR changes these flags and records permission for derived corpus/application display. This
validator trusts that reviewed metadata; it cannot prove the permission document or textual provenance.

Offline review of a licence-cleared artifact may use `python -m corpus.validate --allow-pending-review`
to admit `approved_by: pending`. This option never waives licence checks and is unavailable on
`load_corpus`: runtime records always require `sharia-reviewer-1`. The owner records actual specialist
approval in the content PR; a string in a fixture is not sign-off. Use `--corpus`, `--sources` and
`--register` for explicit offline paths. The loader's analogous keyword paths support tests/integration.

CI validates an artifact when present and reports its absence explicitly otherwise. No corpus records
ship with this task. P-06 raw ingestion and T-403 filling remain blocked on owner files, permissions
and specialist review; format-specific raw importers belong to P-06. Tests use only synthetic prose
and synthetic metadata and cover the eight rejection rules, original-text preservation and runtime
rejection of pending approval.
