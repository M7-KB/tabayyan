"""Offline privacy probes: only minimized topics cross the source boundary."""

import pytest

from api.check import CheckRequest, CheckService
from api.extract import ExtractResponse
from api.search_phrases import SearchPhraseExtractor
from tests.test_composer import Stub, claim, proposal
from tests.test_gatekeeper import composer_with
from tests.test_islamic_mcp import gate


@pytest.mark.parametrize(
    "value",
    [
        RuntimeError("private provider detail"),
        {},
        {"phrases": [], "safe_to_search": True},
        {"phrases": ["worship"], "safe_to_search": False},
        {"phrases": ["SENTINEL_9381"], "safe_to_search": True},
        {"phrases": ["name@example.com"], "safe_to_search": True},
        {"phrases": ["one two three four five six seven"], "safe_to_search": True},
        {"phrases": ["a" * 81], "safe_to_search": True},
        {"phrases": ["my marriage"], "safe_to_search": True},
        {"phrases": ["full claim"], "safe_to_search": True},
        {"phrases": ["full claim", "additional topic"], "safe_to_search": True},
        {"phrases": ["public topic"], "safe_to_search": True, "extra": "private"},
    ],
)
def test_unsafe_or_unavailable_query_has_no_fallback(value):
    phrases = SearchPhraseExtractor(Stub(value))
    assert phrases.extract(text="Full claim!", claims=["Full claim!"]) is None


@pytest.mark.parametrize(
    "level,kind,status",
    [
        ("D", "claim", "rule_forced"),
        ("B", "term", "model_validated"),
        ("D", "claim", "unavailable"),
        ("D", "claim", "low_confidence"),
    ],
)
def test_disallowed_routes_do_not_even_extract_phrases(level, kind, status):
    service, model, connector = make_service(level=level, kind=kind, status=status)
    service.check(CheckRequest(claims=[{"id": "c1", "text_ar": "fixture"}], input_kind=kind))
    assert not model.calls
    assert not connector.calls


def make_service(*, level="A", kind="claim", status="model_validated", value=None):
    class Extractor:
        detector = None

        def extract(self, request):
            return ExtractResponse(
                detected_lang="en",
                input_kind=kind,
                claims=[claim(text=request.text, level=level, status=status)],
                dropped_count=0,
                no_checkable_claim=False,
            )

    class Connector:
        def __init__(self):
            self.calls = []

        def discover(self, query, scope):
            self.calls.append(query)
            return []

    model = Stub(value if value is not None else {"phrases": ["worship"], "safe_to_search": True})
    connector = Connector()
    return (
        CheckService(
            extractor=Extractor(),
            composer=composer_with(gate(), proposal()),
            corpus_version="synthetic",
            connector=connector,
            search_phrases=SearchPhraseExtractor(model),
        ),
        model,
        connector,
    )


def test_full_original_context_never_reaches_source_connector():
    service, model, connector = make_service()
    original = "Verify a public topic. Unrelated private context SENTINEL_9381"
    service.check(
        CheckRequest(
            claims=[{"id": "c1", "text_ar": original}],
            original_text=original,
        )
    )
    assert model.calls[0]["data"] == {"text": original}
    assert connector.calls == ["العبادة"]
    assert all("SENTINEL_9381" not in query for query in connector.calls)


def test_unavailable_phrase_step_does_not_send_claim_or_context():
    service, _, connector = make_service(value=RuntimeError("private text"))
    service.check(CheckRequest(claims=[{"id": "c1", "text_ar": "private context"}]))
    assert not connector.calls


def test_no_model_and_oversize_batch_fail_closed():
    assert SearchPhraseExtractor(None).extract(text="text", claims=["text"]) is None
    value = {"phrases": ["a" * 60, "b" * 60, "c" * 60], "safe_to_search": True}
    assert SearchPhraseExtractor(Stub(value)).extract(text="text", claims=["text"]) is None


@pytest.mark.parametrize("private_phrase", ["PrivateContextSentinel", "Alice Example", "سارة أحمد"])
@pytest.mark.parametrize("with_valid_topic", [False, True])
def test_adversarial_private_topic_proposal_never_reaches_connector(
    private_phrase, with_valid_topic
):
    proposed = ["worship", private_phrase] if with_valid_topic else [private_phrase]
    service, _, connector = make_service(value={"phrases": proposed, "safe_to_search": True})
    original = "Check a general subject. Unrelated private context " + private_phrase
    service.check(CheckRequest(claims=[{"id": "c1", "text_ar": original}], original_text=original))
    assert not connector.calls


def test_topic_mapping_is_closed_and_contains_no_provider_strings():
    from api.search_phrases import TOPIC_QUERIES, SearchPhraseProposal

    schema_ids = set(
        SearchPhraseProposal.model_json_schema()["properties"]["phrases"]["items"]["enum"]
    )
    assert schema_ids == set(TOPIC_QUERIES)
    for topic, expected in TOPIC_QUERIES.items():
        value = {"phrases": [topic], "safe_to_search": True}
        actual = SearchPhraseExtractor(Stub(value)).extract(
            text="PrivateContextSentinel", claims=["PrivateContextSentinel"]
        )
        assert actual == expected


def test_canonical_query_cannot_copy_a_complete_claim():
    model = Stub({"phrases": ["tawhid"], "safe_to_search": True})
    assert SearchPhraseExtractor(model).extract(text="التوحيد!", claims=["التوحيد!"]) is None
