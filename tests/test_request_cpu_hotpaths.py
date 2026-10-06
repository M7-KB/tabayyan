"""Per-request CPU hot paths: shared index, exact prefilter, bounded separation, deadline.

Synthetic nonreligious records only; timings use a generated fixture corpus and
assert generous bounds against the measured costs, not production accuracy.
"""

import random
import threading
from time import monotonic, perf_counter, sleep

import pytest

from api.check import CheckRequest
from api.composer import Composer, _chunk_counts
from api.config import load_config
from api.deadline import DeadlineExceeded, request_deadline
from api.extract import ExtractionError
from api.gatekeeper import QuoteGatekeeper, SourceRequest
from api.retrieval import BM25Retriever
from api.span_detector import DetectorConfig, Record, SpanDetector
from corpus.normalize import normalize_arabic
from tests.test_composer import POLICY, TUNING, Stub, claim, proposal
from tests.test_gatekeeper import local, raw
from tests.test_one_pass import service

LETTERS = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"


def vocabulary(seed=7, size=3000):
    rng = random.Random(seed)
    return ["".join(rng.choice(LETTERS) for _ in range(rng.randint(2, 7))) for _ in range(size)]


VOCAB = vocabulary()
WEIGHTS = [1 / (i + 1) ** 0.9 for i in range(len(VOCAB))]


def sentence(rng, n):
    return " ".join(rng.choices(VOCAB, WEIGHTS, k=n))


def fixture_corpus(quran=1000, hadith=500, seed=7):
    """Generated records shaped like the loader output, never source text."""
    rng = random.Random(seed)
    records = []
    for i in range(quran):
        text = sentence(rng, max(1, min(80, int(rng.lognormvariate(2.3, 0.7)))))
        s, a = 1 + i // 60, 1 + i % 60
        records.append(
            {
                "corpus_id": f"quran:{s}:{a}",
                "domain": "quran",
                "source_id": "kfc-mushaf",
                "source_name_ar": "مصدر تجريبي",
                "source_url": "https://example.invalid/quran",
                "text_ar": text,
                "text_normalized": normalize_arabic(text),
                "ref": {"surah": s, "ayah": a},
            }
        )
    for i in range(hadith):
        text = sentence(rng, max(3, min(200, int(rng.lognormvariate(3.2, 0.6)))))
        url = f"https://example.invalid/hadith/{i + 1}"
        records.append(
            {
                "corpus_id": f"hadeethenc:{i + 1}",
                "domain": "hadith",
                "source_id": "hadeethenc",
                "source_name_ar": "مصدر تجريبي",
                "source_url": url,
                "text_ar": text,
                "text_normalized": normalize_arabic(text),
                "ref": {"collection": "c", "number": str(i + 1), "attribution": "a"},
                "grading": {
                    "grade_ar": "تجريبي",
                    "grader_ar": "اختبار",
                    "grading_source_url": url,
                },
            }
        )
    return records


def composer_over(records, value=None):
    _, tuning = load_config(POLICY, TUNING)
    gatekeeper = QuoteGatekeeper(
        local_records=records,
        request=SourceRequest(),
        detector_config=DetectorConfig.from_files(POLICY, TUNING),
    )
    bound = gatekeeper.records
    return Composer(
        model=Stub(proposal() if value is None else value),
        retriever=BM25Retriever(bound, tuning),
        detector=gatekeeper.detector,
        records=bound,
        policy_path=POLICY,
        tuning_path=TUNING,
        gatekeeper=gatekeeper,
    )


@pytest.fixture(scope="module")
def corpus():
    return fixture_corpus()


@pytest.fixture(scope="module")
def shared(corpus):
    return composer_over(corpus)


def fastest(action, runs=3):
    best = float("inf")
    for _ in range(runs):
        started = perf_counter()
        action()
        best = min(best, perf_counter() - started)
    return best


