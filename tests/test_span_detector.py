"""Literal probe-v2 regressions plus synthetic Unicode/config/failure tests.

The probe literals reproduce RESEARCH/tabayyan/WORD_BUDGET_PROBE.py, not licensed
corpus records. They are detector inputs only and must never authorize evidence.
"""

import copy
import unicodedata
from unittest.mock import patch

import pytest
import yaml

from api.span_detector import (
    DetectorConfig,
    Record,
    SpanDetector,
    comparison_key,
    word_distance,
    words,
)

POLICY = {
    "policy_version": "p1",
    "approved_by": "pending",
    "alignment": {"word_budget_ceiling": 4},
    "scripture_span_markers": {
        "ornate_brackets": ["﴾", "﴿"],
        "quote_marks": ["«", "»", '"', "'", "“", "”"],
        "attribution_allah": [
            "قال الله تعالى",
            "قال تعالى",
            "قال الله",
            "يقول الله",
            "في قوله تعالى",
            "قال عز وجل",
        ],
        "attribution_prophet": [
            "قال رسول الله",
            "قال النبي",
            "عن النبي",
            "قال ﷺ",
            "في الحديث",
            "روى البخاري",
            "روى مسلم",
        ],
    },
}
TUNING = {
    "tuning_version": "t1",
    "card_confidence_min": 0.5,
    "alignment_confidence_min": 0.6,
    "retrieval_score_floor": 8.0,
    "retrieval_overlap_floor": 0.25,
    "retrieval_overlap_min_terms": 1,
    "word_budget_table": {"4": 1, "10": 2, "else": 3},
    "trigger_b_min_window_tokens": 3,
}

PROBE_MISQUOTES = [
    ("quran:108:3", "إِنَّ شَانِئَكَ هُوَ الْأَبْتَرُ", "ان شانئك هو الاكبر"),
    ("quran:17:32:clause", "وَلَا تَقْرَبُوا الزِّنَا", "ولا تقربوا الربا"),
    ("quran:2:286:clause", "لَا يُكَلِّفُ اللَّهُ نَفْسًا إِلَّا وُسْعَهَا", "لا يكلف الله نفسا الا طاقتها"),
    ("hadith:probe:darar", "لَا ضَرَرَ وَلَا ضِرَارَ", "لا ضرر ولا اضرار"),
    ("quran:2:152:clause", "فَاذْكُرُونِي أَذْكُرْكُمْ", "فاذكروني اذكركم جميعا"),
    ("quran:94:5", "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا", "فان بعد العسر يسرا"),
    (
        "quran:2:255:opening",
        "اللَّهُ لَا إِلَهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ لَهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الْأَرْضِ",
        "الله لا اله الا هو الحي القيوم لا تاخذه سنة ولا نوم له ما في السماوات وما في الارضين",
    ),
]
PROBE_TWINS = [
    ("2:164/2:242", "إِنَّ فِي ذَلِكَ لَآيَاتٍ لِقَوْمٍ يَعْقِلُونَ", "إِنَّ فِي ذَلِكَ لَآيَاتٍ لِقَوْمٍ يَتَفَكَّرُونَ"),
    ("6:99/6:95", "لِقَوْمٍ يُؤْمِنُونَ", "لِقَوْمٍ يَعْلَمُونَ"),
    ("10:5/30:8", "كَذَلِكَ يُفَصِّلُ الْآيَاتِ لِقَوْمٍ يَعْلَمُونَ", "كَذَلِكَ يُفَصِّلُ الْآيَاتِ لِقَوْمٍ يَتَفَكَّرُونَ"),
    ("7:69/7:74", "فَاذْكُرُوا آلَاءَ اللَّهِ لَعَلَّكُمْ تُفْلِحُونَ", "فَاذْكُرُوا آلَاءَ اللَّهِ لَعَلَّكُمْ تَذَكَّرُونَ"),
]


def detector(records, policy=None, tuning=None):
    return SpanDetector(records, DetectorConfig.from_mappings(policy or POLICY, tuning or TUNING))


