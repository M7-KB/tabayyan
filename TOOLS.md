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
| 2026-10-02 | Planning edits and PR/review coordination: PR #5, #13, #14 | Claude Code / Anthropic (Luffy contributor report) | Pending verification; contributor report is not independent provider/runtime evidence | SPEC.md, TASKS.md, README.md and .gitignore; no application code or corpus/scripture content authored, per report | Contributor claims `claude-sonnet-5` (Claude Sonnet 5), not independently verified. Planning message `6c1e5f7bde9dfefcf8fb6e2e01bfaf06f839aff6ba5e4d66e2a33a3f88616c47`, Luffy, 2026-10-02 14:09:26 UTC; PR [#5](https://github.com/M7-KB/tabayyan/pull/5), [#13](https://github.com/M7-KB/tabayyan/pull/13), [#14](https://github.com/M7-KB/tabayyan/pull/14) | Service terms pending verification; Robin collects evidence by Oct 5 18:00 Riyadh |

Supporting tools used for Robin's contributions: Buzz CLI, Git, GitHub CLI, PowerShell and Node.js
(source-register checks). Versions and licence evidence are not yet recorded; Robin collects contributor evidence for them
when preparing the submission inventory. These are development tools, not declared product dependencies.

Luffy reports Git, GitHub CLI (gh), Buzz CLI and standard file read/edit/grep for the planning contributions above. Versions and licence evidence remain pending; no specific file utility or version was reported.

## Reconciliation before submission

Robin owns this register and its completion checklist under the TOOLS.md assignment
in merged [PR #14](https://github.com/M7-KB/tabayyan/pull/14) at `a72a122`.
[TASKS.md P-10](TASKS.md) records the task id and acceptance criteria.
Contributor reports are due **2026-10-05 18:00 Riyadh (UTC+03:00)**. Robin reconciles
all reports by **20:00**, before the **22:00 first submission** (TASKS T-608a).
Any unresolved entry at 20:00 is escalated to Luffy and the owner in planning;
submission completeness remains unmet until evidence or an explicit unresolved
status is recorded. Recheck updates before the Oct 6 21:00 final submission.

| Outstanding item | Collection owner | Evidence needed | Due (Riyadh) |
|---|---|---|---|
| Exact model identifiers and service terms for Robin's rows | Robin | Runtime/provider evidence; a display label alone is not an API id | Oct 5 18:00 |
| Earlier and parallel contributors' AI-tool use | Robin | Reports from Luffy, Vegapunk, Usopp and Nami covering each contribution | Oct 5 18:00 |
| Luffy's Claude Code service terms and supporting-tool evidence | Robin | Actual use and model id reported in the row above; collect terms, versions and licence references | Oct 5 18:00 |
| Development tool versions/licence evidence | Robin | Version output and licence/terms references for tools listed above | Oct 5 18:00 |
| Actual product model use | Robin | Vegapunk's verified model ids and use evidence, separate from planned models | Oct 5 18:00 |
| Consolidated completeness check and escalation | Robin | Every report retained; each unknown resolved or explicitly escalated | Oct 5 20:00 |

Luffy confirmed actual Claude Code use and reported the model identifier in the cited planning message. This resolves the earlier configuration-only indication from CLAUDE.md and PR #14's attribution. The row preserves contributor-reported evidence; service terms and independent runtime/provider confirmation are not established by that message. Luffy will report changes before Oct 5 18:00 Riyadh.

Product model identifiers in [SPEC.md section 8](SPEC.md) remain planned and pending
verification. Record actual use and evidence before claiming them in the submission.
