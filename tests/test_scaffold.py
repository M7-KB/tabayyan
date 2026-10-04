"""Scaffold tests use temporary config and an inert key; no provider calls."""

import json

import pytest
import yaml
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
        "policy_version: test-p\napproved_by: pending\nalignment: {word_budget_ceiling: 4}\n",
        encoding="utf-8",
    )
    tuning.write_text(
        "tuning_version: test-t\ncard_confidence_min: 0.5\n"
        "level_confidence_min: 0.5\nalignment_confidence_min: 0.6\n"
        'retrieval_score_floor: 8.0\nword_budget_table: {"4": 1, "10": 2, else: 3}\n'
        "trigger_b_min_window_tokens: 3\n",
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
        "corpus_status": "not_configured",
        "corpus_error": None,
        "pending_review_items": 0,
        "allow_pending_review": False,
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


@pytest.mark.parametrize("key", [None, "", "   "])
def test_health_only_starts_without_key_or_policy(settings, key, tmp_path):
    settings.health_only = True
    settings.openai_api_key = None if key is None else Settings(openai_api_key=key).openai_api_key
    settings.content_policy_path = tmp_path / "missing-policy.yaml"
    settings.tuning_path = tmp_path / "missing-tuning.yaml"
    with TestClient(create_app(settings)) as client:
        result = client.get("/health")
        assert result.status_code == 200
        assert result.json()["status"] == "degraded"
        assert result.json()["corpus_items"] == 0
        assert result.json()["policy_approved_by"] == "pending"
        assert result.json()["policy_version"] is None
        assert result.json()["tuning_version"] is None
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == 404
        assert client.post("/verify").status_code == 404


@pytest.mark.parametrize("band", ["4", "10", "else"])
def test_ceiling_violation_is_startup_failure(settings, band):
    data = yaml.safe_load(settings.tuning_path.read_text("utf-8"))
    bands = ["4", "10", "else"]
    data["word_budget_table"] = {
        key: (5 if bands.index(key) >= bands.index(band) else 1) for key in bands
    }
    # Retain an ordered table to isolate each policy ceiling boundary.
    settings.tuning_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(
        RuntimeError, match=rf"word_budget_table\.{band} exceeds word_budget_ceiling"
    ):
        with TestClient(create_app(settings)):
            pass


def test_ceiling_equality_is_accepted(settings):
    data = yaml.safe_load(settings.tuning_path.read_text("utf-8"))
    data["word_budget_table"]["else"] = 4
    settings.tuning_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200


@pytest.mark.parametrize(
    "table",
    [
        {"4": 0, "10": 2, "else": 3},
        {"4": -1, "10": 2, "else": 3},
        {"4": 1.5, "10": 2, "else": 3},
        {"4": True, "10": 2, "else": 3},
        {"4": 3, "10": 2, "else": 3},
        {"4": 1, "10": 3, "else": 2},
        {"4": 1},
        {},
        {"bad": 1, "else": 3},
        {"0": 1, "else": 3},
        {"04": 1, "4": 1, "else": 3},
    ],
)
def test_invalid_budget_table_fails_closed(settings, table):
    data = yaml.safe_load(settings.tuning_path.read_text("utf-8"))
    data["word_budget_table"] = table
    settings.tuning_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing or invalid") as caught:
        with TestClient(create_app(settings)):
            pass
    assert str(settings.tuning_path) in str(caught.value)
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize(
    "field,value",
    [
        ("alignment_confidence_min", 0),
        ("alignment_confidence_min", 1.1),
        ("alignment_confidence_min", float("nan")),
        ("trigger_b_min_window_tokens", 0),
        ("trigger_b_min_window_tokens", 2.5),
        ("near_miss_max", 0.25),
    ],
)
def test_invalid_tuning_field_identified(settings, field, value):
    data = yaml.safe_load(settings.tuning_path.read_text("utf-8"))
    data[field] = value
    settings.tuning_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(RuntimeError, match=field):
        with TestClient(create_app(settings)):
            pass


@pytest.mark.parametrize("invalid", ["", "[]", "{bad", "alignment: {word_budget_ceiling: .nan}"])
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
