"""Synthetic source adapter and transport checks; no live religious content."""

import io

import pytest

from api.composer import evidence_from
from api.dorar_smoke import probe
from api.gatekeeper import SourceRequest
from api.hadeethenc import SOURCE_NAME_AR, HadeethEncConnector
from api.retrieval import RetrievalResult
from api.source_http import BoundedSourceHTTP, SourceUnavailable
from tests.test_composer import claim, proposal
from tests.test_gatekeeper import compose, composer_with, gate, raw


class StubHTTP:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def get(self, host, path, params):
        self.calls.append((host, path, params))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def response():
    return {
        "id": "42",
        "hadeeth": "Synthetic apple banana pear plum fruit.",
        "grade": "  Synthetic grade.  ",
        "attribution": "Synthetic collection",
        "reference": "Synthetic edition",
        "explanation": "Untrusted unused prose",
    }


def test_hadeethenc_copies_same_response_bytes_and_source_label():
    data = response()
    http = StubHTTP(data)
    request = SourceRequest()
    receipt = HadeethEncConnector(http).receive("42", request)
    assert http.calls == [
        ("hadeethenc.com", "/api/v1/hadeeths/one/", {"language": "ar", "id": "42"})
    ]
    g = gate(request=request)
    r = g.verify("live:hadeethenc:42", data["hadeeth"])
    assert r is not None
    item = evidence_from(RetrievalResult(r, 1, 1))
    assert item["quote_ar"] == data["hadeeth"]
    assert item["grading"] == {
        "grade_ar": data["grade"],
        "grader_ar": SOURCE_NAME_AR,
        "grading_source_url": "https://hadeethenc.com/ar/browse/hadith/42",
    }
    assert item["source_ref"]["record_ref"] == "42"
    assert "explanation" not in receipt.record
    assert receipt.record["grading"]["grading_source_id"] == "hadeethenc"
    data["grade"] = "changed after reception"
    assert g.verify("live:hadeethenc:42", item["quote_ar"])["grading"] == {
        **item["grading"],
        "grading_source_id": "hadeethenc",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "43"),
        ("grade", None),
        ("grade", " "),
        ("hadeeth", None),
        ("hadeeth", "x" * 12001),
        ("reference", []),
        ("attribution", ""),
    ],
)
def test_malformed_or_ungraded_response_is_dropped(field, value):
    data = response()
    data[field] = value
    scope = SourceRequest()
    assert HadeethEncConnector(StubHTTP(data)).receive("42", scope) is None
    assert scope._received == []


@pytest.mark.parametrize(
    "item_id", ["0", "-1", "../42", "42?url=bad", "https://evil.test", "042", 42]
)
def test_invalid_item_id_never_calls_source(item_id):
    http = StubHTTP(response())
    assert HadeethEncConnector(http).receive(item_id, SourceRequest()) is None
    assert http.calls == []


def test_failure_is_not_retried_and_old_scope_cannot_authorize():
    http = StubHTTP(SourceUnavailable(403))
    assert HadeethEncConnector(http).receive("42", SourceRequest()) is None
    assert len(http.calls) == 1
    old = SourceRequest()
    receipt = HadeethEncConnector(StubHTTP(response())).receive("42", old)
    assert (
        gate(request=SourceRequest(), received=[receipt]).verify(
            "live:hadeethenc:42", response()["hadeeth"]
        )
        is None
    )


def test_two_sources_keep_their_own_gradings_without_replacement():
    scope = SourceRequest()
    HadeethEncConnector(StubHTTP(response())).receive("42", scope)
    d = raw("dorar-hadith", response()["hadeeth"], domain="hadith")
    scope.receive(d)
    g = gate(request=scope)
    for key, expected in [
        ("live:hadeethenc:42", response()["grade"]),
        ("live:dorar-hadith:one", d["grading"]["grade_ar"]),
    ]:
        r = g.verify(key, response()["hadeeth"])
        assert evidence_from(RetrievalResult(r, 1, 1))["grading"]["grade_ar"] == expected
    card = compose(g, proposal(corpus_ids=["live:hadeethenc:42"]), response()["hadeeth"])
    assert {e["source_id"] for e in card["evidence"]} == {"hadeethenc", "dorar-hadith"}
    assert {e["grading"]["grade_ar"] for e in card["evidence"]} == {
        response()["grade"],
        d["grading"]["grade_ar"],
    }


@pytest.mark.parametrize("failure", ["different_text", "ungraded", "invalid_url"])
def test_dorar_grade_never_attaches_to_other_or_invalid_record(failure):
    scope = SourceRequest()
    HadeethEncConnector(StubHTTP(response())).receive("42", scope)
    d = raw("dorar-hadith", response()["hadeeth"], domain="hadith")
    if failure == "different_text":
        d["text_ar"] = "Completely different synthetic content."
    elif failure == "ungraded":
        del d["grading"]
    else:
        d["grading"]["grading_source_url"] = "https://evil.invalid/grade"
    scope.receive(d)
    g = gate(request=scope)
    assert g.dependencies("live:hadeethenc:42", response()["hadeeth"]) == []