def test_for_request_reuses_the_startup_index(shared):
    request = SourceRequest()
    derived = shared.for_request(request)
    assert request._used
    assert derived is not shared and derived.gatekeeper is not shared.gatekeeper
    # Nothing was copied or re-indexed: the request shares every local structure.
    assert derived.retriever is shared.retriever
    assert derived.detector is shared.detector
    assert derived.records is shared.records
    assert derived._chunks is shared._chunks
    assert derived.gatekeeper._records == shared.gatekeeper._records
    assert derived.gatekeeper.detector.index is shared.gatekeeper.detector.index
    assert shared.gatekeeper.scan_scripture("كلمة") == derived.gatekeeper.scan_scripture("كلمة")


def test_benchmark_retrieval_and_separation_on_fixture_corpus(shared):
    rng = random.Random(3)
    question = sentence(rng, 7)
    prose = sentence(rng, 20)

    def retrieval():
        bound = shared.for_request(SourceRequest())
        bound.retriever.retrieve(question, top_k=50)

    assert fastest(retrieval) < 0.3
    assert fastest(lambda: shared._isolated(prose)) < 0.1
    assert fastest(lambda: shared.detector.detect(sentence(rng, 12))) < 0.3


def test_received_records_are_layered_on_the_shared_base(corpus, shared):
    live = raw(text="كلمة فريدة للاختبار الحالي فقط")
    request = SourceRequest()
    request.receive(live)
    derived = shared.for_request(request)
    assert "live:islamqa:one" in derived.records and "live:islamqa:one" not in shared.records
    assert derived.retriever is not shared.retriever
    assert derived.records is not shared.records and derived._chunks is not shared._chunks
    hits = derived.retriever.retrieve(live["text_ar"], top_k=3)
    assert hits and hits[0].corpus_id == "live:islamqa:one"
    assert not shared.retriever.retrieve(live["text_ar"], top_k=3)
    # Layered postings score exactly like an index built over all records at once.
    _, tuning = load_config(POLICY, TUNING)
    scratch = BM25Retriever(list(derived.records.values()), tuning)
    for query in (live["text_ar"], sentence(random.Random(5), 6), corpus[3]["text_ar"]):
        expected = [
            (r.corpus_id, r.retrieval_score, r.overlap_score) for r in scratch.candidates(query)
        ]
        actual = [
            (r.corpus_id, r.retrieval_score, r.overlap_score)
            for r in derived.retriever.candidates(query)
        ]
        assert actual == expected
    # The base layer is untouched by the derived index.
    assert shared.retriever._count == len(corpus)
    assert all(not cid.startswith("live:") for cid in shared.records)


def test_derived_gatekeeper_equals_a_fresh_one_including_live_twins():
    locals_ = [local(), local("قلم دفتر ورقة مسطرة حقيبة", cid="local:two")]
    twin = raw("dorar-hadith", "قلم دفتر ورقة مسطرة حقيبة", domain="hadith")
    answer = raw(text="تفاحة برتقال موز عنب رمان ثم شرح")
    requests = [SourceRequest(), SourceRequest()]
    for request in requests:
        request.receive(dict(twin))
        request.receive(dict(answer))
    config = DetectorConfig.from_files(POLICY, TUNING)
    base = QuoteGatekeeper(local_records=locals_, request=SourceRequest(), detector_config=config)
    fresh = QuoteGatekeeper(local_records=locals_, request=requests[0], detector_config=config)
    derived = base.derive(requests[1])
    assert list(fresh._records) == list(derived._records)
    assert fresh._records == derived._records and fresh._live == derived._live
    assert fresh.detector.index == derived.detector.index
    assert fresh._embedded_detector.index == derived._embedded_detector.index
    for key, r in fresh._records.items():
        assert fresh.verify(key, r["text_ar"]) == derived.verify(key, r["text_ar"])
        assert fresh.dependencies(key, r["text_ar"]) == derived.dependencies(key, r["text_ar"])
    assert fresh.published_answer("live:islamqa:one", answer["text_ar"]) == (
        derived.published_answer("live:islamqa:one", answer["text_ar"])
    )
    assert derived.detector.detect(twin["text_ar"]) == fresh.detector.detect(twin["text_ar"])
    # The base keeps only its local records and index.
    assert list(base._records) == ["local:one", "local:two"] and not base._live
    assert len(base.detector.index) == 2


