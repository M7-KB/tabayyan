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
        result.retrieval_overlap_floor = floor
    return result


@pytest.fixture
def retriever() -> Retriever:
    return BM25Retriever([record(t, f"fixture:{i:02}") for i, t in enumerate(TEXTS)], tuning())


@pytest.mark.parametrize(
    "query,target",
    [("أين أجد " + " ".join(tokens(text)[:2]), f"fixture:{i:02}") for i, text in enumerate(TEXTS)]
    + [("ثلج جليد برد شتاء صقيع", None), ("تفاحة مجهول غامض ثلج جليد", None)],
    ids=[f"synthetic-query-{i:02}" for i in range(1, 13)],
)
def test_twelve_queries_top_five_or_abstain(retriever, query, target):
    results = retriever.retrieve(query)
    if target is None:
        assert results == []
    else:
        assert target in [result.corpus_id for result in results]
        assert all(result.overlap_score >= 0.25 for result in results)


def test_normalization_and_punctuation(retriever):
    assert tokens("إِبْرَة، إبــرة! ABC") == ("ابره", "ابره", "abc")
    query = "أَحْمَر، أَزْرَق! أَخْضَر أَصْفَر أَبْيَض"
    assert retriever.retrieve(query)[0].corpus_id == "fixture:09"


def test_bm25_formula_length_and_frequency():
    records = [record("alpha alpha beta", "a"), record("beta", "b")]
    result = BM25Retriever(records, tuning()).candidates("alpha")[0]
    expected = math.log(2) * 2 * 2.5 / (2 + 1.5 * (0.25 + 0.75 * 3 / 2))
    assert result.retrieval_score == pytest.approx(expected)
    assert result.overlap_score == 1


def test_floor_boundary():
    records = [record("alpha beta")]
    query = "alpha beta gamma delta"
    score = BM25Retriever(records, tuning()).candidates(query)[0].overlap_score
    assert BM25Retriever(records, tuning(score)).retrieve(query)
    assert BM25Retriever(records, tuning(math.nextafter(score, math.inf))).retrieve(query) == []


def test_repeated_query_cannot_raise_score(retriever):
    assert retriever.retrieve("تفاحة " * 100) == retriever.retrieve("تفاحة")
    assert retriever.retrieve(TEXTS[0] * 1) == retriever.retrieve((TEXTS[0] + " ") * 100)


def test_domain_filter_and_top_k_keep_global_scores():
    records = [record("alpha beta", "z", "faq"), record("alpha beta", "a", "glossary")]
    search = BM25Retriever(records, tuning())
    assert [r.corpus_id for r in search.retrieve("alpha", top_k=1)] == ["a"]
    filtered = search.retrieve("alpha", domain="faq")
    assert [r.corpus_id for r in filtered] == ["z"]
    assert filtered[0].retrieval_score == search.retrieve("alpha")[1].retrieval_score
    assert search.retrieve("alpha", domain="missing") == []
    reversed_search = BM25Retriever(list(reversed(records)), tuning())
    assert search.retrieve("alpha") == reversed_search.retrieve("alpha")


@pytest.mark.parametrize("query", ["", "   ", "?!", "absent"])
def test_no_tokens_or_overlap_returns_empty(query):
    assert BM25Retriever([record("alpha")], tuning()).retrieve(query) == []
    assert BM25Retriever([], tuning()).retrieve(query) == []
    assert BM25Retriever([record("!!!")], tuning()).retrieve(query) == []


def test_original_text_and_nested_provenance_are_isolated():
    original = record("إِبْرَة إبــرة")
    search = BM25Retriever([original], tuning())
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
        assert BM25Retriever.from_artifact(tuning()).retrieve("alpha")[0].corpus_id == "fixture:one"


@pytest.mark.parametrize("count", [1, 10, 4471, 10000])
def test_gate_is_independent_of_corpus_size_and_unrelated_lengths(count):
    target = record("alpha beta gamma delta epsilon", "target")
    records = [target] + [
        record("unrelated " * (1 + i % 30), f"filler:{i}") for i in range(count - 1)
    ]
    search = BM25Retriever(records, tuning())
    assert search.retrieve("alpha unknown unseen absent missing") == []
    assert search.candidates("alpha unknown unseen absent missing")[0].overlap_score == 0.2
    assert search.retrieve("alpha beta gamma delta epsilon")[0].overlap_score == 1


def test_candidates_preserve_below_floor_twins_and_all_records_by_default():
    records = [record("alpha beta", f"twin:{i:02}") for i in range(8)]
    records.append(record("alpha changed", "near-miss"))
    search = BM25Retriever(records, tuning())
    query = "alpha beta unknown unseen absent missing extra additional further"
    assert search.retrieve(query) == []
    candidates = search.candidates(query)
    assert {r.corpus_id for r in candidates} == {r["corpus_id"] for r in records}
    assert search.candidates(query, top_k=2) == candidates[:2]
    candidates[0].record["ref"]["number"] = "changed"
    assert search.candidates(query)[0].record["ref"]["number"] == "synthetic"


@pytest.mark.parametrize("limit", [0, -1, 1.5, True, "5"])
def test_invalid_candidate_limit(limit, retriever):
    with pytest.raises(ValueError, match="top_k"):
        retriever.candidates("anything", top_k=limit)


def test_candidate_domain_and_empty_query(retriever):
    assert retriever.candidates(TEXTS[0], domain="missing") == []
    assert retriever.candidates("") == []
    with pytest.raises(ValueError, match="domain"):
        retriever.candidates(TEXTS[0], domain="")


@pytest.mark.parametrize("length", [1, 2, 3, 4, 5, 12, 30])
def test_full_overlap_can_clear_gate_at_every_query_length(length):
    query = " ".join(f"term{i}" for i in range(length))
    result = BM25Retriever([record(query + " unrelated extra")], tuning()).retrieve(query)[0]
    assert result.overlap_score == 1


@pytest.mark.parametrize(
    "query,text",
    [
        ("apple", "apple orange banana"),
        ("blue pencil", "blue pencil notebook paper"),
        ("where can I find the blue pencil", "blue pencil notebook paper"),
        ("please describe a notebook and paper for writing", "paper notebook writing supplies"),
        ("quote beta gamma", "alpha beta gamma delta epsilon"),
        (
            "explain alpha beta gamma delta with some other extra absent terms please",
            "alpha beta gamma delta epsilon",
        ),
    ],
)
def test_non_verbatim_questions_and_partial_quotes(query, text):
    assert query != text
    result = BM25Retriever([record(text)], tuning()).retrieve(query)[0]
    assert result.corpus_id == "fixture:one"


def test_denominator_is_tunable_and_independent_of_bm25_floor():
    config = tuning()
    config.retrieval_overlap_min_terms = 5
    search = BM25Retriever([record("alpha beta")], config)
    assert search.candidates("alpha")[0].overlap_score == 0.2
    assert search.retrieve("alpha") == []
    config.retrieval_overlap_min_terms = 1
    config.retrieval_score_floor = 100000
    assert BM25Retriever([record("alpha beta")], config).retrieve("alpha")


@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_invalid_minimum_denominator(value):
    config = tuning()
    config.retrieval_overlap_min_terms = value
    with pytest.raises(ValueError):
        BM25Retriever([], config)
