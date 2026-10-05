# Private short-index handoff (R2)

Owner authority: planning event
`d3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f`,
2026-10-05, O1 and O2. See [the source register](../SOURCES.md#owner-short-index-decision-2026-10-05).

`corpus.short_indexes.load_short_index(directory, source_id, expected_sha256)`
loads R1 JSONL plus manifest from the owner's private directory. Sources are
`bayyinat` and `jamhara-glossary`; the SHA-256 must come from the trusted owner
handoff. Set `owner_review_event` to the owner's review event or explicitly use
`allow_pending_review=True` under the existing pending-review owner decision.
This does not imply that review happened. Do not compute the expected hash
automatically from the same untrusted file you are about to load.

The loader enforces complete manifests, source permissions, bounded file and
field sizes, exact fields/types, duplicate keys/IDs, HTTPS host/path binding,
record counts and original-byte hashes. It performs no normalization, repairs,
fetching, translation or generated content. Empty translations stay empty.
Failures contain fixed reasons without source text. No partial index is returned.

URL identity preserves the complete path and permitted page/lang/language query
selectors. It does not strip language selectors or merge different source pages.
Unrelated Bayyinat routes, parent segments and encoded separator bypasses fail.
The actual collector-to-loader integration test is
`tests/r1-r2-handoff.test.mjs`; set R1_COLLECTOR_PATH to the R1 module path and
R2_TEST_PYTHON to Python 3.11+ while the dependency PRs are separate. After R1
merges, its default path is the collector in this repository. The test uses only
synthetic HTML/fake fetches, never source requests.

Output records are search candidates only. R4 returns their IDs; V3 must bind
source provenance and copy the exact short field into the existing gatekeeper.
The gatekeeper must separately check embedded scripture/hadith and output level.
Loading does not authorize a whole answer, personal fatwa, translation inference,
source bulk display/download or public file redistribution. R2 does not wire the
API, change startup config, fetch files, or enable live sources by itself.

Owner action: run R1, inspect skipped/failure reasons and sample short fields,
then hand off the private directory, both JSONL hashes and review status. Live
files were not available during development, so corpus coverage remains pending.