def test_window_prefilter_matches_the_exhaustive_classification():
    rng = random.Random(11)
    vocab = VOCAB[:40]
    config = DetectorConfig.from_files(POLICY, TUNING)
    for _ in range(40):
        records = []
        for i in range(rng.randint(1, 30)):
            words_ = [rng.choice(vocab) for _ in range(rng.randint(1, 12))]
            if records and rng.random() < 0.4:
                words_ = list(records[-1].text_ar.split())
                words_[rng.randrange(len(words_))] = rng.choice(vocab)
            records.append(Record(f"r:{i}", rng.choice(["quran", "hadith"]), " ".join(words_)))
        detector = SpanDetector(records, config)
        lookup = detector._lookup_for()
        for _ in range(25):
            tokens = tuple(rng.choice(vocab) for _ in range(rng.randint(1, 14)))
            if rng.random() < 0.6:
                base = list(rng.choice(records).text_ar.split())
                if rng.random() < 0.7:
                    base[rng.randrange(len(base))] = rng.choice(vocab)
                tokens = tuple(base)
            full = detector._classify(tokens, "B")
            fast = detector._window_match(tokens, lookup)
            if full.classification == "UNRELATED":
                assert fast is None
            else:
                assert fast == full


def test_extend_and_index_replacement_keep_detection_identical():
    config = DetectorConfig.from_files(POLICY, TUNING)
    first = [
        Record("a", "quran", "واحد اثنان ثلاثة أربعة"),
        Record("b", "hadith", "خمسة ستة سبعة ثمانية"),
    ]
    more = [Record("c", "quran", "واحد اثنان ثلاثة تسعة"), Record("d", "faq", "ليس في الفهرس")]
    base = SpanDetector(first, config)
    assert base.extend([Record("e", "faq", "ليس في الفهرس")]) is base
    extended = base.extend(more)
    together = SpanDetector(first + more, config)
    assert extended.index == together.index and len(extended.index) == 3
    text = "قال واحد اثنان ثلاثة أربعة ثم واحد اثنان ثلاثة تسعة"
    assert extended.detect(text) == together.detect(text)
    assert base.detect(text) != together.detect(text)  # The new record changes the result.
    with pytest.raises(ValueError):
        base.extend([Record("a", "quran", "مكرر")])
    # Tests replace the index tuple directly; derived lookups follow the new tuple.
    reversed_detector = SpanDetector(list(reversed(first + more)), config)
    together.index = tuple(reversed(together.index))
    assert together.detect(text) == reversed_detector.detect(text)
    assert together.classify("واحد اثنان ثلاثة تسعة", "B") == reversed_detector.classify(
        "واحد اثنان ثلاثة تسعة", "B"
    )


def records_for_isolation():
    return [
        {"corpus_id": "g:1", "domain": "glossary", "text_ar": "مصطلح تجريبي"},
        {"corpus_id": "g:2", "domain": "glossary", "text_ar": "مصطلح تجريبي"},
        {"corpus_id": "f:1", "domain": "faq", "text_ar": "شرح طويل عن الفاكهة والخضار"},
        {"corpus_id": "q:1", "domain": "quran", "text_ar": "كلمة"},
    ]


def isolation_engine(records):
    engine = Composer.__new__(Composer)
    engine.records = {r["corpus_id"]: r for r in records}
    engine._chunks = _chunk_counts(engine.records.values())
    engine.gatekeeper = None
    engine.policy = {"span_detector": {"required_status": "ran"}}

    class Detector:
        def _marked(self, text):
            return []

        def detect(self, text):
            from api.span_detector import Detection

            return Detection("ran")

    engine.detector = Detector()
    return engine


