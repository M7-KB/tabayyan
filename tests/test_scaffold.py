"""Scaffold tests use temporary config and an inert key; no provider calls."""

import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import create_app
from api.settings import Settings


@pytest.fixture
def settings(tmp_path):
    policy = tmp_path / "policy.yaml"
    tuning = tmp_path / "tuning.yaml"
    policy.write_text(
        "policy_version: test-p\napproved_by: pending\nalignment: {near_miss_max_ceiling: 0.35}\n",
        encoding="utf-8",
    )
    tuning.write_text(
        "tuning_version: test-t\nnear_miss_max: 0.25\nunmarked_near_miss_max: 0.12\n",
        encoding="utf-8",
    )
    return Settings(
        openai_api_key="inert-test-value",
        content_policy_path=policy,
        tuning_path=tuning,
        cors_origins=["https://web.example"],
        build_sha="test-build",
    )


def test_health_reports_config_and_unavailable_artifacts(settings):
    with TestClient(create_app(settings)) as client:
        result = client.get("/health")
    assert result.status_code == 200
    assert result.json() == {
        "status": "degraded",
        "corpus_version": None,
        "corpus_items": 0,
        "policy_version": "test-p",
        "policy_approved_by": "pending",
        "tuning_version": "test-t",
        "card_schema_version": None,
        "build": "test-build",
    }


@pytest.mark.parametrize("key", [None, "", "   "])
def test_missing_key_fails_startup_without_disclosing_config(settings, key):
    settings.openai_api_key = None if key is None else Settings(openai_api_key=key).openai_api_key
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        with TestClient(create_app(settings)):
            pass


@pytest.mark.parametrize("field", ["near_miss_max", "unmarked_near_miss_max"])
def test_ceiling_violation_is_startup_failure(settings, field):
    settings.tuning_path.write_text(
        "tuning_version: test-t\nnear_miss_max: 0.25\nunmarked_near_miss_max: 0.12\n".replace(
            f"{field}: " + ("0.25" if field == "near_miss_max" else "0.12"), f"{field}: 0.36"
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match=f"{field} exceeds near_miss_max_ceiling"):
        with TestClient(create_app(settings)):
            pass


@pytest.mark.parametrize("invalid", ["", "[]", "{bad", "alignment: {near_miss_max_ceiling: .nan}"])
def test_bad_policy_fails_closed(settings, invalid):
    settings.content_policy_path.write_text(invalid, encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing or invalid"):
        with TestClient(create_app(settings)):
            pass


def test_missing_policy_fails_closed(settings):
    settings.content_policy_path.unlink()
    with pytest.raises(RuntimeError, match="missing or invalid"):
        with TestClient(create_app(settings)):
            pass


def test_errors_do_not_echo_input_or_exception(settings):
    app = create_app(settings)

    @app.post("/test-validation")
    async def validate(count: int):
        return count

    @app.get("/test-http")
    async def http_error():
        raise HTTPException(403, detail="private-exception")

    @app.get("/test-crash")
    async def crash():
        raise RuntimeError("private-exception")

    with TestClient(app, raise_server_exceptions=False) as client:
        for result, status, code in [
            (client.post("/test-validation?count=private-input"), 422, "INVALID_REQUEST"),
            (client.get("/test-http"), 403, "HTTP_ERROR"),
            (client.get("/test-crash"), 500, "INTERNAL_ERROR"),
            (client.post("/health"), 405, "METHOD_NOT_ALLOWED"),
            (client.get("/missing-private-path"), 404, "NOT_FOUND"),
        ]:
            assert result.status_code == status
            assert result.json()["error"]["code"] == code
            assert set(result.json()["error"]) == {"code", "message_ar", "message_en"}
            assert "private" not in result.text


def test_cors_allows_only_configured_origin(settings):
    with TestClient(create_app(settings)) as client:
        allowed = client.options(
            "/health",
            headers={
                "Origin": "https://web.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.options(
            "/health",
            headers={
                "Origin": "https://other.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert allowed.headers["access-control-allow-origin"] == "https://web.example"
    assert "access-control-allow-origin" not in denied.headers


def test_settings_read_env_without_secret_repr(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    monkeypatch.setenv("OPENAI_MODEL_EXTRACT", "configured-extractor")
    monkeypatch.setenv("CORS_ORIGINS", json.dumps(["https://web.example"]))
    settings = Settings()
    assert settings.openai_model_extract == "configured-extractor"
    assert settings.cors_origins == ["https://web.example"]
    assert "private-test-key" not in repr(settings)


def test_wildcard_cors_rejected():
    with pytest.raises(ValidationError, match="explicit origins"):
        Settings(cors_origins=["*"])
