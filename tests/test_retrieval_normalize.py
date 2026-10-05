"""Synthetic non-religious search fixtures; original strings remain untouched."""

import pytest

from corpus.normalize import NORMALIZER_VERSION, normalize_arabic
from corpus.retrieval_normalize import retrieval_token_groups, retrieval_tokens


@pytest.mark.parametrize(
    "word,alias",
    [
        ("ومكتب", "مكتب"),
        ("فمكتب", "مكتب"),
        ("بمكتب", "مكتب"),
        ("كمكتب", "مكتب"),
        ("لمكتب", "مكتب"),
        ("المكتب", "مكتب"),
        ("بالمكتب", "مكتب"),
        ("كالمكتب", "مكتب"),
        ("للمكتب", "مكتب"),
        ("وبالمكتب", "مكتب"),
        ("فللمكتب", "مكتب"),
        ("وَالْمَكْتَبُ", "مكتب"),
    ],
)
def test_prefix_combinations(word, alias):
    group = retrieval_token_groups(word)[0]
    assert group[0] == normalize_arabic(word)
    assert alias in group
    assert len(group) == len(set(group))


def test_keep_ambiguous_stems_and_do_not_invent_suffix_or_root_analysis():
    assert retrieval_token_groups("ورق") == (("ورق",),)
    assert retrieval_token_groups("باب") == (("باب",),)
    assert "ورد" in retrieval_tokens("ورد")
    assert "مكتب" not in retrieval_tokens("مكتبات")
    assert "كتب" not in retrieval_tokens("مكتبات")
    assert "حديقه" in retrieval_tokens("حديقة")


def test_non_arabic_digits_punctuation_and_question_intent_are_preserved():
    assert retrieval_token_groups("Book42 ABC ١٢٣") == (("book42",), ("abc",), ("١٢٣",))
    assert retrieval_token_groups("ومكتب، وباب!") == (("ومكتب", "مكتب"), ("وباب", "باب"))
    question = "هل أجد بالمكتب كتابا؟"
    assert retrieval_token_groups(question)[0] == ("هل",)
    assert question == "هل أجد بالمكتب كتابا؟"


def test_aliases_are_search_only_and_grouped_by_original_word():
    original = "وَبِالْمَكْتَبِ"
    groups = retrieval_token_groups(original)
    assert len(groups) == 1
    assert "مكتب" in groups[0]
    assert original == "وَبِالْمَكْتَبِ"
    assert normalize_arabic(original) == "وبالمكتب"
    assert NORMALIZER_VERSION == "ar-v1"
    assert retrieval_tokens("") == ()
    with pytest.raises(TypeError):
        retrieval_tokens(None)
