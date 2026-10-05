"""Synthetic ranking and fake HTTP boundaries; no live source or provider calls."""

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from api.bayyinat_matcher import BayyinatMatcher
from api.glossary_matcher import GlossaryMatcher
from api.private_index_search import DIMENSIONS, MODEL, IndexUnavailable, OpenAIIndexEmbedder


def vector(index=0):
    return [1.0 if position == index else 0.0 for position in range(DIMENSIONS)]


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    async def embed(self, texts, *, timeout):
        self.calls.append((list(texts), timeout))
        return [vector() for _ in texts]


def matcher():
    rows = (
        {"id": "b", "title": "ومكتب", "similar_phrasings": ["desk"]},
        {"id": "a", "title": "نافذة", "similar_phrasings": ["window"]},
    )
    embedder = FakeEmbedder()
    return BayyinatMatcher(rows, [vector(), vector(1)], embedder), embedder


def test_hybrid_clitic_query_keeps_raw_record_and_counts_word_once():
    search, embedder = matcher()
    one = asyncio.run(search.candidates("مكتب", level="A"))
    repeated = asyncio.run(search.candidates("مكتب مكتب", level="A"))
    assert one[0].record["title"] == "ومكتب"
    assert one[0].source_id == "bayyinat"
    assert one[0].lexical_score > 0 and one[0].semantic_score == 1
    assert one[0].lexical_score == repeated[0].lexical_score
    one[0].record["title"] = "Changed by consumer"
    assert asyncio.run(search.candidates("مكتب", level="A"))[0].record["title"] == "ومكتب"
    assert not any("query" in key for key in search.__dict__)
    assert len(embedder.calls) == 3


def test_level_d_never_embeds_and_deadline_is_bounded():
    search, embedder = matcher()
    assert asyncio.run(search.candidates("private case", level="D")) == []
    assert embedder.calls == []
    asyncio.run(search.candidates("desk", level="B", timeout=2))
    assert 0 < embedder.calls[0][1] <= 2
    with pytest.raises(ValueError):
        asyncio.run(search.candidates("desk", level="unknown"))


def test_stalled_query_embedder_respects_remaining_deadline():
    search, embedder = matcher()

    async def stall(texts, *, timeout):
        await asyncio.sleep(5)

    embedder.embed = stall
    with pytest.raises(IndexUnavailable, match="index_request_timeout"):
        asyncio.run(search.candidates("desk", level="A", timeout=0.01))


def test_cpu_scoring_with_2000_records_cannot_return_late_candidates():
    rows = tuple(
        {"id": str(index), "title": "Sample desk", "similar_phrasings": []} for index in range(2000)
    )
    search = BayyinatMatcher(rows, [vector()] * len(rows), FakeEmbedder())
    with pytest.raises(IndexUnavailable, match="index_request_timeout"):
        asyncio.run(search.candidates("desk", level="A", timeout=0.001))


def test_expired_lexical_stage_does_not_dispatch_embedding_or_block_event_loop():
    import threading

    search, embedder = matcher()
    entered = threading.Event()
    release = threading.Event()
    original = search._lexical

    def delayed(query, deadline):
        entered.set()
        release.wait(timeout=1)
        return original(query, deadline)

    search._lexical = delayed

    async def run():
        task = asyncio.create_task(search.candidates("desk", level="A", timeout=0.01))
        try:
            with pytest.raises(IndexUnavailable, match="index_request_timeout"):
                await task
            assert entered.is_set()
            assert not release.is_set()
            assert embedder.calls == []
        finally:
            release.set()

    asyncio.run(run())


