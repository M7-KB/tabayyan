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

| 2026-10-04 | T-404 lexical retrieval | Codex / OpenAI | Pending verification; session identifies GPT-6 without a verified provider API identifier | BM25 implementation, synthetic engineering tests and README documentation; no religious content generated | Branch `feat/retrieval`; `api/retrieval.py`, `tests/test_retrieval.py` | Tool service terms pending verification |

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

Product model identifiers in [SPEC.md section 8](SPEC.md) are configuration choices.
The T-501 entry below verifies their official documentation and proposed adapter
configuration, but does not establish account access or actual product inference.
Record actual use and evidence before claiming them in the submission.

## T-501 product adapter contribution (2026-10-04)

Vegapunk reported this contribution in build message
`849b87b83312f68c8e8fc10c3f3b0bc92ae49ab41f30287e63231f64e03f1915`.
Evidence is scoped to open [PR #49](https://github.com/M7-KB/tabayyan/pull/49)
at `d832ef65a452f1dea51fb8b1117ef91b439a02a6`; it is not a merged or deployed inventory.
All earlier contributor rows remain above.

| Date | Task | AI tool / provider | Documented and configured model identifier | Use status | Evidence | Licence / terms status |
|---|---|---|---|---|---|---|
| 2026-10-04 | T-501, PR #49 | Responses API / OpenAI | `gpt-6-luna` for extraction; `gpt-6.1-sol` for level classification | Adapter implementation and mocked HTTP validation only; contributor reports no live inference | [Official Luna page](https://developers.openai.com/api/docs/models/gpt-6-luna), [official Sol page](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [adapter](https://github.com/M7-KB/tabayyan/blob/d832ef65a452f1dea51fb8b1117ef91b439a02a6/api/provider.py), [documented environment configuration](https://github.com/M7-KB/tabayyan/blob/d832ef65a452f1dea51fb8b1117ef91b439a02a6/README.md), cited contributor message | Hosted API service; applicable account/service terms pending verification. Model documentation does not establish account entitlement or religious accuracy |

The adapter posts directly through HTTPX; this contribution does not declare an
OpenAI Python SDK dependency. Provider behavior/privacy references are in
[PR #49's README](https://github.com/M7-KB/tabayyan/blob/d832ef65a452f1dea51fb8b1117ef91b439a02a6/README.md).
The contributor's local research record is
`RESEARCH/TABAYYAN_T501_PROVIDER_DOCS_20261004.md` (workspace path, not a shipped repo file).
Mock transport validation is not live model testing. No zero-retention claim is made.

### Runtime dependency contribution

These ranges are declared in
[PR #49's pyproject.toml](https://github.com/M7-KB/tabayyan/blob/d832ef65a452f1dea51fb8b1117ef91b439a02a6/pyproject.toml).
Both also remain listed in the development extras. They are dependency constraints,
not pinned installed or deployed versions. Upstream licence files were checked on
2026-10-04; confirm licences and notices for the resolved release at submission.

| Package | Declared runtime range | Role | Upstream licence evidence | Installed/deployed version |
|---|---|---|---|---|
| `httpx` | `>=0.27,<1` | HTTP transport to Responses API | BSD-3-Clause; [upstream LICENSE.md](https://github.com/encode/httpx/blob/master/LICENSE.md) | Pending verification |
| `jsonschema` | `>=4.23,<5` | Local structured-output schema validation | MIT; [upstream COPYING](https://github.com/python-jsonschema/jsonschema/blob/main/COPYING) | Pending verification |

Robin collects account/service terms and resolved runtime versions/licence notices
by **2026-10-05 18:00 Riyadh**, with evidence from Vegapunk or the deployment owner.
Live access, actual model use and accuracy remain pending until separately reported;
the existing 20:00 reconciliation/escalation deadline applies.

## Bounded connector spike and Quran handoff (2026-10-05)

Authority: owner event 62e18dbe42e11a40f175e75c987826e5b4b202b3b65e2ec679ccdb3756742209,
Luffy routing e660ae834c34b4c7632f3e857e5aafb932e03922d007b3f5319985dc3934bbb2.
See [the measured spike](docs/CONNECTOR_SPIKE_20261005.md), display [PR #61](https://github.com/M7-KB/tabayyan/pull/61)
and artifact metadata [PR #62](https://github.com/M7-KB/tabayyan/pull/62).

| Date | Task | AI tool / provider | Verified model identifier | Use | Evidence | Licence / terms status |
|---|---|---|---|---|---|---|
| 2026-10-05 | Bounded source spike | OpenAI Responses API | gpt-6.1-sol (both response model fields) | Two requests: remote MCP language metadata and domain-filtered web search for API docs; store:false; no real user input | [Measured table](docs/CONNECTOR_SPIKE_20261005.md); 9,933 total provider tokens, dollar cost not measured | Official [remote MCP](https://developers.openai.com/api/docs/guides/tools-connectors-mcp) and [web-search](https://developers.openai.com/api/docs/guides/tools-web-search) documentation; service-contract applicability not independently verified |
| 2026-10-05 | Display scope, Quran handoff and spike log | Codex / OpenAI | Session identifies GPT-6; exact coding-session provider API identifier not exposed | Documentation, source metadata, local build script and existing test update; no generated religious source content | PR #61 and #62; docs/spike-log-20261005 | Service terms pending verification |

Supporting tools in this session: Buzz CLI (authorized channel messages and reads),
Git/GitHub CLI (branches and PRs), PowerShell, Python 3.11/httpx (bounded API probes
and local artifact build), pytest, Node.js test runner and web search/page retrieval
(primary API documentation only). Skills used: Buzz CLI and OpenAI Docs. No relay-backed
skills loaded. Tool outputs contain metadata; keys are read only from the authorized
dev environment and never recorded. Source permissions stay in SOURCES.md.

The resumed documentation session completed the separate five-call terminology
probe (two earlier urllib requests, three resumed HTTPX requests; zero OpenAI
requests), reconciled the README starting-version disclosure and rebased this PR.
It used Codex, Buzz CLI, Git/GitHub CLI, PowerShell, Python/HTTPX and Node's test
runner. No new model identifier or service-contract claim is inferred from these
transport probes. Results and pending source terms are in
[the terminology follow-up](docs/CONNECTOR_SPIKE_20261005.md#bounded-terminology-follow-up)
and [SOURCES.md](SOURCES.md#terminology-discovery-evidence-2026-10-05).
