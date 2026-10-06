"""Synthetic v2 field wiring, source binding and retained safety boundaries."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from api.bayyinat_matcher import BayyinatMatcher
from api.check import CheckRequest
from api.gatekeeper import QuoteGatekeeper, SourceRequest
from api.glossary_matcher import GlossaryMatcher
from api.main import create_app
from api.private_short_discovery import PrivateShortDiscovery
from api.settings import Settings
from api.span_detector import DetectorConfig
from corpus.short_indexes import AUTHORITY_EVENT
from tests.test_composer import POLICY, TUNING, proposal
from tests.test_gatekeeper import composer_with, gate, local
from tests.test_one_pass import route_proposal, service
from tests.test_private_index_matchers import FakeEmbedder, vector
from tests.test_short_indexes import handoff


def row(source="bayyinat"):
    if source == "bayyinat":
        return {
            "id": "/ar/category/1/2",
            "url": "https://bayenat.net/ar/category/1/2",
            "title": "عنوان تجريبي",
            "question_text": "سؤال تجريبي",
            "summary": "خلاصة تجريبية",
            "keywords": ["مكتب"],
            "detailed_answer": "تفاصيل تجريبية\nفقرة ثانية",
        }
    return {
        "id": "/dictionary/word/1",
        "url": "https://islamic-content.com/dictionary/word/1",
        "term_ar": "مصطلح تجريبي",
        "terminological_meaning": "معنى اصطلاحي تجريبي",
        "short_explanation": "مكتب تجريبي",
        "linguistic_definition": "لغة تجريبية",
        "definition": "تعريف تجريبي",
        "translations": ["English", "Français"],
    }


@pytest.mark.parametrize(
    "source,matcher_type", [("bayyinat", BayyinatMatcher), ("jamhara-glossary", GlossaryMatcher)]
)
def test_v2_private_handoff_builds_matcher_and_retains_raw_fields(tmp_path, source, matcher_type):
    raw = row(source)
    digest, registry, _ = handoff(tmp_path, source, [raw], version=2)
    embedder = FakeEmbedder()
    matcher = asyncio.run(
        matcher_type.from_private_files(
            tmp_path,
            digest,
            embedder,
            sources_path=registry,
            allow_pending_review=True,
            expected_format_version=2,
        )
    )
    candidates = asyncio.run(matcher.candidates("مكتب", level="A"))
    assert candidates[0].record == raw
    assert candidates[0].lexical_score > 0
    assert (
        matcher_type.display_text(raw)
        == raw["summary" if source == "bayyinat" else "terminological_meaning"]
    )


def test_bayyinat_fallback_is_exact_first_paragraph_with_400_character_cap():
    raw = row()
    raw["summary"] = ""
    raw["detailed_answer"] = "ح" * 450 + "\nSecond paragraph"
    assert BayyinatMatcher.display_text(raw) == raw["detailed_answer"][:400]
    raw["summary"] = "  Exact summary  "
    assert BayyinatMatcher.display_text(raw) == raw["summary"]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_bayyinat_first_paragraph_keeps_internal_lines_and_stops_at_blank_line(newline):
    raw = row()
    raw["summary"] = ""
    first = newline.join(["First original line", "Second original line"])
    raw["detailed_answer"] = first + newline + " \t" + newline + "Next paragraph"
    # Lines of the first paragraph are kept, joined by a line feed.
    assert BayyinatMatcher.display_text(raw) == first.replace("\r\n", "\n")


def test_bayyinat_single_paragraph_keeps_all_lines_until_character_cap():
    raw = row()
    raw["summary"] = ""
    raw["detailed_answer"] = "First original line\n" + "ح" * 450
    # The cap falls on the last whitespace inside the limit, never inside a word.
    assert BayyinatMatcher.display_text(raw) == "First original line"
    raw["detailed_answer"] = "First original line\n" + "ح" * 370
    assert BayyinatMatcher.display_text(raw) == raw["detailed_answer"]


def test_long_private_fields_bound_embedding_input_without_changing_display(tmp_path):
    raw = row()
    raw["detailed_answer"] = "س" * 6000
    digest, registry, _ = handoff(tmp_path, "bayyinat", [raw], version=2)
    embedder = FakeEmbedder()
    matcher = asyncio.run(
        BayyinatMatcher.from_private_files(
            tmp_path,
            digest,
            embedder,
            sources_path=registry,
            allow_pending_review=True,
            expected_format_version=2,
        )
    )
    assert len(embedder.calls[0][0][0].encode("utf-8")) <= 8000
    assert matcher._records[0]["detailed_answer"] == raw["detailed_answer"]
    assert BayyinatMatcher.display_text(matcher._records[0]) == raw["summary"]


def test_glossary_indexes_explanation_but_displays_meaning_without_fake_equivalent():
    raw = row("jamhara-glossary")
    indexed = GlossaryMatcher.search_text(raw)
    assert raw["short_explanation"] in indexed
    assert raw["terminological_meaning"] not in indexed
    matcher = GlossaryMatcher((raw,), [vector()], FakeEmbedder())
    request = SourceRequest()
    PrivateShortDiscovery(glossary=matcher).discover(
        "مكتب", request, kind="term", level="A", timeout=1
    )
    received = request._received[0].record
    assert received["text_ar"] == raw["terminological_meaning"]
    assert "text_en" not in received
    assert raw["short_explanation"] not in received.values()


def test_private_bayyinat_copy_is_source_bound_and_preserves_display_gates():
    raw = row()
    matcher = BayyinatMatcher((raw,), [vector()], FakeEmbedder())
    request = SourceRequest()
    PrivateShortDiscovery(bayyinat=matcher).discover(
        "مكتب", request, kind="doubt", level="B", timeout=1
    )
    gate = QuoteGatekeeper(
        local_records=[local()],
        request=request,
        detector_config=DetectorConfig.from_files(POLICY, TUNING),
    )
    key = "live:bayyinat:" + raw["id"]
    verified = gate.verify(key, raw["summary"])
    assert verified["text_ar"] == raw["summary"]
    assert verified["source_ref"]["url"] == raw["url"]
    assert gate.verify(key, raw["detailed_answer"]) is None
    assert gate.published_answer(key, raw["summary"])[0]["excerpt_ar"] == raw["summary"]


def test_level_d_skips_private_index_and_embedding():
    embedder = FakeEmbedder()
    matcher = BayyinatMatcher((row(),), [vector()], embedder)
    request = SourceRequest()
    PrivateShortDiscovery(bayyinat=matcher).discover(
        "private", request, kind="doubt", level="D", timeout=1
    )
    assert embedder.calls == [] and request._received == []


def test_one_pass_routes_private_term_discovery_before_composition():
    text = "مصطلح تجريبي"
    value = route_proposal(text, input_kind="term")
    value["claims"][0]["origin"] = "term_lookup"
    checker, _, _ = service(value, decision=proposal(state="CANNOT_CONFIRM"))
    calls = []

    class Discovery:
        def discover(self, text, request, **kwargs):
            calls.append(kwargs)

    checker.private_indexes = Discovery()
    checker.check(CheckRequest(original_text=text))
    assert calls[0]["kind"] == "term"
    assert calls[0]["level"] == "A" and calls[0]["timeout"] <= 3


def test_private_index_failure_returns_retryable_and_no_partial_cards():
    checker, _, _ = service(route_proposal("Synthetic"))

    class Failure:
        def discover(self, *args, **kwargs):
            raise RuntimeError("private error")

    checker.private_indexes = Failure()
    result = checker.check(CheckRequest(original_text="Synthetic"))
    assert result["cards"] == []
    assert result["retryable_results"][0]["code"] == "CHECK_INCOMPLETE"
    assert "private error" not in str(result)


def test_new_index_configuration_is_opt_in():
    settings = Settings()
    assert settings.private_short_index_dir is None
    assert settings.private_bayyinat_sha256 == settings.private_glossary_sha256 == ""


@pytest.mark.parametrize(
    "kind,source,matcher_type",
    [
        ("doubt", "bayyinat", BayyinatMatcher),
        ("term", "jamhara-glossary", GlossaryMatcher),
    ],
)
@pytest.mark.parametrize("quote_overlap", [True, False])
def test_one_pass_copies_private_source_through_composer_gate(
    kind, source, matcher_type, quote_overlap
):
    text = "مكتب تجريبي"
    routed = route_proposal(text, input_kind=kind, proposed_quran_refs=[{"surah": 1, "ayah": 1}])
    routed["claims"][0]["origin"] = "term_lookup" if kind == "term" else "question_subject"
    checker, _, _ = service(routed)
    raw = row(source)
    if quote_overlap:
        raw["summary" if source == "bayyinat" else "terminological_meaning"] = text
    key = "live:" + source + ":" + raw["id"]
    checker.composer = composer_with(gate(), proposal(state="SUPPORTED", corpus_ids=[key]))
    matcher = matcher_type((raw,), [vector()], FakeEmbedder())
    checker.private_indexes = PrivateShortDiscovery(
        **{"glossary" if kind == "term" else "bayyinat": matcher}
    )
    result = checker.check(CheckRequest(original_text=text))
    card = result["cards"][0]
    if kind == "term":
        # The publisher definition is shown as evidence; without a publisher-supplied
        # equivalent there is no term block, only the glossary link.
        assert card["state"] == "SUPPORTED"
        assert card["evidence"][0]["quote_ar"] == matcher_type.display_text(raw)
        assert card["term"] is None  # "English" alone is a language name, not an equivalent.
        assert "glossary_link" not in card  # The link stands in only when nothing is shown.
        return
    # A question's evidence is selected by ID from the request's validated records;
    # the lexical overlap floor applies to stated quotations only.
    assert card["state"] == "SUPPORTED"
    assert card["evidence"][0]["quote_ar"] == matcher_type.display_text(raw)
    assert card["evidence"][0]["source_ref"]["url"] == raw["url"]
    assert card["term"] is None
    if kind == "doubt":
        assert card["published_answer"]["excerpt_ar"] == raw["summary"]


def test_invalid_configured_handoff_is_unavailable_without_embedding(tmp_path, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Embedding must not run before artifact validation")

    monkeypatch.setattr("api.private_short_discovery.TransientIndexEmbedder.embed", forbidden)
    settings = Settings(
        openai_api_key="inert",
        openai_schema_warmup=False,
        private_short_index_dir=tmp_path,
        private_bayyinat_sha256="invalid",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["private_index_status"]["bayyinat"] == "unavailable"
        assert health["private_index_items"]["bayyinat"] == 0
        assert app.state.private_indexes.bayyinat is None


def write_manifest(directory, status="complete", source="bayyinat"):
    """Owner build manifest with one source entry; the loader itself is patched out."""
    name, host = (
        ("bayyinat.jsonl", "bayenat.net")
        if source == "bayyinat"
        else ("glossary.jsonl", "islamic-content.com")
    )
    manifest = {
        "format_version": 2,
        "complete": status == "complete",
        "authority_event": AUTHORITY_EVENT,
        "files": [
            {
                "file": name,
                "source_host": host,
                "sha256": "a" * 64,
                "bytes": 1,
                "records": 1,
                "status": status,
            }
        ],
    }
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_http_startup_wires_validated_matcher_into_check_service(tmp_path, monkeypatch):
    write_manifest(tmp_path)
    matcher = BayyinatMatcher((row(),), [vector()], FakeEmbedder())

    async def build(cls, directory, digest, embedder, **kwargs):
        assert kwargs["expected_format_version"] == 2
        return matcher

    monkeypatch.setattr(BayyinatMatcher, "from_private_files", classmethod(build))

    class Model:
        def __init__(self, **kwargs):
            pass

        def complete_json(self, **kwargs):
            return route_proposal("عقدي")

    monkeypatch.setattr("api.main.OpenAIStructuredModel", Model)
    app = create_app(
        Settings(
            openai_api_key="inert",
            openai_schema_warmup=False,
            private_short_index_dir=tmp_path,
            private_bayyinat_sha256="a" * 64,
        )
    )
    with TestClient(app) as client:
        assert client.get("/health").json()["private_index_items"]["bayyinat"] == 1
        app.state.corpus = [local()]
        response = client.post("/api/v1/check", json={"original_text": "عقدي"})
        assert response.status_code == 200
        assert app.state.checker.private_indexes.bayyinat is matcher


@pytest.mark.parametrize("status", ["complete", "partial"])
def test_health_reports_partial_sources_with_their_counts(tmp_path, monkeypatch, status):
    write_manifest(tmp_path, status)
    matcher = BayyinatMatcher((row(),), [vector()], FakeEmbedder())
    seen = {}

    async def build(cls, directory, digest, embedder, **kwargs):
        seen.update(kwargs)
        return matcher

    monkeypatch.setattr(BayyinatMatcher, "from_private_files", classmethod(build))
    app = create_app(
        Settings(
            openai_api_key="inert",
            openai_schema_warmup=False,
            private_short_index_dir=tmp_path,
            private_bayyinat_sha256="a" * 64,
            private_short_index_allow_partial=True,
        )
    )
    with TestClient(app) as client:
        health = client.get("/health").json()
    assert seen["allow_partial"] is True
    assert health["private_index_status"]["bayyinat"] == (
        "loaded" if status == "complete" else "partial"
    )
    assert health["private_index_status"]["glossary"] == "not_configured"
    assert health["private_index_items"]["bayyinat"] == 1
    assert app.state.private_indexes.bayyinat is matcher
    assert app.state.private_indexes.glossary is None


def test_each_source_loads_independently(tmp_path, monkeypatch):
    write_manifest(tmp_path, source="jamhara-glossary")
    matcher = GlossaryMatcher(({**row("jamhara-glossary")},), [vector()], FakeEmbedder())

    async def build(cls, directory, digest, embedder, **kwargs):
        return matcher

    async def broken(cls, directory, digest, embedder, **kwargs):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(GlossaryMatcher, "from_private_files", classmethod(build))
    monkeypatch.setattr(BayyinatMatcher, "from_private_files", classmethod(broken))
    app = create_app(
        Settings(
            openai_api_key="inert",
            openai_schema_warmup=False,
            private_short_index_dir=tmp_path,
            private_glossary_sha256="b" * 64,
            private_bayyinat_sha256="c" * 64,
        )
    )
    with TestClient(app) as client:
        health = client.get("/health").json()
    assert health["private_index_status"] == {"bayyinat": "unavailable", "glossary": "loaded"}
    assert health["private_index_items"]["glossary"] == 1
    assert app.state.private_indexes.glossary is matcher


def test_partial_env_opt_in_is_explicit(monkeypatch):
    monkeypatch.delenv("PRIVATE_SHORT_INDEX_ALLOW_PARTIAL", raising=False)
    assert Settings(openai_api_key="inert").private_short_index_allow_partial is False
    monkeypatch.setenv("PRIVATE_SHORT_INDEX_ALLOW_PARTIAL", "true")
    assert Settings(openai_api_key="inert").private_short_index_allow_partial is True


def test_startup_logs_the_text_free_loader_reason(tmp_path, caplog):
    import logging

    write_manifest(tmp_path)
    # No bayyinat.jsonl exists: the loader's fixed reason names the failure, not a path.
    app = create_app(
        Settings(
            openai_api_key="inert",
            openai_schema_warmup=False,
            private_short_index_dir=tmp_path,
            private_bayyinat_sha256="a" * 64,
            allow_pending_review=True,
        )
    )
    with caplog.at_level(logging.WARNING, logger="api.main"), TestClient(app) as client:
        assert client.get("/health").json()["private_index_status"]["bayyinat"] == "unavailable"
    messages = [r.getMessage() for r in caplog.records if "Private short index" in r.getMessage()]
    assert messages == [
        "Private short index unavailable: source=bayyinat "
        "reason=Private short-index validation failed"
    ]
    assert str(tmp_path) not in " ".join(messages)