@pytest.mark.parametrize("corpus_id,source,user", PROBE_MISQUOTES)
def test_literal_probe_one_word_misquotes(corpus_id, source, user):
    domain = corpus_id.split(":")[0]
    engine = detector([Record(corpus_id, domain, source)])
    match = engine.classify(user)
    assert word_distance(words(source), words(user)) == 1
    assert match.classification == "NEAR_MISS"
    # Marked path must cover the two-token insertion; the B floor stays intact.
    result = engine.detect('"' + user + '"')
    assert result.span_detector_status == "ran"
    assert any(f.match.classification == "NEAR_MISS" for f in result.findings)
    effects = result.effects("A", "تنبيه تجريبي")
    assert effects["force_quran_contradicts"] == (domain == "quran")
    assert (effects["misquote_notice"] is not None) == (domain == "hadith")


@pytest.mark.parametrize("label,left,right", PROBE_TWINS)
def test_literal_probe_twins_veto_before_near_match(label, left, right):
    records = [Record(label + ":left", "quran", left), Record(label + ":right", "quran", right)]
    assert word_distance(words(left), words(right)) == 1
    for ordered in (records, records[::-1]):
        engine = detector(ordered)
        for value in (left, right):
            for trigger in ("A", "B"):
                assert engine.classify(value, trigger).classification == "VERBATIM"
            for text in (value, '"' + value + '"'):
                result = engine.detect(text)
                assert result.findings
                assert all(f.match.classification == "VERBATIM" for f in result.findings)
                assert not result.effects("A", "تنبيه")["force_quran_contradicts"]


def test_both_triggers_whole_index_and_hadith_notice():
    corpus_id, source, user = PROBE_MISQUOTES[3]
    records = [
        Record("unrelated", "quran", "مكتب تجريبي جديد"),
        Record(corpus_id, "hadith", source),
    ]
    engine = detector(records)
    for text in (user, "قال رسول الله: " + user):
        result = engine.detect(text)
        assert any(f.match.record.corpus_id == corpus_id for f in result.findings)
        effects = result.effects("A", "تنبيه تجريبي")
        assert not effects["force_quran_contradicts"]
        assert effects["misquote_notice"]["quote_ar"] == source


def test_level_d_notice_without_alignment_force():
    corpus_id, source, user = PROBE_MISQUOTES[0]
    result = detector([Record(corpus_id, "quran", source)]).detect('"' + user + '"')
    effects = result.effects("D", "تنبيه تجريبي")
    assert not effects["force_quran_contradicts"]
    assert effects["misquote_notice"]["quote_ar"] == source
    assert effects["misquote_notice"]["quote_ar"] != user


def test_paraphrase_outside_budget_is_unrelated():
    source = "مكتب تجريبي جديد واسع"
    engine = detector([Record("fixture", "quran", source)])
    user = "غرفة أخرى للعمل ذات مساحة كبيرة"
    assert engine.classify(user).classification == "UNRELATED"
    assert engine.detect(user).findings == ()


def test_trigger_b_floor_only_and_tuning_is_effective():
    records = [Record("fixture", "quran", "مكتب جديد")]
    engine = detector(records)
    assert engine.classify("مكتب قديم", "A").classification == "NEAR_MISS"
    assert engine.classify("مكتب قديم", "B").classification == "UNRELATED"
    assert engine.detect("مكتب قديم").findings == ()
    tuning = copy.deepcopy(TUNING)
    tuning["trigger_b_min_window_tokens"] = 2
    assert detector(records, tuning=tuning).detect("مكتب قديم").findings


def test_budget_symmetric_max_and_configurable():
    engine = detector([Record("fixture", "quran", "واحد اثنان ثلاثة أربعة")])
    match = engine.classify("واحد اثنان ثلاثة أربعة خمسة ستة")
    assert match.token_count == 6
    assert match.distance == 2
    assert match.classification == "NEAR_MISS"
    tuning = copy.deepcopy(TUNING)
    tuning["word_budget_table"] = {"4": 1, "10": 1, "else": 1}
    assert (
        detector([match.record], tuning=tuning)
        .classify("واحد اثنان ثلاثة أربعة خمسة ستة")
        .classification
        == "UNRELATED"
    )


@pytest.mark.parametrize("mark", [chr(c) for c in range(0x08CA, 0x08D3)])
def test_nine_annotation_marks_cannot_bypass_either_trigger_or_veto(mark):
    engine = detector([Record("fixture", "quran", "مكتب جديد واسع")])
    assert comparison_key("م" + mark + "كتب") == "مكتب"
    for value, expected in (("مكتب جديد واسع", "VERBATIM"), ("مكتب قديم واسع", "NEAR_MISS")):
        altered = value.replace("م", "م" + mark)
        for trigger in ("A", "B"):
            assert engine.classify(altered, trigger).classification == expected


