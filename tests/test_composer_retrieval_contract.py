"""Retrieval prerequisites for T-502; these do not yet test card alignment.

Synthetic non-religious records isolate SPEC 5.4's overlap gate from BM25 rank.
The composer must additionally enforce source, verbatim, detector and confidence gates.
"""

from pathlib import Path

import pytest

from api.config import load_config
from api.retrieval import BM25Retriever
from corpus.normalize import normalize_arabic

ROOT = Path(__file__).resolve().parents[1]


def record(text, cid):
    return {
        "corpus_id": cid,
        "domain": "faq",
        "text_ar": text,
        "text_normalized": normalize_arabic(text),
    }


def config():
    _, tuning = load_config(ROOT / "api/policy/content_policy.yaml", ROOT / "api/tuning.yaml")
    return tuning


def test_high_raw_score_cannot_rescue_below_overlap_evidence():
    tuning = config()
    records = [record("alpha", "target")] + [
        record("unrelated", f"filler:{i}") for i in range(9999)
    ]
    search = BM25Retriever(records, tuning)
    query = "alpha beta gamma delta epsilon"
    candidate = search.candidates(query)[0]
    assert candidate.retrieval_score > tuning.retrieval_score_floor
    assert candidate.overlap_score == pytest.approx(0.2)
    assert candidate.overlap_score < tuning.retrieval_overlap_floor
    assert search.retrieve(query) == []


def test_low_raw_score_does_not_veto_above_overlap_evidence():
    tuning = config()
    search = BM25Retriever([record("alpha beta", "target")], tuning)
    query = "alpha unknown"
    candidate = search.candidates(query)[0]
    assert candidate.retrieval_score < tuning.retrieval_score_floor
    assert candidate.overlap_score == pytest.approx(0.5)
    assert candidate.overlap_score > tuning.retrieval_overlap_floor
    assert search.retrieve(query) == [candidate]


def test_exact_overlap_floor_is_inclusive():
    tuning = config()
    search = BM25Retriever([record("alpha", "target")], tuning)
    query = "alpha beta gamma delta"
    candidate = search.candidates(query)[0]
    assert candidate.overlap_score == tuning.retrieval_overlap_floor == 0.25
    assert search.retrieve(query) == [candidate]