def test_isolated_uses_record_chunks_with_glossary_exemption():
    engine = isolation_engine(records_for_isolation())
    assert engine._isolated("نص عادي لا يحتوي على مقاطع")
    assert not engine._isolated("هذا كلمة واحدة")  # whole short record
    assert not engine._isolated("نص فيه مصطلح تجريبي هنا")  # whole two-word record
    assert not engine._isolated("كان شرح طويل عن شيء")  # 3-gram of a longer record
    assert engine._isolated("شرح عن الفاكهة")  # not a consecutive run of three words
    # A glossary label may match only its own definition, not another record's.
    assert not engine._isolated("مصطلح تجريبي", glossary_label_id="g:1")
    engine = isolation_engine(records_for_isolation()[:1] + records_for_isolation()[2:])
    assert engine._isolated("مصطلح تجريبي", glossary_label_id="g:1")
    assert not engine._isolated("مصطلح تجريبي", glossary_label_id="f:1")
    assert not engine._isolated("مصطلح تجريبي")


def expired(action):
    token = request_deadline.set(monotonic() - 1)
    try:
        return action()
    finally:
        request_deadline.reset(token)


def test_scans_stop_when_the_request_deadline_has_passed(shared):
    text = "تفاحة برتقال موز عنب رمان ثم شرح إضافي"
    assert shared.detector.detect(text).span_detector_status == "ran"
    with pytest.raises(DeadlineExceeded):
        expired(lambda: shared.detector.detect(text))
    with pytest.raises(DeadlineExceeded):
        expired(lambda: shared._isolated(text))
    with pytest.raises(DeadlineExceeded):
        expired(
            lambda: shared.compose(
                claim(text), original=text, lang="ar", input_kind="claim", no_checkable_claim=False
            )
        )
    request = SourceRequest()
    request.receive(raw())
    bound = shared.for_request(request)
    with pytest.raises(DeadlineExceeded):
        expired(lambda: bound.gatekeeper.verify("live:islamqa:one", raw()["text_ar"]))


def test_one_pass_reports_deadline_stopped_work_as_retryable():
    checker, _, _ = service()
    bound = checker.composer.for_request

    def for_request(request):
        current = bound(request)

        def compose(*args, **kwargs):
            raise DeadlineExceeded

        current.compose = compose
        return current

    checker.composer.for_request = for_request
    result = checker.check(CheckRequest(original_text="تفاحة برتقال موز عنب رمان"))
    assert result["cards"] == []
    assert [r["code"] for r in result["retryable_results"]] == ["CHECK_INCOMPLETE"]
    checker, _, _ = service()

    def route(text):
        raise DeadlineExceeded

    checker.router.route = route
    with pytest.raises(ExtractionError) as failure:
        checker.check(CheckRequest(original_text="تفاحة برتقال موز عنب رمان"))
    assert failure.value.code == "CHECK_INCOMPLETE"


def test_worker_still_running_at_the_deadline_stops_instead_of_finishing_a_card():
    checker, _, compose_model = service()
    checker.deadline_seconds = 0.3
    outcomes = []
    finished = threading.Event()
    bound = checker.composer.for_request

    class Slow:
        def complete_json(self, **kwargs):
            sleep(0.5)  # Past the deadline; the separation scan must not continue.
            return proposal(state="SUPPORTED", explanation_ar="شرح يحتاج إلى فحص الفصل")

    def for_request(request):
        current = bound(request)
        compose = current.compose

        def observed(*args, **kwargs):
            try:
                return compose(*args, **kwargs)
            except BaseException as exc:
                outcomes.append(type(exc))
                raise
            finally:
                finished.set()

        current.compose = observed
        return current

    checker.composer.model = Slow()
    checker.composer.for_request = for_request
    started = monotonic()
    result = checker.check(CheckRequest(original_text="تفاحة برتقال موز عنب رمان"))
    assert monotonic() - started < 1.5
    assert result["cards"] == [] and len(result["retryable_results"]) == 1
    assert finished.wait(timeout=2)
    assert outcomes == [DeadlineExceeded]
