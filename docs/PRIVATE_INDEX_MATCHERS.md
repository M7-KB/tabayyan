# Private candidate matchers (R4)

Dependencies: R2 private loaders and R3 grouped search aliases. No source files
are bundled; actual owner collection/inspection is still required. The PR is
stacked on R2, with the independently approved R3 commit included as a dependency.

One module per source: `api.bayyinat_matcher.BayyinatMatcher` matches question
titles and similar phrasings; `api.glossary_matcher.GlossaryMatcher` matches
publisher terms and supplied translations. Both use the shared
`api.private_index_search` BM25/embedding transport and ranker.

At startup, call `await Matcher.from_private_files(directory, trusted_sha256,
embedder, allow_pending_review=...)`. This always invokes the R2 loader first;
construction fails atomically if any batch fails. Vectors and source records
live in memory only, without disk indexes. Source embeddings use
`text-embedding-3-large`, 1024 dimensions, float encoding, batches of 16.
Each input is bounded to 8000 UTF-8 bytes, a conservative token upper bound.
Oversized fields fail instead of silently truncating source meaning.

Pass the shared HTTPX client and runtime SecretStr key to OpenAIIndexEmbedder.
Its URL/model are fixed, redirects are refused, failures contain categories only,
and the caller bounds startup/request time. No live provider access was tested.
The [official embedding request/response reference](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
documents dimensions, float encoding and indexed responses. O5 in owner event
`d3f6a64c16cd66be3207b50eb507c50692307566724b43abc5c1a356b325ed7f`
authorizes sending published private-index text for embeddings.

For each request call `await matcher.candidates(query, level=level,
timeout=remaining_seconds)`. Level D returns an empty list without embedding.
An allowed query goes to the same AI provider under the existing input disclosure;
its vector is transient, never cached or saved. This embedding request is in
addition to the router/composer calls; V3 must account for it in the 35 s deadline.
No query reaches the publisher, and the matcher makes no source HTTP requests.

The supplied budget covers lexical scoring, embedding and cosine/fusion ranking
under one absolute deadline. CPU scoring runs off the event loop and checks
expiry during its loops; the embedding gets only the remaining budget. Expired
work cannot dispatch embedding or return late candidates. Cancelled workers may
finish a bounded primitive before the next checkpoint; their result is discarded.

BM25 uses one best alias match per query word; repetitions do not inflate its
score. Cosine candidates below 0.25 are dropped (configurable); reciprocal-rank
fusion uses 1/(60+rank) and deterministic ID ties. The top five records are
candidates only. Fusion scores are ranks, **not calibrated confidence**. They
never mean support, alignment, quote authorization or agreement between sources.
Semantic-only candidates still require the existing composer and gatekeeper.
Actual retrieval quality and thresholds await live/held-out evaluation.

V3 integration remains separate: use validated record IDs and source provenance,
copy only the exact short source field, retain source attribution/link, apply
embedded scripture/hadith gates, and preserve retryable failure policy. An
embedding timeout raises IndexUnavailable; it must not be presented as a
CANNOT_CONFIRM result implying no evidence. The API and deployment config are
not changed here.
