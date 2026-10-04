"""Synthetic non-religious fixtures; no scripture, references or gradings invented."""

import math
from pathlib import Path
from unittest.mock import patch

import pytest

from api.config import load_config
from api.retrieval import BM25Retriever, Retriever, tokens
from corpus.normalize import normalize_arabic

ROOT = Path(__file__).resolve().parents[1]
TEXTS = [
    "تفاحة برتقال موز عنب رمان",
    "قلم دفتر ورقة مسطرة حقيبة",
    "قطار محطة تذكرة عربة سكة",
    "حاسوب شاشة لوحة مفاتيح فأرة",
    "طاولة كرسي سرير خزانة رف",
    "حديقة زهرة شجرة غصن ورق",
    "قارب بحر ميناء شراع مرساة",
    "مطبخ ملعقة طبق كوب قدر",
    "نافذة باب سقف جدار أرضية",
    "أحمر أزرق أخضر أصفر أبيض",
]


def record(text, cid="fixture:one", domain="faq"):
    return {
        "corpus_id": cid,
        "domain": domain,
        "text_ar": text,
        "text_normalized": normalize_arabic(text),
        "source_id": "synthetic",
        "ref": {"number": "synthetic"},
    }


def tuning(floor=None):
    _, result = load_config(ROOT / "api/policy/content_policy.yaml", ROOT / "api/tuning.yaml")
    if floor is not None:
        result.retrieval_score_floor = floor
    return result


@pytest.fixture
def retriever() -> Retriever:
    return BM25Retriever([record(t, f"fixture:{i:02}") for i, t in enumerate(TEXTS)], tuning())


@pytest.mark.parametrize(
    "query,target",
    [(text, f"fixture:{i:02}") for i, text in enumerate(TEXTS)]
    + [("ثلج جليد برد شتاء صقيع", None), ("تفاحة مجهول", None)],
    ids=[f"synthetic-query-{i:02}" for i in range(1, 13)],
)
def test_twelve_queries_top_five_or_abstain(retriever, query, target):
    results = retriever.retrieve(query)
    if target is None:
        assert results == []
    else:
        assert target in [result.corpus_id for result in results]
        assert all(result.retrieval_score >= 8 for result in results)


def test_normalization_and_punctuation(retriever):
    assert tokens("إِبْرَة، إبــرة! ABC") == ("ابره", "ابره", "abc")
    query = "أَحْمَر، أَزْرَق! أَخْضَر أَصْفَر أَبْيَض"
    assert retriever.retrieve(query)[0].corpus_id == "fixture:09"


def test_bm25_formula_length_and_frequency():
    records = [record("alpha alpha beta", "a"), record("beta", "b")]
    result = BM25Retriever(records, tuning(0)).retrieve("alpha")[0]
    expected = math.log(2) * 2 * 2.5 / (2 + 1.5 * (0.25 + 0.75 * 3 / 2))
    assert result.retrieval_score == pytest.approx(expected)


def test_floor_boundary():
    records = [record("alpha beta")]
    score = BM25Retriever(records, tuning(0)).retrieve("alpha beta")[0].retrieval_score
    assert BM25Retriever(records, tuning(score)).retrieve("alpha beta")
    assert (
        BM25Retriever(records, tuning(math.nextafter(score, math.inf))).retrieve("alpha beta") == []
    )


def test_repeated_query_cannot_raise_score(retriever):
    assert retriever.retrieve("تفاحة " * 100) == []
    assert retriever.retrieve(TEXTS[0] * 1) == retriever.retrieve((TEXTS[0] + " ") * 100)


def test_domain_filter_and_top_k_keep_global_scores():
    records = [record("alpha beta", "z", "faq"), record("alpha beta", "a", "glossary")]
    search = BM25Retriever(records, tuning(0))
    assert [r.corpus_id for r in search.retrieve("alpha", top_k=1)] == ["a"]
    filtered = search.retrieve("alpha", domain="faq")
    assert [r.corpus_id for r in filtered] == ["z"]
    assert filtered[0].retrieval_score == search.retrieve("alpha")[1].retrieval_score
    assert search.retrieve("alpha", domain="missing") == []
    reversed_search = BM25Retriever(list(reversed(records)), tuning(0))
    assert search.retrieve("alpha") == reversed_search.retrieve("alpha")


@pytest.mark.parametrize("query", ["", "   ", "?!", "absent"])
def test_no_tokens_or_overlap_returns_empty(query):
    assert BM25Retriever([record("alpha")], tuning(0)).retrieve(query) == []
    assert BM25Retriever([], tuning(0)).retrieve(query) == []
    assert BM25Retriever([record("!!!")], tuning(0)).retrieve(query) == []


def test_original_text_and_nested_provenance_are_isolated():
    original = record("إِبْرَة إبــرة")
    search = BM25Retriever([original], tuning(0))
    original["text_ar"] = "changed"
    original["ref"]["number"] = "changed"
    result = search.retrieve("ابره")[0]
    assert result.record["text_ar"] == "إِبْرَة إبــرة"
    assert result.record["ref"]["number"] == "synthetic"
    result.record["text_ar"] = "changed again"
    result.record["ref"]["number"] = "changed again"
    assert search.retrieve("ابره")[0].record["text_ar"] == "إِبْرَة إبــرة"
    assert search.retrieve("ابره")[0].record["ref"]["number"] == "synthetic"


@pytest.mark.parametrize("limit", [0, -1, 1.5, True, "5"])
def test_invalid_limit(limit, retriever):
    with pytest.raises(ValueError, match="top_k"):
        retriever.retrieve("anything", top_k=limit)


@pytest.mark.parametrize("floor", [-1, math.nan, math.inf])
def test_invalid_floor(floor):
    with pytest.raises(ValueError):
        BM25Retriever([], tuning(floor))


def test_duplicate_ids_and_key_drift_fail():
    with pytest.raises(ValueError, match="unique"):
        BM25Retriever([record("one"), record("two")], tuning())
    with pytest.raises(ValueError, match="ar-v1"):
        BM25Retriever([record("one") | {"text_normalized": "two"}], tuning())


def test_artifact_factory_propagates_loader_validation(tmp_path):
    with patch("api.retrieval.load_corpus", side_effect=ValueError("approval rejected")) as loader:
        with pytest.raises(ValueError, match="approval rejected"):
            BM25Retriever.from_artifact(tuning(), tmp_path / "corpus.jsonl")
        loader.assert_called_once()
    with patch("api.retrieval.load_corpus", return_value=[record("alpha")]) as loader:
        assert (
            BM25Retriever.from_artifact(tuning(0)).retrieve("alpha")[0].corpus_id == "fixture:one"
        )
