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
from corpus.validate import ROOT


def tokens(text: str) -> tuple[str, ...]:
    """Use ar-v1 keys, Unicode word boundaries and case folding for lexical search."""
    return tuple(re.findall(r"[^\W_]+", normalize_arabic(text).casefold()))


@dataclass(frozen=True)
class RetrievalResult:
    record: dict
    retrieval_score: float

    @property
    def corpus_id(self) -> str:
        return self.record["corpus_id"]


class Retriever(Protocol):
    def retrieve(
        self, query: str, *, top_k: int = 5, domain: str | None = None
    ) -> list[RetrievalResult]: ...


class BM25Retriever:
    """Index validated loader output once; keep original records separate from keys.

    Direct construction is an adapter for already validated records (or synthetic
    tests), not a licensing/approval boundary. Use from_artifact for public artifacts;
    a private loader must enforce its own approval and permission gates first.
    """

    def __init__(self, records: Sequence[Mapping], tuning: TuningMetadata):
        self._floor = TuningMetadata.model_validate(tuning.model_dump()).retrieval_score_floor
        self._records = copy.deepcopy([dict(record) for record in records])
        ids = [record["corpus_id"] for record in self._records]
        if any(not isinstance(cid, str) or not cid for cid in ids) or len(set(ids)) != len(ids):
            raise ValueError("corpus ids must be nonempty and unique")
        self._postings: dict[str, dict[int, int]] = defaultdict(dict)
        self._lengths = []
        for index, record in enumerate(self._records):
            if record["text_normalized"] != normalize_arabic(record["text_ar"]):
                raise ValueError("retrieval key differs from ar-v1")
            terms = tokens(record["text_normalized"])
            self._lengths.append(len(terms))
            for term, frequency in Counter(terms).items():
                self._postings[term][index] = frequency
        count = len(self._records)
        self._average_length = sum(self._lengths) / count if count else 0.0
        self._idf = {
            term: math.log(1 + (count - len(postings) + 0.5) / (len(postings) + 0.5))
            for term, postings in self._postings.items()
        }

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
        if domain is not None and (not isinstance(domain, str) or not domain):
            raise ValueError("domain must be a nonempty string or None")
        scores: dict[int, float] = defaultdict(float)
        # Count a query term once: repeating user text cannot inflate its score.
        for term in sorted(set(tokens(query))):
            for index, frequency in self._postings.get(term, {}).items():
                if domain is not None and self._records[index]["domain"] != domain:
                    continue
                # Okapi BM25 with k1=1.5, b=0.75 and positive Robertson IDF.
                length_ratio = self._lengths[index] / self._average_length
                denominator = frequency + 1.5 * (0.25 + 0.75 * length_ratio)
                scores[index] += self._idf[term] * frequency * 2.5 / denominator
        ranked = sorted(
            (index for index, score in scores.items() if score > 0 and score >= self._floor),
            key=lambda index: (-scores[index], self._records[index]["corpus_id"]),
        )
        return [
            RetrievalResult(copy.deepcopy(self._records[index]), scores[index])
            for index in ranked[:top_k]
        ]
