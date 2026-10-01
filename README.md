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

## Planning

| Document | Contents |
|---|---|
| [SPEC.md](SPEC.md) | Scope, architecture, API contracts, data schemas, input kinds and the question → claim design for all 12 required brief cases, the A–D → card-state mapping with the `alignment` ratchet, the scripture-span detector, the policy/tuning split, untrusted-input rules, providers, referral target, clip privacy, acceptance criteria |
| [TASKS.md](TASKS.md) | Day-by-day task plan for Oct 4–6, plus disclosed pre-work |
| [AGENTS.md](AGENTS.md) | Team, non-negotiable rules, workflow, file-access boundary |
| [CODEOWNERS](CODEOWNERS) | `api/policy/` is owned by the project owner (gate G24) |
| [docs/challenge-brief.md](docs/challenge-brief.md) | Challenge requirements: content levels, approved references, required test cases, evaluation weights |

## Status

The plan is owner-approved in substance and is **pending independent review** on PR #5. The owner merges
only after the reviewer posts `APPROVE`.

The content-level policy in [SPEC.md §5](SPEC.md) is still pending final Sharia specialist review, which
is why it ships as two config files — `api/policy/content_policy.yaml` (specialist-owned, pinned by a
test, CODEOWNERS) and `api/tuning.yaml` (engineering-owned thresholds) — rather than as branching code. A
change the specialist asks for is a config edit plus a pinned-literal update, not a rewrite.
`GET /health` reports `policy_approved_by`, so the running policy is auditable from the live demo. While
it reads `pending`, release gate G14 is **not met**, and that is reported rather than softened.

Items still awaiting the owner's or the specialist's decision are listed in [SPEC.md §12](SPEC.md), each
with a working default chosen in the restrictive direction.

## Disclosure of pre-Oct-4 work

Only work done Oct 4 09:00 → Oct 6 23:59 Riyadh is evaluated by the challenge, and prior work must be
disclosed. Everything produced before Oct 4 is tagged `baseline` and listed in
[TASKS.md](TASKS.md) §"Pre-work": the test set, `SOURCES.md`, the approved-source allowlist, corpus
collection and ingestion, the card JSON Schema, and the two policy/tuning config files. No application
code was written before Oct 4 09:00.

The word `baseline` in this repository means **only** that pre-Oct-4 disclosure. The corpus-free
comparison arm in the eval reports is called `control`.

The reference-pack PDF was **removed from the tree but remains reachable in this repository's public
history at commit `03109af`**, and the `baseline` tag freezes a repository in that state. There is no
history rewrite.

## Privacy

No accounts. No stored queries. Text, audio and images you submit are sent to an AI provider for
processing and are not stored by us; audio and images are deleted immediately after processing. Cards
judge statements, never people: no speaker is named or identified, and there is no voice fingerprinting.
Uploading a clip requires an explicit consent tick. Opening a platform embed on a result screen contacts
that platform, and the UI says so before it loads.

Run and setup instructions land with the application code (TASKS.md, T-604).
