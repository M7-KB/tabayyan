"""Synthetic wire and source fixtures; no stored publisher text or live calls."""

import json
import time

import pytest
from pydantic import ValidationError

from api.gatekeeper import SourceRequest
from api.islamic_mcp import DirectMCP, IslamicContentConnector, rpc_result
from api.settings import Settings
from api.source_http import SourceUnavailable
from tests.test_gatekeeper import gate

TEXT = "شرح تجريبي عن التفاح والموز والفاكهة"
URL = "https://islamcontent.com/ar/content/42"


def block(text, tag="COMMENTARY", url=URL):
    wrapped = f"Untrusted wrapper\n[{tag}] publisher label\n{text}\n[/{tag}]\n"
    wrapped += f"Source: {url}\n"
    return {
        "content": [
            {
                "type": "text",
                "text": wrapped,
            }
        ]
    }


def search(url=URL, id="library:42:ar"):
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"results": [{"id": id, "url": url, "title": "Unused title"}]}),
            }
        ]
    }


class Transport:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def call(self, name, arguments, *, deadline):
        self.calls.append((name, arguments, deadline))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


def test_discovery_copies_only_same_response_publisher_text():
    transport = Transport([search(), block(TEXT)])
    scope = SourceRequest()
    receipts = IslamicContentConnector(transport).discover("synthetic", scope)
    assert len(receipts) == 1
    assert receipts[0].record["text_ar"] == TEXT
    g = gate(request=scope)
    verified = g.verify("live:islamhouse:42", TEXT)
    assert verified is not None
    assert verified["source_ref"]["url"] == URL
    assert "Untrusted wrapper" not in verified["text_ar"]
    assert [x[0] for x in transport.calls] == ["search", "get_library_item"]
    assert len({x[2] for x in transport.calls}) == 1
    assert len(g.records) == 2  # Original local Quran is retained.


@pytest.mark.parametrize(
    "url,id",
    [
        ("https://islamcontent.com.evil/ar/content/42", "library:42:ar"),
        (URL, "library:42:en"),
        (URL, "hadith:42:ar"),
        ("https://islamcontent.com/ar/content/43", "library:42:ar"),
    ],
)
def test_metadata_only_or_unbound_identity_is_not_evidence(url, id):
    transport = Transport([search(url, id)])
    scope = SourceRequest()
    assert IslamicContentConnector(transport).discover("synthetic", scope) == []
    assert len(transport.calls) == 1
    assert scope._received == []


@pytest.mark.parametrize(
    "detail",
    [
        block(TEXT, url="https://evil.test/42"),
        block("English-only description"),
        {"isError": True, **block(TEXT)},
        {"content": [{"type": "image", "text": TEXT}]},
        block(TEXT + "x" * 12000),
        block(TEXT, tag="EXACT"),
        {"content": [{"type": "text", "text": "title and link only"}]},
        SourceUnavailable(),
    ],
)
def test_missing_raw_text_or_timeout_refuses_receipts(detail):
    scope = SourceRequest()
    assert IslamicContentConnector(Transport([search(), detail])).discover("synthetic", scope) == []
    assert scope._received == []


def test_failed_batch_discards_earlier_success():
    metadata = {
        "results": [
            {"id": f"library:{i}:ar", "url": f"https://islamcontent.com/ar/content/{i}"}
            for i in (42, 43)
        ]
    }
    transport = Transport(
        [
            {"content": [{"type": "text", "text": json.dumps(metadata)}]},
            block(TEXT),
            SourceUnavailable(),
        ]
    )
    scope = SourceRequest()
    assert IslamicContentConnector(transport).discover("synthetic", scope) == []
    assert scope._received == []


def test_verse_keeps_arabic_and_translation_from_one_exact_block():
    url = "https://islamenc.com/en/quran/1/1"
    text = "[1:1]\n" + TEXT + "\nSynthetic translation."
    scope = SourceRequest()
    receipt = IslamicContentConnector(Transport([block(text, "EXACT", url)])).verse(1, 1, scope)
    assert receipt.record["text_ar"] == TEXT + "\nSynthetic translation."
    assert receipt.record["source_id"] == "quranenc"
    # Synthetic Quran-like text is deliberately not authorized by local corpus.
    assert receipt.record["ref"] == {"surah": 1, "ayah": 1}


def test_wrong_verse_or_source_is_refused():
    scope = SourceRequest()
    text = "[1:2]\n" + TEXT + "\nSynthetic translation."
    assert (
        IslamicContentConnector(
            Transport([block(text, "EXACT", "https://islamenc.com/en/quran/1/1")])
        ).verse(1, 1, scope)
        is None
    )
    assert scope._received == []


@pytest.mark.parametrize("encoding", ["application/json", "text/event-stream"])
def test_matching_rpc_wire(encoding):
    value = {"jsonrpc": "2.0", "id": 1, "result": block(TEXT)}
    data = json.dumps(value).encode()
    if encoding == "text/event-stream":
        data = b"event: message\ndata: " + data + b"\n\n"
    assert rpc_result(data, encoding, 1) == value["result"]


