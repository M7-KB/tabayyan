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
span detector, corpus download, loader, or eight-rule validator is implemented here. The loader and
validator remain Robin's work. Tests use synthetic non-scriptural text and include idempotence across
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

## First Render API deployment (T-420)

The [Render Blueprint](render.yaml) runs the scaffold in explicit `HEALTH_ONLY=true` mode.
This mode requires the dashboard key but makes no model calls and does not load policy, tuning,
corpus or synthetic fixtures. Only `GET /health` is registered; verification, ingestion,
transcription and documentation routes are unavailable. Normal scaffold startup remains strict:
with `HEALTH_ONLY` unset or false, missing/invalid policy and tuning still fail startup.

The owner creates the Render account and enters the production key directly in its dashboard.
Never send it in chat or put it in a file. In Render, create a Blueprint from this public repository,
select branch `ops/deploy-api-v0`, and use `render.yaml`. Its free plan and disabled auto-deploy
are explicit. Do not provision a second service if `tabayyan-api-v0` already exists; configure the
existing service with the same build/start commands and branch instead.

Enter these values in the Render dashboard only (the Blueprint contains names, no values):

| Variable | Dashboard value |
|---|---|
| `OPENAI_API_KEY` | Owner's production key; required at startup, unused by health-only mode |
| `HEALTH_ONLY` | `true` |
| `CORS_ORIGINS` | `[]` until the web origin exists, then a JSON array of exact HTTPS web origins |
| `BUILD_SHA` | Exact reviewed commit being deployed, from `git rev-parse HEAD` |
| `PYTHON_VERSION` | `3.11.9` (the version used for local validation) |

Build command: `python -m pip install .`. Start command:
`uvicorn api.main:app --host 0.0.0.0 --port $PORT --no-access-log`.
Health check path: `/health`. Leave root directory at repository root, use no persistent disk,
and trigger deployment manually after Nami's exact-head review. Match the Render deployment's
commit with `BUILD_SHA`; that field is configured metadata, not independent proof of the deployed code.

After Render shows the service live, record its actual public URL and smoke-test:

```sh
curl --fail --silent --show-error https://YOUR-SERVICE.onrender.com/health
curl --silent --show-error -X POST https://YOUR-SERVICE.onrender.com/verify
```

The first request must return HTTP 200 with `status: degraded`, `corpus_items: 0`,
`policy_approved_by: pending`, null `corpus_version`, `policy_version`, `tuning_version` and
`card_schema_version`, and the reviewed `build` SHA. The second must return HTTP 404 in the fixed
error envelope; never send real user input during this smoke test. Once a frontend origin is set,
check `/health` with its `Origin` header and confirm only that origin receives the CORS allow header.
The owner inspects Render logs for G11 and posts the evidence. A local smoke pass or this runbook
does not prove a public deployment, G11, or G18 dashboard setup; record those separately.

Render setup references: [FastAPI deployment](https://render.com/docs/deploy-fastapi) and
[Blueprint fields](https://render.com/docs/blueprint-spec).

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