def test_startup_loads_validated_handoff_before_embedding_and_builds_atomically(tmp_path):
    import hashlib

    from corpus.short_indexes import AUTHORITY_EVENT

    rows = [
        {
            "id": f"/question/{index}",
            "url": f"https://bayenat.net/question/{index}",
            "title": "Sample title",
            "similar_phrasings": [],
            "short_answer": "Short.",
            "keywords": [],
            "category": "",
        }
        for index in range(17)
    ]
    data = "".join(json.dumps(row) + "\n" for row in rows).encode()
    digest = hashlib.sha256(data).hexdigest()
    (tmp_path / "bayyinat.jsonl").write_bytes(data)
    manifest = {
        "format_version": 1,
        "authority_event": AUTHORITY_EVENT,
        "complete": True,
        "files": [
            {
                "file": "bayyinat.jsonl",
                "source_host": "bayenat.net",
                "bytes": len(data),
                "records": 17,
                "sha256": digest,
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    embedder = FakeEmbedder()
    search = asyncio.run(
        BayyinatMatcher.from_private_files(tmp_path, digest, embedder, allow_pending_review=True)
    )
    assert [len(texts) for texts, timeout in embedder.calls] == [16, 1]
    assert len(search._records) == 17
    embedder.calls.clear()
    with pytest.raises(ValueError):
        asyncio.run(
            BayyinatMatcher.from_private_files(
                tmp_path, "0" * 64, embedder, allow_pending_review=True
            )
        )
    assert embedder.calls == []

    async def fail_second(texts, *, timeout):
        if len(texts) == 1:
            raise IndexUnavailable("synthetic_failure")
        return [vector() for _ in texts]

    embedder.embed = fail_second
    with pytest.raises(IndexUnavailable, match="synthetic_failure"):
        asyncio.run(
            BayyinatMatcher.from_private_files(
                tmp_path, digest, embedder, allow_pending_review=True
            )
        )


def test_glossary_uses_publisher_translation_and_missing_translation_stays_missing():
    rows = (
        {"id": "a", "term_ar": "مكتب", "translations": {"English": "desk"}},
        {"id": "b", "term_ar": "نافذة", "translations": {}},
    )
    search = GlossaryMatcher(rows, [vector(), vector(1)], FakeEmbedder())
    result = asyncio.run(search.candidates("desk", level="A"))
    assert result[0].record["translations"] == {"English": "desk"}
    assert result[0].lexical_score > 0
    assert search.search_text(rows[1]) == "نافذة"


def test_no_overlap_and_low_semantic_score_return_no_candidates():
    search, embedder = matcher()

    async def opposite(texts, *, timeout):
        return [[-value for value in vector()] for _ in texts]

    embedder.embed = opposite
    assert asyncio.run(search.candidates("unrelated", level="A")) == []


def test_fixed_embedding_wire_shape_and_index_reordering():
    async def checked():
        def handle(request):
            payload = json.loads(request.content)
            assert str(request.url) == "https://api.openai.com/v1/embeddings"
            assert payload == {
                "model": MODEL,
                "dimensions": 1024,
                "encoding_format": "float",
                "input": ["one", "two"],
            }
            return httpx.Response(
                200,
                json={
                    "model": MODEL,
                    "data": [
                        {"index": 1, "embedding": vector(1)},
                        {"index": 0, "embedding": vector()},
                    ],
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            values = await OpenAIIndexEmbedder(client, SecretStr("synthetic")).embed(
                ["one", "two"], timeout=1
            )
            assert values == [tuple(vector()), tuple(vector(1))]

    asyncio.run(checked())


@pytest.mark.parametrize(
    "data",
    [
        [{"index": 0, "embedding": [1.0]}],
        [{"index": 0, "embedding": [0.0] * DIMENSIONS}],
        [{"index": 0, "embedding": [float("nan")] * DIMENSIONS}],
        [{"index": 1, "embedding": vector()}],
        [{"index": 0, "embedding": vector()}, {"index": 0, "embedding": vector()}],
    ],
)
def test_bad_vectors_fail_closed(data):
    async def run():
        def handle(request):
            # Encode explicitly for the NaN corruption probe.
            return httpx.Response(200, content=json.dumps({"model": MODEL, "data": data}))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(IndexUnavailable):
                await OpenAIIndexEmbedder(client, SecretStr("synthetic")).embed(["one"], timeout=1)

    asyncio.run(run())


def test_http_error_never_exposes_provider_text():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, text="Private provider diagnostic")
            )
        ) as client:
            with pytest.raises(IndexUnavailable) as error:
                await OpenAIIndexEmbedder(client, SecretStr("synthetic")).embed(["one"], timeout=1)
            assert str(error.value) == "embedding_http_error"

    asyncio.run(run())
