# Tools register

Owner and editor: Robin. Contributors report AI-tool use in the planning channel,
with date, task/PR, tool/provider, exact model identifier if available, use, evidence
and terms/licence status. Only Robin edits this register, in a dedicated PR rebased
on main. Contributors do not edit the shared table on parallel task branches.
Robin preserves every report during reconciliation; never resolve a conflict by
dropping a row. Correct a reported entry with a cited correction rather than erasing it.
This implements the tool log required by [docs/challenge-brief.md](docs/challenge-brief.md).

Record date, task, tool, provider, verified model identifier, use, evidence and licence/terms status.
Use `pending verification` when evidence is unavailable, and track its owner and
closing date below. A planned product model is not evidence of use.
Never put credentials, private prompts, user queries or personal data in this register.

| Date | Task | AI tool / provider | Verified model identifier | Use | Evidence | Licence / terms status |
|---|---|---|---|---|---|---|
| 2026-10-02 | P-04 source documentation | Codex / OpenAI | Pending verification; no provider API identifier recorded in the contribution | Metadata research and documentation; no religious source downloads or ingestion | PR [#6](https://github.com/M7-KB/tabayyan/pull/6), source documentation and tests | Tool service terms pending verification; source permissions belong in SOURCES.md |
| 2026-10-02 | P-03 register split and tools register | Codex / OpenAI | Pending verification; runtime display labels are not provider API identifiers | Documentation edits and repository checks | Branches `docs/sources-v0` and `docs/tools-register` | Tool service terms pending verification |

Supporting tools used for these contributions: Buzz CLI, Git, GitHub CLI, PowerShell and Node.js
(source-register checks). Versions and licence evidence are not yet recorded; Robin collects contributor evidence for them
when preparing the submission inventory. These are development tools, not declared product dependencies.

## Reconciliation before submission

Robin owns this register and its completion checklist under the TOOLS.md assignment
in [PR #14](https://github.com/M7-KB/tabayyan/pull/14). The TASKS id and acceptance
criteria are pending Luffy's update in #14; this PR does not assign a new task id.
Contributor reports are due **2026-10-05 18:00 Riyadh (UTC+03:00)**. Robin reconciles
all reports by **20:00**, before the **22:00 first submission** (TASKS T-608a).
Any unresolved entry at 20:00 is escalated to Luffy and the owner in planning;
submission completeness remains unmet until evidence or an explicit unresolved
status is recorded. Recheck updates before the Oct 6 21:00 final submission.

| Outstanding item | Collection owner | Evidence needed | Due (Riyadh) |
|---|---|---|---|
| Exact model identifiers and service terms for Robin's rows | Robin | Runtime/provider evidence; a display label alone is not an API id | Oct 5 18:00 |
| Earlier and parallel contributors' AI-tool use | Robin | Reports from Luffy, Vegapunk, Usopp and Nami covering each contribution | Oct 5 18:00 |
| Claude-based tooling indication | Robin | Contributor confirmation of actual tool/model use or correction | Oct 5 18:00 |
| Development tool versions/licence evidence | Robin | Version output and licence/terms references for tools listed above | Oct 5 18:00 |
| Actual product model use | Robin | Vegapunk's verified model ids and use evidence, separate from planned models | Oct 5 18:00 |
| Consolidated completeness check and escalation | Robin | Every report retained; each unknown resolved or explicitly escalated | Oct 5 20:00 |

Claude tooling is a pending inventory item, not a verified contributor row.
Main `52a3983` includes `CLAUDE.md` containing `@AGENTS.md`; that configuration
alone does not establish actual use. [PR #14's body](https://github.com/M7-KB/tabayyan/pull/14)
also contains a Claude Code attribution. Robin will collect the responsible
contributor's confirmation and exact model evidence rather than invent that row.

Product model identifiers in [SPEC.md section 8](SPEC.md) remain planned and pending
verification. Record actual use and evidence before claiming them in the submission.