def test_asker_context_reaches_explanation_without_changing_quote_or_grade():
    scope = SourceRequest()
    HadeethEncConnector(StubHTTP(response())).receive("42", scope)
    g = gate(request=scope)
    engine = composer_with(g, proposal(corpus_ids=["live:hadeethenc:42"]))
    original = response()["hadeeth"] + " Explain simply; I am new to this topic."
    card = engine.compose(
        claim(original),
        original=original,
        lang="en",
        input_kind="question",
        no_checkable_claim=False,
    )
    assert engine.model.calls[0]["data"]["asker_context"] == original
    assert card["evidence"][0]["quote_ar"] == response()["hadeeth"]
    assert card["evidence"][0]["grading"]["grade_ar"] == response()["grade"]


def test_dorar_smoke_refuses_workstation_and_makes_one_render_call(monkeypatch):
    http = StubHTTP({"synthetic": True})
    monkeypatch.delenv("RENDER", raising=False)
    assert probe(http)["attempted"] is False
    assert http.calls == []
    monkeypatch.setenv("RENDER", "true")
    assert probe(http)["http_status"] == 200
    assert len(http.calls) == 1
    fail = StubHTTP(SourceUnavailable(403))
    assert probe(fail)["http_status"] == 403
    assert len(fail.calls) == 1


class FakeResponse:
    def __init__(
        self, body=b'{"ok":true}', status=200, content_type="application/json", encoding="identity"
    ):
        self.status = status
        self.body = io.BytesIO(body)
        self.headers = {"Content-Type": content_type, "Content-Encoding": encoding}

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read(self, size):
        return self.body.read(size)

    def close(self):
        self.body.close()


def install_transport(monkeypatch, response, addresses=("8.8.8.8",)):
    calls = []

    class Connection:
        def __init__(self, host, address, timeout, *, deadline):
            calls.append((host, address, timeout))

        def request(self, method, target, headers):
            calls.append((method, target, headers))

        def getresponse(self):
            return response

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(
        "api.source_http.socket.getaddrinfo",
        lambda *a, **k: [(None, None, None, None, (ip, 443)) for ip in addresses],
    )
    monkeypatch.setattr("api.source_http._PinnedHTTPS", Connection)
    return calls


def test_transport_pins_resolved_public_address_and_encodes_params(monkeypatch):
    calls = install_transport(monkeypatch, FakeResponse())
    assert BoundedSourceHTTP().get(
        "hadeethenc.com", "/api/v1/hadeeths/one/", {"id": "42 &x=1"}
    ) == {"ok": True}
    assert calls[0][:2] == ("hadeethenc.com", "8.8.8.8")
    assert 0 < calls[0][2] <= 10
    assert "42+%26x%3D1" in calls[1][1]
    assert calls[-1] == "closed"


@pytest.mark.parametrize(
    "addresses", [("127.0.0.1",), ("::1",), ("169.254.169.254",), ("8.8.8.8", "10.0.0.1"), ()]
)
def test_nonpublic_or_mixed_resolution_never_connects(monkeypatch, addresses):
    calls = install_transport(monkeypatch, FakeResponse(), addresses)
    with pytest.raises(SourceUnavailable):
        BoundedSourceHTTP().get("hadeethenc.com", "/api/v1/hadeeths/one/", {})
    assert calls == []


@pytest.mark.parametrize(
    "r",
    [
        FakeResponse(status=302),
        FakeResponse(status=403),
        FakeResponse(content_type="text/html"),
        FakeResponse(encoding="gzip"),
        FakeResponse(b'{"a":1,"a":2}'),
        FakeResponse(b"private-source-text"),
        FakeResponse(b"x" * (256 * 1024 + 1)),
    ],
)
def test_transport_failures_are_bounded_safe_and_not_retried(monkeypatch, r):
    calls = install_transport(monkeypatch, r)
    with pytest.raises(SourceUnavailable) as error:
        BoundedSourceHTTP().get("hadeethenc.com", "/api/v1/hadeeths/one/", {})
    assert str(error.value) == "Source unavailable"
    assert len(calls) == 3
    assert calls[-1] == "closed"


def test_unlisted_source_cannot_resolve_or_connect(monkeypatch):
    calls = install_transport(monkeypatch, FakeResponse())
    with pytest.raises(SourceUnavailable):
        BoundedSourceHTTP().get("hadeethenc.com.evil", "/api/v1/hadeeths/one/", {})
    assert calls == []