@pytest.mark.parametrize(
    "data,encoding",
    [
        (b'{"jsonrpc":"2.0","id":2,"result":{}}', "application/json"),
        (b'{"jsonrpc":"2.0","id":1,"error":{}}', "application/json"),
        (b'{"jsonrpc":"2.0","id":1,"result":{"isError":true}}', "application/json"),
        (b'{"jsonrpc":"2.0","id":1,"id":1,"result":{}}', "application/json"),
        (b"data: {}\n\ndata: {}\n\n", "text/event-stream"),
        (b"<html>untrusted</html>", "text/html"),
    ],
)
def test_bad_rpc_is_refused(data, encoding):
    with pytest.raises((SourceUnavailable, ValueError)):
        rpc_result(data, encoding, 1)


def test_dns_private_address_is_not_connected(monkeypatch):
    monkeypatch.setattr("api.islamic_mcp._resolve", lambda d: {"127.0.0.1"})
    monkeypatch.setattr("api.islamic_mcp._PinnedHTTPS", lambda *a, **k: pytest.fail("connect"))
    with pytest.raises(SourceUnavailable):
        DirectMCP().call("search", {}, deadline=time.monotonic() + 10)


def test_unknown_tool_and_endpoint_never_reach_transport():
    with pytest.raises(SourceUnavailable):
        DirectMCP().call("byenah", {}, deadline=time.monotonic() + 10)
    with pytest.raises(ValidationError):
        Settings(islamic_content_mcp_url="https://evil.test/mcp")


@pytest.mark.parametrize(
    "status,encoding,ctype,oversize",
    [
        (200, "identity", "text/event-stream", False),
        (302, "identity", "text/event-stream", False),
        (200, "gzip", "application/json", False),
        (200, "identity", "text/html", False),
        (200, "identity", "application/json", True),
    ],
)
def test_fixed_host_post_bounds_and_cleanup(monkeypatch, status, encoding, ctype, oversize):
    import io

    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "result": block(TEXT)}).encode()
    if ctype == "text/event-stream":
        payload = b"data: " + payload + b"\n\n"
    if oversize:
        payload = b"x" * (DirectMCP.MAX_BYTES + 1)

    class Response(io.BytesIO):
        def getheader(self, key, default=None):
            return {"Content-Encoding": encoding, "Content-Type": ctype}.get(key, default)

    response = Response(payload)
    response.status = status
    calls = []

    class Connection:
        closed = False

        def request(self, method, path, *, body, headers):
            calls.append((method, path, json.loads(body)))

        def getresponse(self):
            return response

        def close(self):
            self.closed = True

    connection = Connection()

    def connect(host, address, timeout, *, deadline):
        assert host == "mcp.islamiccontent.org" and address == "8.8.8.8"
        return connection

    monkeypatch.setattr("api.islamic_mcp._resolve", lambda d: {"8.8.8.8"})
    monkeypatch.setattr("api.islamic_mcp._PinnedHTTPS", connect)
    if status == 200 and encoding == "identity" and ctype == "text/event-stream":
        assert DirectMCP().call("search", {}, deadline=time.monotonic() + 10) == block(TEXT)
    else:
        with pytest.raises(SourceUnavailable):
            DirectMCP().call("search", {}, deadline=time.monotonic() + 10)
    assert len(calls) == 1 and calls[0][:2] == ("POST", "/mcp")
    assert response.closed and connection.closed


@pytest.mark.parametrize(
    "level,kind,status,called",
    [
        ("A", "claim", "model_validated", True),
        ("D", "claim", "model_validated", False),
        ("B", "term", "model_validated", False),
        ("B", "claim", "unavailable", False),
    ],
)
def test_check_routes_server_classification_before_discovery(level, kind, status, called):
    from api.check import CheckRequest, CheckService
    from api.extract import ExtractResponse
    from tests.test_composer import TEXT as CLAIM_TEXT
    from tests.test_composer import claim, proposal
    from tests.test_gatekeeper import composer_with

    class Extractor:
        detector = None

        def extract(self, request):
            return ExtractResponse(
                detected_lang="ar",
                input_kind=kind,
                claims=[claim(level=level, status=status)],
                dropped_count=0,
                no_checkable_claim=False,
            )

    class Connector:
        calls = []

        def discover(self, query, scope):
            self.calls.append(query)
            return []

    connector = Connector()

    class Phrases:
        def extract(self, **kwargs):
            return "موضوع عام"

    service = CheckService(
        extractor=Extractor(),
        composer=composer_with(gate(), proposal()),
        corpus_version="synthetic",
        connector=connector,
        search_phrases=Phrases(),
    )
    request = CheckRequest(claims=[{"id": "c1", "text_ar": CLAIM_TEXT}], input_kind=kind)
    service.check(request)
    assert bool(connector.calls) == called
