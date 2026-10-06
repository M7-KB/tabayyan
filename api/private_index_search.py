"""In-memory hybrid candidates; never quote authorization or query storage."""

import asyncio
import copy
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

import httpx
from pydantic import SecretStr

from corpus.retrieval_normalize import retrieval_token_groups
from corpus.short_indexes import load_short_index

MODEL = "text-embedding-3-large"
DIMENSIONS = 1024


def _embedding_text(text: str) -> str:
    # Bound only the indexing input; keep complete raw records and lexical text.
    return text.encode("utf-8")[:8000].decode("utf-8", errors="ignore").strip()


class IndexUnavailable(RuntimeError):
    """Text-free retrieval failure; caller uses its retryable failure policy."""


def _check_deadline(deadline: float) -> None:
    if perf_counter() >= deadline:
        raise IndexUnavailable("index_request_timeout")


def _unit(vector: object) -> tuple[float, ...]:
    if not isinstance(vector, (list, tuple)) or len(vector) != DIMENSIONS:
        raise IndexUnavailable("invalid_embedding")
    if any(type(value) not in {int, float} or not math.isfinite(value) for value in vector):
        raise IndexUnavailable("invalid_embedding")
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(norm) or norm == 0:
        raise IndexUnavailable("invalid_embedding")
    return tuple(value / norm for value in vector)


class Embedder(Protocol):
    async def embed(self, texts: list[str], *, timeout: float) -> list[tuple[float, ...]]: ...


class OpenAIIndexEmbedder:
    """Fixed model/endpoint, shared client, no retries/caches/logged text."""

    def __init__(self, client: httpx.AsyncClient, key: SecretStr, *, model: str = MODEL):
        self._client = client
        self._key = key
        if model != MODEL:
            raise IndexUnavailable("invalid_embedding_model")
        self._model = model

    async def embed(self, texts: list[str], *, timeout: float) -> list[tuple[float, ...]]:
        # Conservative token upper bound via UTF-8 bytes, not an English word heuristic.
        if (
            not texts
            or len(texts) > 16
            or any(
                not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 8000
                for text in texts
            )
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise IndexUnavailable("invalid_embedding_input")
        try:
            async with asyncio.timeout(timeout):
                response = await self._client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._key.get_secret_value()}"},
                    json={
                        "model": self._model,
                        "dimensions": DIMENSIONS,
                        "encoding_format": "float",
                        "input": texts,
                    },
                    timeout=httpx.Timeout(timeout, connect=min(5, timeout)),
                    follow_redirects=False,
                )
                if response.status_code != 200:
                    raise IndexUnavailable("embedding_http_error")
                if len(response.content) > 2 * 1024 * 1024:
                    raise IndexUnavailable("invalid_embedding_response")
                payload = response.json()
            if not isinstance(payload, dict) or payload.get("model") != self._model:
                raise IndexUnavailable("invalid_embedding_response")
            rows = payload.get("data")
            if not isinstance(rows, list) or len(rows) != len(texts):
                raise IndexUnavailable("invalid_embedding_response")
            result = {}
            for row in rows:
                if not isinstance(row, dict) or type(row.get("index")) is not int:
                    raise IndexUnavailable("invalid_embedding_response")
                index = row["index"]
                if index in result or not 0 <= index < len(texts):
                    raise IndexUnavailable("invalid_embedding_response")
                result[index] = _unit(row.get("embedding"))
            return [result[index] for index in range(len(texts))]
        except IndexUnavailable:
            raise
        except (httpx.HTTPError, TimeoutError, ValueError, TypeError, OverflowError):
            raise IndexUnavailable("embedding_unavailable") from None


@dataclass(frozen=True)
class IndexCandidate:
    source_id: str
    record: dict
    fusion_score: float
    lexical_score: float
    semantic_score: float


