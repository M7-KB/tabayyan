# Tools register

## Owner collector and reference-pack revisions (2026-10-06)

R1 (reference-pack translation), R2 (HadeethEnc owner collector) and R3
(Bayyinat/glossary selectors) were prepared with Claude Sonnet 5, as recorded
in their original material-author commit trailers; the provider identifier was
not independently verified in this session. Codex / OpenAI (session identifies
GPT-6; exact API model ID not exposed) applied the owner's final host, D4 and
heading decisions, checked attribution, ran synthetic offline tests and opened
the review PRs. Authority: Buzz planning event
`5bea83c2bb77c7a0d48ca75c6093bd52af60935ac35470c2879bdb43fbc7d83f`.
Supporting tools: Git/GitHub CLI, bundled Buzz CLI and its local skill,
PowerShell, Node test runner and the existing Python 3.11/pytest workspace
environment. No religious source content was generated, no collector was run
against a publisher, and no outside-workspace source document was read in this
revision session. Account/service terms were not independently verified.

## Private-index implementation log (2026-10-05)

Authority: owner planning event
`d3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f`.
Implementation evidence: R1 [PR #91](https://github.com/M7-KB/tabayyan/pull/91),
R3 [PR #92](https://github.com/M7-KB/tabayyan/pull/92), R2
[PR #94](https://github.com/M7-KB/tabayyan/pull/94), R4
[PR #96](https://github.com/M7-KB/tabayyan/pull/96). These are review branches;
listing them does not claim owner merge, deployment, live quality or source coverage.

| Date | Task | AI tool / provider | Model identifier | Use | Evidence | Terms status |
|---|---|---|---|---|---|---|
| 2026-10-05 | R1/R3/R2/R4 | Codex / OpenAI | Session identifies GPT-6; exact provider API coding-model ID not exposed | Collector, search aliases, private validators, matchers, synthetic tests and docs; no generated religious source text | PRs #91/#92/#94/#96 | Service/account terms not independently verified |
| 2026-10-05 | R4 configured provider | OpenAI embeddings API | `text-embedding-3-large`, 1024 dimensions (configuration only) | Source embeddings at startup and transient query embedding; no actual provider request was made in development | [R4 integration docs](https://github.com/M7-KB/tabayyan/blob/feat/private-index-matchers/docs/PRIVATE_INDEX_MATCHERS.md), [official request reference](https://developers.openai.com/api/reference/resources/embeddings/methods/create) | O5 authorizes published private-index embeddings; account access, billing and live output remain unverified |

Supporting tools used: bundled Buzz CLI (thread reads and authorized result/review
messages), Git/GitHub CLI (worktrees, feature branches and PRs), PowerShell,
Node.js 24.18.0/npm and Node test runner, Python 3.11/pytest with existing workspace
dependencies, Ruff 0.9.10, and official-domain web search/page retrieval for the
embedding API contract. Skills used: Buzz CLI and OpenAI Docs. No relay-backed
skills loaded. No live crawling by agents, source-provider calls or private
religious source files committed. Real owner queries were not used as fixtures.

Collector dependencies: parse5 7.3.0 (MIT), entities 6.0.1 (BSD-2-Clause), pinned
in [the lockfile](https://github.com/M7-KB/tabayyan/blob/feat/owner-private-source-collector/tools/source-collector/package-lock.json).
Installed package licence notices were inspected. R3's own-code MIT notice is
[documented separately](https://github.com/M7-KB/tabayyan/blob/feat/arabic-retrieval-clitics/corpus/RETRIEVAL_NORMALIZER_LICENSE.md).
Code licences grant no source-content permission; those scoped owner decisions
and pending publisher evidence belong in SOURCES.md.

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

## HadeethEnc discovery and held-out handoff (2026-10-05)

Authority: build routing event
`74955bb4a1b90316e3a47f4f39bd1e785f28b286b8ba27415bdd66f65b2b910d`,
channel `49777fe4-55e3-4545-8614-a17a0a9f3a80`.

| Date | Task | AI tool / provider | Verified model identifier | Use | Evidence | Licence / terms status |
|---|---|---|---|---|---|---|
| 2026-10-05 | HadeethEnc item discovery, PR #63 rebase, private held-out handoff | Codex / OpenAI | Session identifies GPT-6; exact coding-session provider API identifier not exposed | Source-adapter code, synthetic adapter tests, documentation and ten synthetic questions; no generated scripture, grade or reference | [Discovery PR #73](https://github.com/M7-KB/tabayyan/pull/73), `e16b22a`; [rebased PR #63 review](https://github.com/M7-KB/tabayyan/pull/63#issuecomment-5990542090), `42c6a9b` | Coding service terms pending verification; source permissions recorded separately in SOURCES.md |

Supporting tools: Buzz CLI (including authorized private delivery to Nami),
Git/GitHub CLI, PowerShell, Python 3.11, pytest, Ruff, Node's test runner, and
web retrieval of [official API documentation](https://github.com/islamhouse-dev/hadith-api).
Skill used: local Buzz CLI. No relay-backed skills or additional OpenAI API calls.
One bounded HadeethEnc discovery invocation with a synthetic topic returned one
request-bound item with internal `grading_source_id: hadeethenc`. Only counts
and provenance metadata were printed; no source religious text persisted. This
is author-executed workstation transport evidence, not deployed accuracy or a
pipeline evaluation. The ten held-out inputs were sent only by DM to Nami,
not used to tune the implementation, run against the pipeline or put in this repo.

## Router reference gates and schema repair (2026-10-06)

Codex / OpenAI (session identifies GPT-6; exact API model identifier unavailable)
implemented owner D2/D3 with synthetic engineering fixtures. Tools: local Buzz CLI
skill, Git/GitHub CLI, PowerShell, Python 3.11, pytest, Ruff and Node test runner.
No collectors, source downloads, model API calls or private source reads were run.

## Collector review corrections (2026-10-06)

Codex / OpenAI, GPT-6 (session model; exact API identifier not exposed), corrected
the owner-supplied glossary heading and synthetic collector-to-loader contract.
PowerShell, Git/GitHub CLI, Buzz CLI, Node, Python/pytest and Ruff were used.
No source collection or product-model calls were made. The v2 loader validates
raw owner fields; it does not infer translations or authorize display.

## Collector rebase and artifact register (2026-10-06)

Codex / OpenAI, GPT-6 (session model; exact API identifier not exposed),
resolved PR #109 documentation conflicts and recorded owner-reported HadeethEnc
private-index metadata. Tools: local Buzz CLI skill, Git/GitHub CLI, PowerShell,
Node test runner, Python/pytest and Ruff. No collector or source request, private
artifact fetch, or product-model API call was made.
