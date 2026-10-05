"""Default route discovery is bounded by classification and minimized phrases."""

import pytest
from fastapi.testclient import TestClient

from api.discovery import DefaultDiscovery
from api.gatekeeper import SourceRequest
from api.main import create_app
from api.settings import Settings
from tests.test_search_phrases import make_service


class Adapter:
    def __init__(self, error=False):
        self.calls = []
        self.error = error

    def discover(self, query, scope):
        self.calls.append((query, scope))
        if self.error:
            raise RuntimeError("private diagnostics")
        return []


@pytest.mark.parametrize(
    "query,hadith", [("public topic", False), ("حديث موضوع عام", True), ("hadith topic", True)]
)
def test_only_hadith_topics_use_hadeethenc(query, hadith):
    mcp, hadeethenc = Adapter(), Adapter()
    scope = SourceRequest()
    DefaultDiscovery(mcp=mcp, hadeethenc=hadeethenc).discover(query, scope)
    assert mcp.calls == [(query, scope)]
    assert hadeethenc.calls == ([(query, scope)] if hadith else [])


def test_source_outage_and_consumed_scope():
    mcp, hadeethenc = Adapter(error=True), Adapter()
    scope = SourceRequest()
    assert DefaultDiscovery(mcp=mcp, hadeethenc=hadeethenc).discover("حديث عام", scope) == []
    assert len(hadeethenc.calls) == 1
    scope._used = True
    DefaultDiscovery(mcp=mcp, hadeethenc=hadeethenc).discover("حديث عام", scope)
    assert len(mcp.calls) == len(hadeethenc.calls) == 1


@pytest.mark.parametrize("mcp_enabled", [False, True])
def test_real_default_check_route_only_sends_minimized_query(monkeypatch, mcp_enabled):
    mcp, hadeethenc = Adapter(), Adapter()
    service, model, _ = make_service(value={"phrases": ["hadith"], "safe_to_search": True})
    service.extractor.model = model
    monkeypatch.setattr("api.main.Extractor", lambda **kwargs: service.extractor)
    monkeypatch.setattr("api.main.IslamicContentConnector", lambda: mcp)
    monkeypatch.setattr("api.main.HadeethEncDiscovery", lambda: hadeethenc)
    settings = Settings(
        openai_api_key="inert",
        openai_model_extract="fixture",
        openai_model_reason="fixture",
        islamic_content_mcp_url="https://mcp.islamiccontent.org/mcp" if mcp_enabled else "",
    )
    app = create_app(settings)
    original = "Verify the public topic. Private context SENTINEL_9381"
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert not mcp.calls and not hadeethenc.calls
        assert client.post("/api/v1/extract", json={"text": original}).status_code == 200
        assert not mcp.calls and not hadeethenc.calls
        response = client.post(
            "/api/v1/check",
            json={
                "claims": [{"id": "c1", "text_ar": original}],
                "original_text": original,
            },
        )
    assert response.status_code == 200
    assert len(hadeethenc.calls) == 1
    assert len(mcp.calls) == int(mcp_enabled)
    for query, scope in mcp.calls + hadeethenc.calls:
        assert query == "الحديث"
        assert "SENTINEL_9381" not in query
        assert scope._used


@pytest.mark.parametrize(
    "level,kind,status",
    [
        ("D", "claim", "rule_forced"),
        ("B", "term", "model_validated"),
        ("D", "claim", "unavailable"),
    ],
)
def test_forbidden_routes_call_neither_default_source(level, kind, status):
    from api.check import CheckRequest

    service, _, _ = make_service(level=level, kind=kind, status=status)
    mcp, hadeethenc = Adapter(), Adapter()
    service.connector = DefaultDiscovery(mcp=mcp, hadeethenc=hadeethenc)
    service.check(
        CheckRequest(claims=[{"id": "c1", "text_ar": "private fixture"}], input_kind=kind)
    )
    assert not mcp.calls and not hadeethenc.calls


@pytest.mark.parametrize("topic", ["PrivateContextSentinel", "Alice Example", "سارة أحمد"])
@pytest.mark.parametrize("mixed", [False, True])
def test_default_sources_reject_private_topic_proposals(topic, mixed):
    from api.check import CheckRequest

    service, _, _ = make_service(
        value={
            "phrases": ["hadith", topic] if mixed else [topic],
            "safe_to_search": True,
        }
    )
    mcp, hadeethenc = Adapter(), Adapter()
    service.connector = DefaultDiscovery(mcp=mcp, hadeethenc=hadeethenc)
    service.check(CheckRequest(claims=[{"id": "c1", "text_ar": "Synthetic topic " + topic}]))
    assert not mcp.calls and not hadeethenc.calls


def test_default_adapters_share_receipts_and_verbatim_gate():
    from api.hadeethenc_discovery import HadeethEncDiscovery
    from api.islamic_mcp import IslamicContentConnector
    from tests.test_gatekeeper import gate
    from tests.test_hadeethenc import response
    from tests.test_hadeethenc_discovery import SequenceHTTP
    from tests.test_islamic_mcp import TEXT, Transport, block, search

    transport = Transport([search(), block(TEXT)])
    http = SequenceHTTP(
        [{"id": "7", "title": "الحديث"}],
        {"data": [{"id": "42", "title": "الحديث"}]},
        response(),
    )
    scope = SourceRequest()
    receipts = DefaultDiscovery(
        mcp=IslamicContentConnector(transport),
        hadeethenc=HadeethEncDiscovery(http),
    ).discover("الحديث", scope)
    assert len(receipts) == 2
    verifier = gate(request=scope)
    assert verifier.verify("live:islamhouse:42", TEXT)["text_ar"] == TEXT
    assert (
        verifier.verify("live:hadeethenc:42", response()["hadeeth"])["grading"]["grade_ar"]
        == response()["grade"]
    )
    assert gate(request=SourceRequest()).verify("live:hadeethenc:42", response()["hadeeth"]) is None


def test_mcp_default_and_explicit_disable(monkeypatch):
    monkeypatch.delenv("ISLAMIC_CONTENT_MCP_URL", raising=False)
    assert Settings().islamic_content_mcp_url == "https://mcp.islamiccontent.org/mcp"
    assert Settings(islamic_content_mcp_url="").islamic_content_mcp_url == ""
