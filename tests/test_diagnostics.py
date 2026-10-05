"""Failure metadata never contains submitted text or provider diagnostics."""

import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from api.diagnostics import request_id
from api.main import create_app
from api.provider import OpenAIStructuredModel, ProviderUnavailable
from api.settings import Settings
from tests.test_extract import proposal, service


@pytest.mark.parametrize(
    "status,category",
    [
        (400, "http_error"),
        (401, "authentication_error"),
        (429, "rate_limited"),
        (500, "provider_server_error"),
    ],
)
def test_fixed_provider_failures_no_payload(caplog, status, category):
    caplog.set_level(logging.INFO)
    model = OpenAIStructuredModel(
        api_key="SECRET_SENTINEL",
        model="MODEL_SENTINEL",
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="BODY_SENTINEL")),
    )
    with pytest.raises(ProviderUnavailable):
        model.complete_json(instructions="fixed", data={"text": "INPUT_SENTINEL"}, schema={})
    assert f"outcome={category}" in caplog.text
    for forbidden in ("SECRET_SENTINEL", "MODEL_SENTINEL", "BODY_SENTINEL", "INPUT_SENTINEL"):
        assert forbidden not in caplog.text


def test_invalid_span_has_fixed_diagnostic_and_correlated_response(caplog):
    caplog.set_level(logging.INFO)
    value = proposal("INPUT_SENTINEL", lang="en")
    value["claims"][0]["span"]["end"] += 1
    app = create_app(Settings(openai_api_key="inert", openai_model_extract="inert"))
    with TestClient(app) as client:
        app.state.extractor = service(value)
        response = client.post("/api/v1/extract", json={"text": "INPUT_SENTINEL"})
    assert response.status_code == 503
    correlation = response.headers["X-Request-ID"]
    assert len(correlation) == 32
    assert (
        f"request_id={correlation} stage=extraction_validation outcome=invalid_span" in caplog.text
    )
    assert f"request_id={correlation} stage=extract outcome=http_failure" in caplog.text
    assert "INPUT_SENTINEL" not in caplog.text
    assert request_id.get() == "none"


def test_timeout_category_without_exception_text(caplog):
    caplog.set_level(logging.INFO)

    def timeout(request):
        raise httpx.ReadTimeout("PRIVATE_PROVIDER_SENTINEL", request=request)

    model = OpenAIStructuredModel(
        api_key="inert", model="inert", transport=httpx.MockTransport(timeout)
    )
    with pytest.raises(ProviderUnavailable):
        model.complete_json(
            instructions="fixed", data={"text": "PRIVATE_INPUT_SENTINEL"}, schema={}
        )
    assert "outcome=provider_timeout" in caplog.text
    assert "PRIVATE_PROVIDER_SENTINEL" not in caplog.text
    assert "PRIVATE_INPUT_SENTINEL" not in caplog.text


def test_request_ids_are_server_generated_and_reset(caplog):
    caplog.set_level(logging.INFO)
    app = create_app(Settings(openai_api_key="inert", openai_model_extract="inert"))
    with TestClient(app) as client:
        app.state.extractor = service(proposal("fixture", lang="en"))
        first = client.post(
            "/api/v1/extract",
            json={"text": "fixture"},
            headers={"X-Request-ID": "PRIVATE_SENTINEL"},
        )
        second = client.post("/api/v1/extract", json={"text": "fixture"})
        assert first.status_code == second.status_code == 200
        assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]
        assert "X-Request-ID" not in client.get("/health").headers
    assert "PRIVATE_SENTINEL" not in caplog.text
    assert request_id.get() == "none"


def test_check_correlation_reaches_parallel_composition_and_router(caplog):
    from tests.test_composer import TEXT, proposal
    from tests.test_one_pass import service as one_pass_service

    caplog.set_level(logging.INFO)
    checker, _, _ = one_pass_service()
    correlations = []

    class Model:
        def complete_json(self, **kwargs):
            correlations.append(request_id.get())
            return proposal(state="SUPPORTED")

    checker.composer.model = Model()
    app = create_app(Settings(openai_api_key="inert", openai_schema_warmup=False))
    app.state.checker = checker
    with TestClient(app) as client:
        response = client.post("/api/v1/check", json={"original_text": TEXT})
    assert response.status_code == 200
    correlation = response.headers["X-Request-ID"]
    assert correlations == [correlation]
    assert f"request_id={correlation} stage=router_validation outcome=validated" in caplog.text
    assert f"request_id={correlation} stage=check outcome=completed" in caplog.text
    assert TEXT not in caplog.text
