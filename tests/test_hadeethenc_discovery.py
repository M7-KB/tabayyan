"""Synthetic discovery payloads; no religious text, grading or source references."""

import pytest

from api.gatekeeper import SourceRequest
from api.hadeethenc_discovery import HadeethEncDiscovery
from api.source_http import BoundedSourceHTTP, SourceUnavailable
from tests.test_gatekeeper import gate
from tests.test_hadeethenc import response


class SequenceHTTP:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, host, path, params):
        self.calls.append((host, path, params))
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return value


def categories():
    return [{"id": "7", "title": "apple fruit"}, {"id": "8", "title": "other"}]


def page():
    return {"data": [{"id": "42", "title": "apple fruit"}], "meta": {}}


def test_source_discovered_id_fetches_original_item_and_grade_in_same_scope():
    data = response()
    http = SequenceHTTP(categories(), page(), data)
    scope = SourceRequest()
    receipts = HadeethEncDiscovery(http).discover("apple fruit", scope)
    assert len(receipts) == 1
    assert http.calls[1] == (
        "hadeethenc.com",
        "/api/v1/hadeeths/list/",
        {"language": "ar", "category_id": "7", "page": "1", "per_page": "20"},
    )
    assert http.calls[2][2] == {"language": "ar", "id": "42"}
    assert receipts[0].record["grading"]["grading_source_id"] == "hadeethenc"
    verified = gate(request=scope).verify("live:hadeethenc:42", data["hadeeth"])
    assert verified["text_ar"] == data["hadeeth"]
    assert verified["grading"]["grade_ar"] == data["grade"]
    assert (
        gate(request=SourceRequest(), received=receipts).verify(
            "live:hadeethenc:42", data["hadeeth"]
        )
        is None
    )


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        [],
        [{"id": "7", "title": ""}],
        [{"id": "https://evil.test", "title": "apple"}],
        categories() * 2,
        categories() * 501,
    ],
)
def test_bad_categories_never_fetch_an_item(bad):
    http = SequenceHTTP(bad)
    scope = SourceRequest()
    assert HadeethEncDiscovery(http).discover("apple", scope) == []
    assert len(http.calls) == 1
    assert scope._received == []


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {},
        {"data": {}},
        {"data": page()["data"] * 21},
        {"data": page()["data"] * 2},
        {"data": [{"id": "../42", "title": "apple"}]},
    ],
)
def test_bad_page_never_fetches_an_item(bad):
    http = SequenceHTTP(categories(), bad)
    assert HadeethEncDiscovery(http).discover("apple", SourceRequest()) == []
    assert len(http.calls) == 2


def test_no_lexical_match_and_metadata_only_are_not_evidence():
    scope = SourceRequest()
    http = SequenceHTTP(categories())
    assert HadeethEncDiscovery(http).discover("unmatched", scope) == []
    assert len(http.calls) == 1
    http = SequenceHTTP(categories(), {"data": [{"id": "42", "title": "unmatched"}]})
    assert HadeethEncDiscovery(http).discover("apple", scope) == []
    assert len(http.calls) == 2
    assert scope._received == []


def test_bounded_selection_drops_ungraded_and_never_retries_or_paginates():
    data = {"data": [{"id": str(i), "title": "apple fruit"} for i in (42, 43, 44)]}
    ungraded = {**response(), "id": "43", "grade": None}
    http = SequenceHTTP(categories(), data, response(), ungraded)
    receipts = HadeethEncDiscovery(http).discover("apple", SourceRequest())
    assert len(receipts) == 1
    assert len(http.calls) == 4
    http = SequenceHTTP(SourceUnavailable())
    assert HadeethEncDiscovery(http).discover("apple", SourceRequest()) == []
    assert len(http.calls) == 1


@pytest.mark.parametrize("query", [None, "", " ", "x" * 12001])
def test_invalid_query_and_consumed_scope_make_no_calls(query):
    http = SequenceHTTP()
    assert HadeethEncDiscovery(http).discover(query, SourceRequest()) == []
    scope = SourceRequest()
    gate(request=scope)
    assert HadeethEncDiscovery(http).discover("apple", scope) == []
    assert http.calls == []


def test_endpoint_allowlist_binds_path_to_host():
    for host, path in [
        ("dorar.net", "/api/v1/hadeeths/list/"),
        ("hadeethenc.com", "/dorar_api.json"),
        ("hadeethenc.com", "/api/v1/search/"),
    ]:
        with pytest.raises(SourceUnavailable):
            BoundedSourceHTTP().get(host, path, {})