def test_all_cf_characters_are_removed():
    formats = [chr(c) for c in range(0x110000) if unicodedata.category(chr(c)) == "Cf"]
    engine = detector([Record("fixture", "quran", "مكتب جديد واسع")])
    for char in formats:
        assert comparison_key("م" + char + "كتب") == "مكتب"
        assert engine.classify("م" + char + "كتب جديد واسع").classification == "VERBATIM"
        assert engine.classify("م" + char + "كتب قديم واسع", "B").classification == "NEAR_MISS"


@pytest.mark.parametrize(
    "source,user", [("مكتب جديد واسع", "ﻣﻜﺘﺐ جديد واسع"), ("الله جديد واسع", "ﷲ جديد واسع")]
)
def test_presentation_forms(source, user):
    engine = detector([Record("fixture", "quran", source)])
    assert engine.classify(user).classification == "VERBATIM"
    assert engine.classify(user.replace("جديد", "قديم"), "B").classification == "NEAR_MISS"


@pytest.mark.parametrize("digits", ["١٢٣", "۱۲۳"])
def test_arabic_indic_digits(digits):
    engine = detector([Record("fixture", "quran", "مكتب 123 واسع")])
    assert engine.classify("مكتب " + digits + " واسع").classification == "VERBATIM"
    assert engine.classify("مكتب " + digits + " قديم", "B").classification == "NEAR_MISS"


@pytest.mark.parametrize(
    "opening,closing", [("﴿", "﴾"), ("«", "»"), ('"', '"'), ("'", "'"), ("“", "”")]
)
def test_configured_marker_pairs_and_offsets(opening, closing):
    engine = detector([Record("fixture", "quran", "مكتب جديد واسع")])
    user = "مقدمة " + opening + "مكتب قديم واسع" + closing
    result = engine.detect(user)
    finding = result.findings[0]
    assert finding.marker is not None
    assert user[finding.start : finding.end] == "مكتب قديم واسع"
    assert finding.card_span()["classification"] == "NEAR_MISS"


@pytest.mark.parametrize(
    "formula",
    POLICY["scripture_span_markers"]["attribution_allah"]
    + POLICY["scripture_span_markers"]["attribution_prophet"],
)
def test_every_configured_attribution_formula(formula):
    engine = detector([Record("fixture", "quran", "مكتب جديد واسع")])
    result = engine.detect(formula + ": مكتب قديم واسع")
    assert any(f.marker == "attribution_formula" for f in result.findings)


def test_custom_markers_are_used_and_no_model_interface_exists():
    policy = copy.deepcopy(POLICY)
    policy["scripture_span_markers"]["attribution_allah"] = ["custom attribution"]
    engine = detector([Record("fixture", "quran", "مكتب جديد")], policy=policy)
    assert any(
        f.marker == "attribution_formula"
        for f in engine.detect("custom attribution: مكتب قديم").findings
    )
    assert engine.detect("قال تعالى: مكتب قديم").findings == ()


