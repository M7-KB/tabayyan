# Tabayyan (تبيّن)

Arabic-first web app that checks religious claims from text, a link, or short audio (≤ 3 min).
Each claim returns one evidence card in exactly one state: SUPPORTED, DISPUTED, or CANNOT_CONFIRM.
Tabayyan is an AI tool. It is not a fatwa.

## Planning

| Document | Contents |
|---|---|
| [SPEC.md](SPEC.md) | Scope, architecture, API contracts, data schemas, content level A–D → card state mapping with `alignment`, providers, referral target, acceptance criteria |
| [TASKS.md](TASKS.md) | Day-by-day task plan for Oct 4–6, plus disclosed pre-work |
| [AGENTS.md](AGENTS.md) | Team, non-negotiable rules, workflow |
| [docs/challenge-brief.md](docs/challenge-brief.md) | Challenge requirements: content levels, approved references, required test cases, evaluation weights |

Both planning documents were approved by the project owner on 2026-10-01; the owner's decisions are
listed in [SPEC.md §10](SPEC.md). The content-level policy in SPEC.md §5 is still pending final
Sharia specialist review, which is why it ships as a policy file (`api/policy/content_policy.yaml`)
rather than as code.

Run and setup instructions land with the application code (TASKS.md, T-604).
