# Tools register

Owner: Robin. Contributors append a row in the PR where they use an AI tool or change a product model.
This implements the tool log required by [docs/challenge-brief.md](docs/challenge-brief.md).

Record date, task, tool, provider, verified model identifier, use, evidence and licence/terms status.
Use `not recorded` when evidence is unavailable. A planned product model is not evidence of use.
Never put credentials, private prompts, user queries or personal data in this register.

| Date | Task | AI tool / provider | Verified model identifier | Use | Evidence | Licence / terms status |
|---|---|---|---|---|---|---|
| 2026-10-02 | P-04 source documentation | Codex / OpenAI | Not recorded; no provider API identifier recorded in the contribution | Metadata research and documentation; no religious source downloads or ingestion | PR [#6](https://github.com/M7-KB/tabayyan/pull/6), source documentation and tests | Tool service terms not recorded; source permissions belong in SOURCES.md |
| 2026-10-02 | P-03 register split and tools register | Codex / OpenAI | Not recorded; runtime display labels are not provider API identifiers | Documentation edits and repository checks | Branches `docs/sources-v0` and `docs/tools-register` | Tool service terms not recorded |

Supporting tools used for these contributions: Buzz CLI, Git, GitHub CLI, PowerShell and Node.js
(source-register checks). Versions and licence evidence are not yet recorded; contributors add them
when preparing the submission inventory. These are development tools, not declared product dependencies.

Team-wide completeness remains pending. Earlier contributors must supply their own verifiable rows.
Product model identifiers in [SPEC.md section 8](SPEC.md) remain planned and pending verification;
append actual use, verified identifier and evidence before claiming them in the submission.
