"""The HTTP and orchestration timers use the same validated setting."""

from time import monotonic

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.deadline import request_deadline
from api.main import create_app
from api.settings import Settings


@pytest.mark.parametrize("value", [0, -1, "nan", "inf", "bad"])
def test_invalid_server_deadline_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(check_deadline_seconds=value)


def test_server_deadline_environment_override(monkeypatch):
    monkeypatch.setenv("CHECK_DEADLINE_SECONDS", "72.5")
    assert Settings().check_deadline_seconds == 72.5


@pytest.mark.parametrize("seconds", [60, 72.5])
def test_http_and_service_share_configured_deadline(seconds, monkeypatch):
    import asyncio

    configured = []
    actual_wait = asyncio.wait_for

    async def observe_wait(awaitable, *, timeout):
        configured.append(timeout)
        return await actual_wait(awaitable, timeout=timeout)

    class Checker:
        def __init__(self, **kwargs):
            configured.append(kwargs["deadline_seconds"])

        def check(self, request):
            remaining = request_deadline.get() - monotonic()
            assert 0 < remaining <= seconds
            return {"cards": []}

    monkeypatch.setattr("api.main.asyncio.wait_for", observe_wait)
    monkeypatch.setattr("api.main.OnePassCheckService", Checker)
    app = create_app(
        Settings(
            openai_api_key="inert",
            openai_model_extract="test-model",
            openai_model_reason="test-model",
            openai_schema_warmup=False,
            check_deadline_seconds=seconds,
        )
    )
    with TestClient(app) as client:
        result = client.post("/api/v1/check", json={"original_text": "test input"})
    assert result.status_code == 200
    assert configured == [seconds, seconds]


def test_server_default_is_sixty_seconds(monkeypatch):
    monkeypatch.delenv("CHECK_DEADLINE_SECONDS", raising=False)
    assert Settings().check_deadline_seconds == 60
