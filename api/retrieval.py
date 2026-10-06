"""Local BM25 candidates; lexical scores never authorize evidence or alignment."""

import copy
import math
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from api.config import TuningMetadata
from corpus.loader import load_corpus
from corpus.normalize import normalize_arabic
from corpus.quran_binding import matching_text
from corpus.retrieval_normalize import retrieval_token_groups
from corpus.validate import ROOT


def tokens(text: str) -> tuple[str, ...]:
    """Use ar-v1 keys, Unicode word boundaries and case folding for lexical search."""
    return tuple(re.findall(r"[^\W_]+", normalize_arabic(text).casefold()))


@dataclass(frozen=True)
class RetrievalResult:
    record: dict
    retrieval_score: float
    overlap_score: float

    @property
    def corpus_id(self) -> str:
        return self.record["corpus_id"]


class Retriever(Protocol):
    def candidates(
        self, query: str, *, top_k: int | None = None, domain: str | None = None
    ) -> list[RetrievalResult]: ...

    def retrieve(
        self, query: str, *, top_k: int = 5, domain: str | None = None
    ) -> list[RetrievalResult]: ...


class BM25Retriever:
    """Index validated loader output once; keep original records separate from keys.

    Direct construction is an adapter for already validated records (or synthetic
    tests), not a licensing/approval boundary. Use from_artifact for public artifacts;
    a private loader must enforce its own approval and permission gates first.
    """

    def __init__(
        self,
        records: Sequence[Mapping],
        tuning: TuningMetadata,
        *,
        base: "BM25Retriever | None" = None,
    ):
        validated = TuningMetadata.model_validate(tuning.model_dump())
        self._tuning = validated
        self._overlap_floor = validated.retrieval_overlap_floor
        self._min_terms = validated.retrieval_overlap_min_terms
        # A derived retriever shares the base layer's postings and copies a term's
        # postings only when an added record extends it, so the base is never
        # mutated. IDF and average length are computed over all records at
        # query time, so results equal an index built from scratch over them.
        base_records = base._records if base is not None else []
        added = copy.deepcopy([dict(record) for record in records])
        self._records = [*base_records, *added]
        ids = [record["corpus_id"] for record in self._records]
        if any(not isinstance(cid, str) or not cid for cid in ids) or len(set(ids)) != len(ids):
            raise ValueError("corpus ids must be nonempty and unique")
        self._postings: dict[str, dict[int, int]] = dict(base._postings) if base else {}
        shared = set(self._postings)
        self._lengths = list(base._lengths) if base is not None else []
        for offset, record in enumerate(added):
            index = len(base_records) + offset
            if record["text_normalized"] != normalize_arabic(matching_text(record)):
                raise ValueError("retrieval key differs from ar-v1")
            groups = retrieval_token_groups(record["text_normalized"])
            self._lengths.append(len(groups))
            for term, frequency in Counter(alias for group in groups for alias in group).items():
                if term in shared:
                    shared.discard(term)
                    self._postings[term] = dict(self._postings[term])
                self._postings.setdefault(term, {})[index] = frequency
        self._count = len(self._records)
        self._average_length = sum(self._lengths) / self._count if self._count else 0.0

    def extend(self, records: Sequence[Mapping]) -> "BM25Retriever":
        """A retriever over this index plus more records, indexing only the new ones."""
        if not records:
            return self
        return BM25Retriever(records, self._tuning, base=self)

    def _idf(self, term: str) -> float:
        # Okapi positive Robertson IDF over every indexed record.
        df = len(self._postings[term])
        return math.log(1 + (self._count - df + 0.5) / (df + 0.5))

    @classmethod
    def from_artifact(
        cls,
        tuning: TuningMetadata,
        path: Path = ROOT / "corpus/corpus.jsonl",
        *,
        sources_path: Path = ROOT / "corpus/approved_sources.json",
        register_path: Path = ROOT / "SOURCES.md",
    ) -> "BM25Retriever":
        return cls(
            load_corpus(path, sources_path=sources_path, register_path=register_path), tuning
        )

    def retrieve(
        self, query: str, *, top_k: int = 5, domain: str | None = None
    ) -> list[RetrievalResult]:
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        return [
            result
            for result in self.candidates(query, domain=domain)
            if result.overlap_score >= self._overlap_floor
        ][:top_k]

    def candidates(
        self, query: str, *, top_k: int | None = None, domain: str | None = None
    ) -> list[RetrievalResult]:
        """Return positive-overlap records without the evidence floor or deduplication.

        Default to all candidates so near-miss detection can inspect low-scoring
        twins. These candidates do not authorize evidence or bypass approval.
        """
        if top_k is not None and (type(top_k) is not int or top_k < 1):
            raise ValueError("top_k must be a positive integer or None")
        if domain is not None and (not isinstance(domain, str) or not domain):
            raise ValueError("domain must be a nonempty string or None")
        scores: dict[int, float] = defaultdict(float)
        overlap: Counter = Counter()
        query_terms = set(retrieval_token_groups(query))
        # Count a query term once: repeating user text cannot inflate its score.
        for group in sorted(query_terms):
            frequencies = {}
            for alias in group:
                postings = self._postings.get(alias)
                if not postings:
                    continue
                idf = self._idf(alias)
                for index, frequency in postings.items():
                    score = (frequency, idf)
                    if index not in frequencies or score > frequencies[index]:
                        frequencies[index] = score
            for index, (frequency, idf) in frequencies.items():
                if domain is not None and self._records[index]["domain"] != domain:
                    continue
                # Okapi BM25 with k1=1.5, b=0.75 and positive Robertson IDF.
                length_ratio = self._lengths[index] / self._average_length
                denominator = frequency + 1.5 * (0.25 + 0.75 * length_ratio)
                scores[index] += idf * frequency * 2.5 / denominator
                overlap[index] += 1
        ranked = sorted(
            (index for index, score in scores.items() if score > 0),
            key=lambda index: (-scores[index], self._records[index]["corpus_id"]),
        )
        return [
            RetrievalResult(
                copy.deepcopy(self._records[index]),
                scores[index],
                overlap[index] / max(self._min_terms, len(query_terms)),
            )
            for index in ranked[:top_k]
        ]
