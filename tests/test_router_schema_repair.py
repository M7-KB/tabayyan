"""Router schema resilience and strict evidence gates, using synthetic records."""

import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from api.diagnostics import Summary, summary
from api.main import create_app
from api.router import QuranRef
from api.settings import Settings
from tests.test_composer import claim, engine, proposal
from tests.test_one_pass import route_proposal, service
from tests.test_router_candidates import quran_record


def test_oversize_default_and_legacy_claim_join_return_within_timeout():
    # A subprocess deadline makes the original infinite loop fail this test
    # without leaving a spinning thread behind in the test runner.
    script = (
        f"sys.path[:] = {sys.path!r}\n"
        + """
from api.router import _repair_proposal
from api.check import CheckRequest
from tests.test_one_pass import service
for length in (100, 12001, 12049):
    repaired = _repair_proposal("x" * length, {})
    assert len(repaired.claims[0].text_ar) <= 12000
    assert len(repaired.premise) <= 12000
    assert repaired.claims[0].span.end <= 12000
request = CheckRequest(claims=[dict(id=str(i), text_ar="x" * 240) for i in range(50)])
checker, _, _ = service({})
result = checker.check(request)
assert result["cards"] and result["cards"][0]["state"] == "CANNOT_CONFIRM"
"""
    )
    result = subprocess.run(
        [sys.executable, "-c", "import sys\n" + script], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "mutation",
    [
        "topic",
        "ref",
        "claims",
        "level",
        "confidence",
        "kind",
        "premise",
        "missing",
        "extra",
        "object",
    ],
)
def test_ten_schema_shapes_never_produce_http_failure(mutation):
    text = "Synthetic question about fruit?"
    value = route_proposal(text)
    updates = {
        "topic": {"search_queries": ["ethics", "private secret topic"]},
        "ref": {"proposed_quran_refs": [{"surah": 0, "ayah": 40}]},
        "claims": {"claims": [{"source_text": "invented"}]},
        "level": {"level": "invalid"},
        "confidence": {"level_confidence": float("nan")},
        "kind": {"input_kind": 42},
        "premise": {"premise": None},
        "extra": {"secret field name": "secret value"},
    }
    value.update(updates.get(mutation, {}))
    if mutation == "missing":
        del value["claims"]
    if mutation == "object":
        value = []
    checker, _, _ = service(value)
    app = create_app(Settings(openai_api_key="inert", openai_schema_warmup=False))
    app.state.checker = checker
    with TestClient(app) as client:
        response = client.post("/api/v1/check", json={"original_text": text})
    assert response.status_code == 200
    assert response.json()["cards"][0]["state"] == "CANNOT_CONFIRM"


def test_optional_bad_items_keep_valid_refs_and_topics_without_logging_values():
    text = "Synthetic question about fruit?"
    value = route_proposal(
        text,
        search_queries=["ethics", "secret topic"],
        proposed_quran_refs=[
            {"surah": 33, "ayah": 40},
            {"surah": 0, "ayah": 1},
            {"surah": 33, "ayah": 999},
        ],
    )
    value["claims"][0]["origin"] = "question_subject"
    metrics = Summary()
    token = summary.set(metrics)
    try:
        checker, _, _ = service(value)
        route = checker.router.route(text)
    finally:
        summary.reset(token)
    assert route.queries == ("ethics",)
    assert route.quran_refs == (QuranRef(surah=33, ayah=40),)
    assert set(metrics.codes) == {"router_field:search_queries", "router_field:proposed_quran_refs"}
    assert text not in json.dumps(metrics.codes)
    assert "secret" not in json.dumps(metrics.codes)


@pytest.mark.parametrize(
    "origin,confidence,alignment,state",
    [
        ("question_subject", 0.9, "CONFIRMS", "SUPPORTED"),
        ("presupposition", 0.9, "CONFIRMS", "SUPPORTED"),
        ("stated", 0.9, "CONFIRMS", "CANNOT_CONFIRM"),
        ("question_subject", 0.1, "CONFIRMS", "CANNOT_CONFIRM"),
        ("question_subject", 0.9, None, "CANNOT_CONFIRM"),
    ],
)
def test_nomination_exempts_only_question_overlap(origin, confidence, alignment, state):
    text = "Synthetic question about fruit?"
    record = quran_record()
    composer = engine(
        records=[record],
        value=proposal(
            state="SUPPORTED",
            corpus_ids=["quran:33:40"],
            alignment_proposal=alignment,
            alignment_confidence=confidence,
        ),
    )
    result = composer.compose(
        claim(text, origin=origin),
        original=text,
        lang="en",
        input_kind="question",
        no_checkable_claim=False,
        propose_state=True,
        quran_refs=[QuranRef(surah=33, ayah=40)],
    )
    assert result["state"] == state
    if state == "SUPPORTED":
        assert result["evidence"][0]["quote_ar"] == record["aya_text_unicode"]
        assert result["evidence"][0]["retrieval_score"] == 0
