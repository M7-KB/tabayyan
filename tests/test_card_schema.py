"""Structural card checks use synthetic fixtures, never corpus approval."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
SCHEMA = json.loads((CONTRACTS / "card.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
NON_RAN = ("error", "timeout", "index_unavailable", "corpus_id_unresolved", "skipped")


def card(name):
    return json.loads((CONTRACTS / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))


def test_schema_is_draft_2020_12():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize(
    "path", sorted((CONTRACTS / "fixtures").glob("*.json")), ids=lambda p: p.stem
)
def test_fixture_acceptance(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    assert VALIDATOR.is_valid(value) == (not path.name.startswith("invalid-"))


@pytest.mark.parametrize("status", NON_RAN)
@pytest.mark.parametrize("name", ("supported-confirms", "supported-contradicts", "disputed"))
def test_non_ran_detector_rejects_non_abstaining_cards(status, name):
    value = card(name)
    value["claim"]["span_detector_status"] = status
    assert not VALIDATOR.is_valid(value)


@pytest.mark.parametrize("status", NON_RAN)
def test_non_ran_detector_requires_reason_and_failed_gate(status):
    value = card("cannot-confirm")
    value["claim"]["span_detector_status"] = status
    assert not VALIDATOR.is_valid(value)
    value["abstained_reason"] = "ALIGNMENT_UNDETERMINED"
    assert not VALIDATOR.is_valid(value)
    value["gate_report"]["span_detector"] = "fail"
    VALIDATOR.validate(value)
    value["abstained_reason"] = "LEVEL_D_PERSONAL_CASE"
    assert not VALIDATOR.is_valid(value)


@pytest.mark.parametrize("name", ("supported-confirms", "cannot-confirm"))
@pytest.mark.parametrize("classification", (None, "VERBATIM", "UNRELATED"))
def test_notice_requires_near_miss(name, classification):
    value = card(name)
    if classification is None:
        value["claim"]["scripture_spans"] = []
    else:
        for span in value["claim"]["scripture_spans"]:
            span["classification"] = classification
    assert not VALIDATOR.is_valid(value)
    value["misquote_notice"] = None
    VALIDATOR.validate(value)


@pytest.mark.parametrize("level", ("A", "B", "C", "D"))
@pytest.mark.parametrize("name", ("supported-confirms", "disputed", "cannot-confirm"))
def test_level_state_mapping(level, name):
    value = card(name)
    value["claim"]["level"] = level
    allowed = {
        "A": {"SUPPORTED", "CANNOT_CONFIRM"},
        "B": {"SUPPORTED", "DISPUTED", "CANNOT_CONFIRM"},
        "C": {"DISPUTED", "CANNOT_CONFIRM"},
        "D": {"CANNOT_CONFIRM"},
    }
    assert VALIDATOR.is_valid(value) == (value["state"] in allowed[level])