def test_files_and_rejected_policy_tuning(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    tuning_path = tmp_path / "tuning.yaml"
    policy_path.write_text(yaml.safe_dump(POLICY, allow_unicode=True), "utf-8")
    tuning_path.write_text(yaml.safe_dump(TUNING), "utf-8")
    config = DetectorConfig.from_files(policy_path, tuning_path)
    assert [config.budget(n) for n in (4, 5, 10, 11)] == [1, 2, 2, 3]
    tuning = copy.deepcopy(TUNING)
    tuning["word_budget_table"]["else"] = 5
    with pytest.raises(ValueError):
        DetectorConfig.from_mappings(POLICY, tuning)


def test_status_failures_do_not_look_like_a_clean_run():
    engine = detector([Record("fixture", "quran", "مكتب جديد واسع")])
    assert engine.detect("نص مختلف تماما").span_detector_status == "ran"
    assert engine.detect("input", ["absent"]).span_detector_status == "corpus_id_unresolved"
    for failure, expected in ((RuntimeError("private text"), "error"), (TimeoutError(), "timeout")):
        with patch.object(engine, "_scan", side_effect=failure):
            result = engine.detect("private text")
            assert result.span_detector_status == expected
            assert not result.findings
            assert "private text" not in repr(result)
    for records in (None, [], [Record("faq", "faq", "مكتب جديد واسع")]):
        assert detector(records).detect("input").span_detector_status == "index_unavailable"


def test_adjacent_correct_quote_does_not_hide_separate_misquote():
    records = [Record("a", "quran", "مكتب جديد واسع"), Record("b", "quran", "غرفة صغيرة هادئة")]
    result = detector(records).detect("مكتب جديد واسع ثم غرفة كبيرة هادئة")
    assert any(f.match.classification == "VERBATIM" for f in result.findings)
    assert any(
        f.match.classification == "NEAR_MISS" and f.match.record.corpus_id == "b"
        for f in result.findings
    )


def test_no_source_mutation_or_quote_authorization():
    source = "مَكْتَبٌ جديد واسع"
    record = Record("fixture", "quran", source)
    result = detector([record]).detect('"مكتب قديم واسع"')
    assert result.effects("D", "تنبيه")["misquote_notice"]["quote_ar"] == source
    assert record.text_ar == source
    assert comparison_key(source) != source


def test_short_exact_record_does_not_hide_longer_misquote():
    records = [
        Record("short", "hadith", "مكتب جديد واسع"),
        Record("long", "quran", "مكتب جديد واسع مشرق"),
    ]
    result = detector(records).detect("مكتب جديد واسع مظلم")
    assert any(
        f.match.classification == "NEAR_MISS" and f.match.record.corpus_id == "long"
        for f in result.findings
    )


def test_attribution_colon_without_whitespace_preserves_body_offsets():
    engine = detector([Record("fixture", "quran", "مكتب جديد")])
    user = "قال تعالى:مكتب قديم"
    result = engine.detect(user)
    assert result.span_detector_status == "ran"
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert user[finding.start : finding.end] == "مكتب قديم"
    assert finding.match.classification == "NEAR_MISS"


def test_unmarked_offsets_around_punctuation_and_unicode_insertions():
    engine = detector([Record("fixture", "quran", "مكتب جديد واسع")])
    user = "تمهيد،م\u200dكتب قديم واسع."
    result = engine.detect(user)
    finding = next(f for f in result.findings if f.match.classification == "NEAR_MISS")
    assert user[finding.start : finding.end] == "م\u200dكتب قديم واسع"


@pytest.mark.parametrize("domain", ["quran", "hadith"])
@pytest.mark.parametrize("marker", ['"{}"', "قال تعالى: {}", "قال النبي: {}"])
@pytest.mark.parametrize("placement", ["before", "after", "both"])
def test_marked_commentary_cannot_hide_embedded_near_miss(domain, marker, placement):
    engine = detector([Record("synthetic", domain, "alpha beta gamma")])
    padding = "followed by unrelated explanation with many extra words and further commentary"
    body = "alpha wrong gamma"
    if placement in {"before", "both"}:
        body = padding + " " + body
    if placement in {"after", "both"}:
        body += " " + padding
    text = marker.format(body)
    result = engine.detect(text)
    assert result.span_detector_status == "ran"
    assert any(f.marker and f.match.classification == "UNRELATED" for f in result.findings)
    embedded = next(f for f in result.findings if f.match.classification == "NEAR_MISS")
    assert text[embedded.start : embedded.end] == "alpha wrong gamma"
    assert embedded.marker is None
    effects = result.effects("A", "Synthetic notice")
    assert effects["force_quran_contradicts"] == (domain == "quran")
    assert (effects["misquote_notice"] is not None) == (domain == "hadith")
    assert not result.effects("D", "Synthetic notice")["force_quran_contradicts"]


@pytest.mark.parametrize("marker", ['"{}"', "قال تعالى: {}"])
def test_padded_correct_quote_retains_verbatim_veto(marker):
    records = [
        Record("left", "quran", "alpha beta gamma"),
        Record("twin", "quran", "alpha delta gamma"),
    ]
    text = marker.format("alpha beta gamma followed by unrelated explanation with many extra words")
    result = detector(records).detect(text)
    assert any(f.match.classification == "VERBATIM" for f in result.findings)
    assert not any(f.match.classification == "NEAR_MISS" for f in result.findings)
    assert not result.effects("A", "Synthetic notice")["force_quran_contradicts"]
