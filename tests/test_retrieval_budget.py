"""Synthetic sources exercise concurrency, timeout isolation and search-only aliases."""

import threading
from time import monotonic

import pytest

from api.check import CheckRequest
from api.deadline import request_deadline
from api.diagnostics import Summary, summary
from api.discovery import DefaultDiscovery
from api.gatekeeper import SourceRequest
from api.retrieval import BM25Retriever
from api.source_http import _remaining
from corpus.normalize import normalize_arabic
from tests.test_composer import TEXT, claim, engine, proposal
from tests.test_default_discovery import Adapter
from tests.test_gatekeeper import gate
from tests.test_one_pass import route_proposal, service
from tests.test_retrieval import record, tuning


def test_sources_run_in_parallel_with_inherited_correlation():
    barrier = threading.Barrier(2)
    deadlines = []

    class Parallel:
        def discover(self, query, scope):
            deadlines.append(request_deadline.get())
            barrier.wait(timeout=1)
            return [scope.receive({"source_id": "synthetic", "text_ar": "source fixture"})]

    scope = SourceRequest()
    metrics = Summary()
    token = summary.set(metrics)
    try:
        received = DefaultDiscovery(mcp=Parallel(), hadeethenc=Parallel()).discover("hadith", scope)
    finally:
        summary.reset(token)
    assert len(received) == len(scope._received) == 2
    assert all(r.request_token is scope._token for r in received)
    assert deadlines[0] == deadlines[1]
    assert {s[0] for s in metrics.stages} == {"retrieval_mcp", "retrieval_hadeethenc"}


def test_timed_out_source_cannot_append_late_receipts(monkeypatch):
    release, finished = threading.Event(), threading.Event()

    class Slow:
        def discover(self, query, scope):
            try:
                release.wait(timeout=1)
                return [scope.receive({"text_ar": "late fixture"})]
            finally:
                finished.set()

    monkeypatch.setattr(DefaultDiscovery, "TIMEOUT", 0.05)
    scope = SourceRequest()
    started = monotonic()
    try:
        assert DefaultDiscovery(mcp=Slow()).discover("public fixture", scope) == []
        assert monotonic() - started < 0.5
        assert scope._received == []
    finally:
        release.set()
    assert finished.wait(timeout=1)
    assert scope._received == []


def test_source_socket_budget_respects_discovery_deadline():
    deadline = monotonic() + 0.1
    token = request_deadline.set(deadline)
    try:
        assert 0 < _remaining(monotonic() + 10) <= 0.1
    finally:
        request_deadline.reset(token)


def test_expired_request_starts_no_sources():
    adapter = Adapter()
    token = request_deadline.set(monotonic() - 1)
    try:
        assert DefaultDiscovery(mcp=adapter).discover("public fixture", SourceRequest()) == []
    finally:
        request_deadline.reset(token)
    assert adapter.calls == []


def test_successful_batch_survives_other_source_timeout(monkeypatch):
    release, finished = threading.Event(), threading.Event()

    class Fast:
        def discover(self, query, scope):
            return [scope.receive({"text_ar": "successful fixture"})]

    class Slow:
        def discover(self, query, scope):
            try:
                release.wait(timeout=1)
                return []
            finally:
                finished.set()

    monkeypatch.setattr(DefaultDiscovery, "TIMEOUT", 0.05)
    scope, metrics = SourceRequest(), Summary()
    token = summary.set(metrics)
    try:
        receipts = DefaultDiscovery(mcp=Fast(), hadeethenc=Slow()).discover("hadith", scope)
    finally:
        release.set()
        summary.reset(token)
    assert finished.wait(timeout=1)
    assert len(receipts) == len(scope._received) == 1
    assert receipts[0].record["text_ar"] == "successful fixture"
    assert [(s[0], s[1]) for s in metrics.stages] == [
        ("retrieval_mcp", "completed"),
        ("retrieval_hadeethenc", "timeout"),
    ]


@pytest.mark.parametrize("kind", ["verse", "term"])
def test_verse_and_term_skip_both_sources(kind):
    routed = route_proposal(TEXT, input_kind=kind)
    if kind == "term":
        routed["claims"][0]["origin"] = "term_lookup"
    checker, _, _ = service(routed)
    mcp, hadeethenc = Adapter(), Adapter()
    checker.connector = DefaultDiscovery(mcp=mcp, hadeethenc=hadeethenc)
    checker.check(CheckRequest(original_text=TEXT))
    assert not mcp.calls and not hadeethenc.calls


def test_aliases_count_each_query_word_once_and_preserve_source():
    original = record("والتفاحة والتفاحة")
    search = BM25Retriever([original], tuning())
    result = search.candidates("التفاحة مجهول")[0]
    assert result.overlap_score == 0.5
    assert result.record == original
    assert search.candidates("التفاحة التفاحة مجهول")[0] == result


def test_owner_supplied_lookup_fragment_passes_overlap_floor():
    # Input fragment supplied by the owner in the task, used for lexical matching
    # only: this fixture is not a Quran record and is never displayed as evidence.
    result = BM25Retriever([record("وخاتم النبيين")], tuning()).retrieve("من هو خاتم الأنبياء؟")
    assert result[0].overlap_score == 0.25


def test_clitic_overlap_allows_confirms_without_changing_display_text():
    r = record("والتفاحة برتقال موز")
    from tests.test_composer import record as full_record

    r = full_record(text=r["text_ar"])
    r["text_normalized"] = normalize_arabic(r["text_ar"])
    composer = engine(records=[r], value=proposal(state="SUPPORTED"))
    question = "من هو التفاحة؟"
    card = composer.compose(
        claim(question, origin="question_subject"),
        original=question,
        lang="ar",
        input_kind="question",
        no_checkable_claim=False,
        propose_state=True,
    )
    assert card["state"] == "SUPPORTED"
    assert card["alignment"] == "CONFIRMS"
    assert card["evidence"][0]["quote_ar"] == r["text_ar"]


def test_composer_post_provider_stages_are_text_free():
    from tests.test_gatekeeper import local

    composer = engine(
        records=[local()], value=proposal(state="SUPPORTED", corpus_ids=["local:one"])
    )
    composer.gatekeeper = gate()
    metrics = Summary()
    token = summary.set(metrics)
    try:
        composer.compose(
            claim(),
            original=TEXT,
            lang="ar",
            input_kind="claim",
            no_checkable_claim=False,
            propose_state=True,
        )
    finally:
        summary.reset(token)
    names = {s[0] for s in metrics.stages}
    assert {
        "composer_gatekeeper",
        "composer_dependencies",
        "composer_published_answer",
        "composer_post_provider",
        "composer_separation",
    } <= names
    assert TEXT not in str(metrics.stages)