class PrivateIndexMatcher:
    """Use from_private_files for real data; direct construction is a test adapter."""

    source_id: str

    def __init__(self, records: tuple[dict, ...], vectors: list, embedder: Embedder):
        if not records or len(records) != len(vectors):
            raise IndexUnavailable("invalid_index")
        self._records = copy.deepcopy(records)
        ids = [row["id"] for row in records]
        if len(set(ids)) != len(ids):
            raise IndexUnavailable("invalid_index")
        self._vectors = tuple(_unit(vector) for vector in vectors)
        self._embedder = embedder
        self._postings = defaultdict(dict)
        self._lengths = []
        for index, row in enumerate(records):
            groups = retrieval_token_groups(self.search_text(row))
            self._lengths.append(len(groups))
            frequencies = Counter(alias for group in groups for alias in set(group))
            for alias, frequency in frequencies.items():
                self._postings[alias][index] = frequency
        self._average = sum(self._lengths) / len(records)

    @staticmethod
    def search_text(row: dict) -> str:
        raise NotImplementedError

    @classmethod
    async def from_private_files(
        cls,
        directory: Path,
        expected_sha256: str,
        embedder: Embedder,
        *,
        startup_timeout: float = 300,
        **loader_options,
    ):
        if not math.isfinite(startup_timeout) or startup_timeout <= 0:
            raise ValueError("invalid_startup_timeout")
        records = load_short_index(directory, cls.source_id, expected_sha256, **loader_options)
        vectors = []
        # Publish no partially built matcher; startup failure leaves the index disabled.
        try:
            async with asyncio.timeout(startup_timeout):
                for offset in range(0, len(records), 16):
                    batch = [
                        _embedding_text(cls.search_text(row))
                        for row in records[offset : offset + 16]
                    ]
                    vectors.extend(await embedder.embed(batch, timeout=min(30, startup_timeout)))
        except TimeoutError:
            raise IndexUnavailable("index_startup_timeout") from None
        return cls(records, vectors, embedder)

    def _lexical(self, query: str, deadline: float) -> dict[int, float]:
        _check_deadline(deadline)
        scores = defaultdict(float)
        # Repeated words and multiple aliases cannot multiply one query word's score.
        groups = dict.fromkeys(retrieval_token_groups(query))
        _check_deadline(deadline)
        count = len(self._records)
        for group in groups:
            _check_deadline(deadline)
            best = defaultdict(float)
            for alias in group:
                postings = self._postings.get(alias, {})
                idf = math.log(1 + (count - len(postings) + 0.5) / (len(postings) + 0.5))
                for index, frequency in postings.items():
                    _check_deadline(deadline)
                    ratio = self._lengths[index] / self._average
                    score = idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * ratio))
                    best[index] = max(best[index], score)
            for index, score in best.items():
                scores[index] += score
        return dict(scores)

    def _rank(
        self,
        lexical: dict[int, float],
        vectors: list,
        top_k: int,
        semantic_floor: float,
        deadline: float,
    ) -> list[IndexCandidate]:
        """Worker-local scoring with cooperative expiry; no late/partial result."""
        _check_deadline(deadline)
        if len(vectors) != 1:
            raise IndexUnavailable("invalid_embedding_response")
        vector = _unit(vectors[0])
        semantic = {}
        for index, stored in enumerate(self._vectors):
            _check_deadline(deadline)
            score = sum(a * b for a, b in zip(vector, stored, strict=True))
            if score >= semantic_floor:
                semantic[index] = score
        fusion = defaultdict(float)
        for scores in (lexical, semantic):
            _check_deadline(deadline)
            ranked = sorted(scores, key=lambda index: (-scores[index], self._records[index]["id"]))
            for rank, index in enumerate(ranked, 1):
                _check_deadline(deadline)
                fusion[index] += 1 / (60 + rank)
        ranked = sorted(fusion, key=lambda index: (-fusion[index], self._records[index]["id"]))
        result = []
        for index in ranked[:top_k]:
            _check_deadline(deadline)
            result.append(
                IndexCandidate(
                    self.source_id,
                    copy.deepcopy(self._records[index]),
                    fusion[index],
                    lexical.get(index, 0),
                    semantic.get(index, 0),
                )
            )
        _check_deadline(deadline)
        return result

    async def candidates(
        self,
        query: str,
        *,
        level: str,
        top_k: int = 5,
        timeout: float = 10,
        semantic_floor: float = 0.25,
    ) -> list[IndexCandidate]:
        """No level D calls. Query vector is transient; never cached on the matcher.

        Timeout is the remaining V3 request budget, capped at 10 seconds here.
        A retrieval failure raises a text-free error instead of inventing no evidence.
        Fusion rank is not confidence, alignment or a SUPPORTED decision.
        """
        if level not in {"A", "B", "C", "D"}:
            raise ValueError("invalid_content_level")
        if level == "D":
            return []
        if type(top_k) is not int or not 1 <= top_k <= 5:
            raise ValueError("invalid_top_k")
        if not math.isfinite(semantic_floor) or not 0 <= semantic_floor <= 1:
            raise ValueError("invalid_semantic_floor")
        if not math.isfinite(timeout) or timeout <= 0:
            raise IndexUnavailable("index_request_timeout")
        if not query.strip():
            return []
        budget = min(timeout, 10)
        deadline = perf_counter() + budget
        loop_deadline = asyncio.get_running_loop().time() + budget
        try:
            # Offload CPU work so request/HTTP timers can run. Worker checkpoints
            # use the same absolute deadline; late results are never returned.
            async with asyncio.timeout_at(loop_deadline):
                lexical = await asyncio.to_thread(self._lexical, query, deadline)
                _check_deadline(deadline)
                vectors = await self._embedder.embed(
                    [_embedding_text(query)], timeout=deadline - perf_counter()
                )
                _check_deadline(deadline)
                result = await asyncio.to_thread(
                    self._rank, lexical, vectors, top_k, semantic_floor, deadline
                )
                _check_deadline(deadline)
                return result
        except TimeoutError:
            raise IndexUnavailable("index_request_timeout") from None
