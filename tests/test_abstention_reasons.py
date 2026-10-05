"""Abstention reason precedence never authorizes additional output."""

import pytest

from tests.test_composer import claim, compose, engine


@pytest.mark.parametrize("status", ["unavailable", "low_confidence"])
def test_known_no_claim_takes_precedence_over_classifier_failure(status):
    e = engine()
    card = compose(
        e, claim(level="D", status=status, origin="term_lookup"), kind="question", no_claim=True
    )
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "NO_CHECKABLE_CLAIM"
    assert not card["evidence"]
    assert not e.model.calls


@pytest.mark.parametrize("status", ["unavailable", "low_confidence"])
def test_absent_candidates_takes_precedence_over_classifier_failure(status):
    e = engine()
    card = compose(e, claim(text="unrelated synthetic topic", level="D", status=status))
    assert card["state"] == "CANNOT_CONFIRM"
    assert card["abstained_reason"] == "NO_MATCHING_EVIDENCE"
    assert not e.model.calls


@pytest.mark.parametrize("status", ["model_validated", "rule_forced"])
def test_personal_case_keeps_precedence_over_no_claim_and_no_evidence(status):
    e = engine()
    card = compose(
        e,
        claim(text="unrelated synthetic topic", level="D", status=status),
        kind="question",
        no_claim=True,
    )
    assert card["abstained_reason"] == "LEVEL_D_PERSONAL_CASE"
    assert card["referral"]
    assert not e.model.calls


def test_unknown_classifier_with_candidates_still_abstains_low_confidence():
    e = engine()
    card = compose(e, claim(level="D", status="unavailable"))
    assert card["abstained_reason"] == "LOW_CONFIDENCE"
    assert not e.model.calls
