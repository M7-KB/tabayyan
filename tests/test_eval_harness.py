"""Acceptance tests for the eval harness (T-407).

The harness is the instrument the release gates are read from, so these tests
check that it fails when it should: a missing brief case, a SUPPORTED card with
no alignment, a card that does not validate, a CONFIRMS over a Qur'an-domain
near-miss, and a pair whose halves diverge. A stub that passes proves only that
the instrument runs end to end.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from eval import run as harness
from eval.assertions import HARD_ASSERTIONS
from eval.testset import TestsetError as LoadError
from eval.testset import load_testset, validate_record

ROOT = Path(__file__).resolve().parents[1]
TESTSET = ROOT / "eval" / "testset.jsonl"
BUNDLE = ROOT / "eval" / "stubs" / "contract_pass.json"
BLOCKED_BRIEF_IDS = ("T03", "T10", "T11")


def records():
    return load_testset(TESTSET)


def write_testset(path: Path, items) -> Path:
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items), encoding="utf-8"
    )
    return path


def write_bundle(path: Path, patch=None) -> Path:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    if patch is not None:
        patch(bundle)
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def overrides(bundle, case_id):
    return bundle["cases"][case_id]["cards"][0].setdefault("overrides", {})


def run(tmp_path, *, testset=TESTSET, bundle=BUNDLE, only=None, extra=()):
    report_path = tmp_path / "report.json"
    argv = [
        "--testset",
        str(testset),
        "--stub",
        str(bundle),
        "--json",
        str(report_path),
        "--quiet",
    ]
    if only:
        argv += ["--only", only]
    argv += list(extra)
    code = harness.main(argv)
    return code, json.loads(report_path.read_text(encoding="utf-8"))


def gate(report, gate_id):
    return next(item for item in report["gates"] if item["id"] == gate_id)


def case(report, case_id):
    return next(item for item in report["cases"] if item["case_id"] == case_id)


def assertion(report, case_id, name):
    return next(item for item in case(report, case_id)["assertions"] if item["name"] == name)


def countable_testset(tmp_path):
    """The current file with the three blocked brief cases marked countable."""
    items = records()
    for item in items:
        if item["case_id"] in BLOCKED_BRIEF_IDS:
            item["g9_countable"] = True
            item["blocked_reason_en"] = None
    return write_testset(tmp_path / "testset.jsonl", items)


def test_every_case_is_reported_with_every_hard_assertion(tmp_path):
    _, report = run(tmp_path)
    assert [item["case_id"] for item in report["cases"]] == [item["case_id"] for item in records()]
    for item in report["cases"]:
        names = {entry["name"] for entry in item["assertions"]}
        assert set(HARD_ASSERTIONS) <= names
        assert "pair_consistency" in names
        assert item["status"] == "pass", item["assertions"]
        assert item["soft_review"]["status"] == "awaiting manual review"


def test_blocked_brief_cases_fail_g9_and_the_run(tmp_path):
    code, report = run(tmp_path)
    assert code == 1
    assert report["outcome"] == "fail"
    detail = gate(report, "G9")["detail"]
    assert gate(report, "G9")["status"] == "fail"
    for case_id in BLOCKED_BRIEF_IDS:
        assert case_id in detail


def test_run_passes_once_every_brief_case_is_countable(tmp_path):
    code, report = run(tmp_path, testset=countable_testset(tmp_path))
    assert gate(report, "G9")["status"] == "pass"
    assert report["outcome"] == "pass"
    assert code == 0


def test_removing_a_brief_case_id_fails_the_run(tmp_path):
    items = [item for item in records() if item["case_id"] != "T05"]
    path = write_testset(tmp_path / "missing.jsonl", items)
    code, report = run(tmp_path, testset=path)
    assert code == 1
    assert "missing brief case T05" in gate(report, "G9")["detail"]


def test_supported_card_without_alignment_fails(tmp_path):
    def patch(bundle):
        overrides(bundle, "T01").update({"alignment": None})

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert assertion(report, "T01", "schema_valid")["status"] == "fail"
    assert assertion(report, "T01", "alignment")["status"] == "not_evaluated"
    assert gate(report, "G17")["status"] == "fail"
    assert "T01" in gate(report, "G17")["detail"]


def test_card_that_does_not_validate_fails(tmp_path):
    def patch(bundle):
        overrides(bundle, "T06").update({"unexpected_field": "x"})

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert assertion(report, "T06", "schema_valid")["status"] == "fail"
    assert gate(report, "G23")["status"] == "fail"


def test_confirms_over_a_quran_domain_near_miss_fails_g17(tmp_path):
    """Every hard assertion still passes; only the G17 property catches this."""

    def patch(bundle):
        overrides(bundle, "T04")["claim"]["scripture_spans"] = [
            {
                "start": 0,
                "end": 8,
                "marker": None,
                "nearest_corpus_id": "quran:2:255",
                "normalized_distance": 0.05,
                "classification": "NEAR_MISS",
            }
        ]

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert all(entry["status"] != "fail" for entry in case(report, "T04")["assertions"]), case(
        report, "T04"
    )["assertions"]
    assert gate(report, "G17")["status"] == "fail"
    assert "quran-domain NEAR_MISS" in gate(report, "G17")["detail"]


def test_confirms_over_an_unresolved_near_miss_fails_closed(tmp_path):
    def patch(bundle):
        overrides(bundle, "T04")["claim"]["scripture_spans"] = [
            {
                "start": 0,
                "end": 8,
                "marker": None,
                "nearest_corpus_id": "unknown-index:1",
                "normalized_distance": 0.05,
                "classification": "NEAR_MISS",
            }
        ]

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert "unresolved" in gate(report, "G17")["detail"]


def test_hadith_domain_near_miss_does_not_block_confirms(tmp_path):
    """The Qur'an/hadith split of section 5.2 is honoured, not flattened."""

    def patch(bundle):
        card = bundle["cases"]["T04"]["cards"][0]["overrides"]
        card["claim"].pop("scripture_spans")
        card.pop("misquote_notice")
        card["evidence"] = {"0": {"domain": "fiqh"}}

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert gate(report, "G17")["status"] == "pass"
    assert code == 0


def test_level_d_supported_fails_g4(tmp_path):
    def patch(bundle):
        overrides(bundle, "T05").update(
            {
                "state": "SUPPORTED",
                "alignment": "CONFIRMS",
                "state_label_key": "supported_confirms",
                "abstained_reason": None,
                "claim": {"scripture_spans": []},
                "misquote_notice": None,
            }
        )

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert gate(report, "G4")["status"] == "fail"
    assert assertion(report, "T05", "schema_valid")["status"] == "fail"
    assert assertion(report, "T05", "state")["status"] == "not_evaluated"


def test_pair_divergence_is_reported_with_both_case_ids(tmp_path):
    """Both halves pass their own expectations; the comparison still fails."""
    items = records()
    for item in items:
        if item["case_id"] == "T13":
            item["expect"]["abstained_reason"] = "NO_CHECKABLE_CLAIM"
            item["g9_countable"] = True
        if item["case_id"] in BLOCKED_BRIEF_IDS:
            item["g9_countable"] = True
            item["blocked_reason_en"] = None
    path = write_testset(tmp_path / "pair.jsonl", items)

    def patch(bundle):
        overrides(bundle, "T13")["abstained_reason"] = "NO_CHECKABLE_CLAIM"

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=path, bundle=bundle)
    assert code == 1
    for case_id in ("T09", "T13"):
        detail = assertion(report, case_id, "pair_consistency")["detail"]
        assert assertion(report, case_id, "pair_consistency")["status"] == "fail"
        assert "T09" in detail and "T13" in detail


def test_filtered_run_pulls_in_the_pair_partner(tmp_path):
    _, report = run(tmp_path, testset=countable_testset(tmp_path), only="T09")
    assert {item["case_id"] for item in report["cases"]} == {"T09", "T13"}
    # A filtered run has no G9 evidence either way, and must not claim it does.
    assert gate(report, "G9")["status"] == "not_evaluated"
    assert "not executed" in gate(report, "G9")["detail"]


def test_forbidden_substring_in_a_generated_field_fails(tmp_path):
    needle = next(item for item in records() if item["case_id"] == "T14")["expect"][
        "forbidden_substrings_ar"
    ][0]

    def patch(bundle):
        overrides(bundle, "T14")["explanation_ar"] = f"{needle} …"

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert assertion(report, "T14", "forbidden_substrings_ar")["status"] == "fail"


def test_input_echo_in_the_claim_block_is_not_a_fabrication(tmp_path):
    """T14's own input contains a forbidden attribution formula verbatim."""
    record = next(item for item in records() if item["case_id"] == "T14")
    assert record["expect"]["forbidden_substrings_ar"][0] in record["input"]["text"]
    _, report = run(tmp_path)
    assert assertion(report, "T14", "forbidden_substrings_ar")["status"] == "pass"
    assert case(report, "T14")["status"] == "pass"


def test_evidence_on_a_no_matching_evidence_card_fails(tmp_path):
    def patch(bundle):
        bundle["cases"]["T06"]["template"] = "supported-confirms"
        overrides(bundle, "T06").update(
            {
                "state": "CANNOT_CONFIRM",
                "alignment": None,
                "state_label_key": "cannot_confirm",
                "abstained_reason": "NO_MATCHING_EVIDENCE",
                "claim": {"scripture_spans": [], "level": "A", "origin": "question_subject"},
                "misquote_notice": None,
                "referral": {
                    "body_name_ar": "جهة تجريبية",
                    "body_url": "https://example.invalid/referral",
                    "fallback_line_ar": "سطر تجريبي",
                    "ready_to_ask_question_ar": "سؤال تجريبي",
                },
            }
        )

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    detail = assertion(report, "T06", "must_not_fabricate")["detail"]
    assert "NO_MATCHING_EVIDENCE card returned evidence items" in detail


def test_a_missing_response_fails_the_case_and_g19(tmp_path):
    def patch(bundle):
        bundle["cases"]["T05"] = {"error": "PIPELINE_DEGRADED"}

    bundle = write_bundle(tmp_path / "bundle.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert case(report, "T05")["error"] == "PIPELINE_DEGRADED"
    assert assertion(report, "T05", "response")["status"] == "fail"
    for name in HARD_ASSERTIONS:
        assert assertion(report, "T05", name)["status"] == "not_evaluated"
    assert gate(report, "G19")["status"] == "fail"


def test_corpus_dependent_gates_are_never_reported_as_passes(tmp_path):
    _, report = run(tmp_path)
    for gate_id in ("G1", "G2", "G16"):
        assert gate(report, gate_id)["status"] == "not_evaluated"
    assert gate(report, "G21")["status"] == "not_evaluated"
    assert gate(report, "G25")["status"] == "not_evaluated"
    assert report["metrics"]["unmatched_quotes"] is None


def test_report_pins_the_inputs_it_was_produced_from(tmp_path):
    _, report = run(tmp_path)
    assert report["testset"]["sha256"] and report["card_schema"]["sha256"]
    assert report["arm"] == "tabayyan"
    assert report["card_source"].startswith("stub:")


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda record: record.update(needs_sharia_review=False), id="review-flag"),
        pytest.param(lambda record: record.update(blocked_reason_en="x"), id="blocked-reason"),
        pytest.param(
            lambda record: record.update(paired_case_id=record["case_id"]), id="self-pair"
        ),
        pytest.param(lambda record: record.update(baseline=True), id="unknown-field"),
        pytest.param(lambda record: record.pop("g9_countable"), id="missing-field"),
        pytest.param(
            lambda record: record["expect"].update(state="DISPUTED"), id="alignment-shape"
        ),
    ],
)
def test_loader_rejects_a_broken_record(mutate):
    record = next(item for item in records() if item["case_id"] == "T01")
    mutate(record)
    with pytest.raises(LoadError):
        validate_record(record, "probe")


def test_loader_rejects_a_one_sided_pair(tmp_path):
    items = [item for item in records() if item["case_id"] != "T13"]
    path = write_testset(tmp_path / "one-sided.jsonl", items)
    with pytest.raises(LoadError):
        load_testset(path)


def test_the_corpus_free_arm_is_named_control_everywhere():
    """Section 6.5: the arm is `control`, and the retired word names nothing."""
    retired = "base" + "line"
    for path in sorted((ROOT / "eval").glob("*.py")) + [BUNDLE]:
        assert retired not in path.read_text(encoding="utf-8").lower(), path
    assert harness.ARMS == ("tabayyan", "control")


class _Handler(BaseHTTPRequestHandler):
    """A stub API: the section 3 extract/check shape, cards from the bundle."""

    cards: list = []

    def log_message(self, *args):  # noqa: A003 - silence the test server
        return

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/v1/extract":
            payload = {
                "detected_lang": "ar",
                "input_kind": "question",
                "claims": [{"id": "c1", "text_ar": body["text"], "level": "D"}],
                "dropped_count": 0,
                "no_checkable_claim": False,
            }
        elif self.path == "/api/v1/check":
            payload = {
                "cards": self.cards,
                "corpus_version": "v0",
                "policy_version": "p1",
                "tuning_version": "t1",
                "card_schema_version": "1",
                "disclaimer_ar": "هذه أداة ذكاء اصطناعي، وليست فتوى.",
                "generated_at": "2026-10-04T00:00:00Z",
            }
        else:
            self.send_error(404)
            return
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def test_http_client_runs_a_case_end_to_end(tmp_path):
    from eval.clients import StubClient

    testset = countable_testset(tmp_path)
    record = next(item for item in records() if item["case_id"] == "T05")
    _Handler.cards = StubClient(BUNDLE).cards_for(record).cards
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report_path = tmp_path / "http.json"
        code = harness.main(
            [
                "--testset",
                str(testset),
                "--api-base",
                f"http://127.0.0.1:{server.server_port}",
                "--only",
                "T05",
                "--json",
                str(report_path),
                "--quiet",
            ]
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
    finally:
        server.shutdown()
        server.server_close()
    assert code == 0, report["cases"]
    assert case(report, "T05")["status"] == "pass"
    assert report["card_source"].startswith("http:")
    assert report["testset"] == {
        **report["testset"],
        "records": len(records()),
        "executed": 1,
    }


def test_http_client_reports_an_unreachable_api_as_a_failure(tmp_path):
    report_path = tmp_path / "down.json"
    code = harness.main(
        [
            "--testset",
            str(TESTSET),
            "--api-base",
            "http://127.0.0.1:9",
            "--only",
            "T05",
            "--json",
            str(report_path),
            "--quiet",
        ]
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert code == 1
    assert "failed" in (case(report, "T05")["error"] or "")


def test_requires_exactly_one_card_source(capsys):
    assert harness.main(["--testset", str(TESTSET)]) == 2
    assert (
        harness.main(["--testset", str(TESTSET), "--stub", str(BUNDLE), "--api-base", "http://x"])
        == 2
    )


def test_unreadable_testset_is_a_setup_error(tmp_path):
    assert harness.main(["--testset", str(tmp_path / "nope.jsonl"), "--stub", str(BUNDLE)]) == 2


def corpus_args(tmp_path, corpus_id):
    """Write validated synthetic records, never religious content."""
    from test_corpus_loader import metadata, record

    source, register = metadata("faq")
    corpus_path = tmp_path / "corpus.jsonl"
    corpus_path.write_text(json.dumps(record(corpus_id=corpus_id)) + "\n", encoding="utf-8")
    sources_path = tmp_path / "sources.json"
    sources_path.write_text(json.dumps({"sources": list(source.values())}), encoding="utf-8")
    register_path = tmp_path / "SOURCES.md"
    columns = ["Source id", "domain", "license", "license_url"]
    register_path.write_text(
        "| "
        + " | ".join(columns)
        + " |\n|---|---|---|---|\n"
        + "| "
        + " | ".join(register["faq"][column] for column in columns)
        + " |\n",
        encoding="utf-8",
    )
    return (
        "--corpus",
        str(corpus_path),
        "--sources",
        str(sources_path),
        "--register",
        str(register_path),
    )


@pytest.mark.parametrize(
    "availability,returned,status",
    [
        ("present", True, "pass"),
        ("present", False, "fail"),
        ("absent", True, "not_evaluated"),
        ("unavailable", True, "not_evaluated"),
    ],
)
def test_required_ids_use_validated_loaded_corpus(tmp_path, availability, returned, status):
    items = load_testset(countable_testset(tmp_path))
    items[0]["expect"]["required_corpus_ids"] = ["synthetic:e1"]
    path = write_testset(tmp_path / "required.jsonl", items)

    def patch(bundle):
        if not returned:
            overrides(bundle, "T01")["evidence"] = {"0": {"corpus_id": "synthetic:other"}}

    bundle = write_bundle(tmp_path / "required-bundle.json", patch)
    extra = (
        ()
        if availability == "unavailable"
        else corpus_args(
            tmp_path, "synthetic:e1" if availability == "present" else "synthetic:other"
        )
    )
    code, report = run(tmp_path, testset=path, bundle=bundle, extra=extra)
    assert assertion(report, "T01", "required_corpus_ids")["status"] == status
    assert case(report, "T01")["status"] == status
    assert gate(report, "G9")["status"] == ("pass" if status == "pass" else "fail")
    assert code == (0 if status == "pass" else 1)
    if status == "not_evaluated":
        assert case(report, "T01")["g9_countable"] is False
        assert case(report, "T01")["blocked_reason_en"]
        assert report["metrics"]["cases_executed"] == len(items) - 1
        assert report["metrics"]["cases_passing"] == len(items) - 1
        assert report["metrics"]["cases_not_evaluated"] == 1
    if availability != "unavailable":
        assert report["loaded_corpus"]["status"] == "validated"
        assert len(report["loaded_corpus"]["sha256"]) == 64


@pytest.mark.parametrize(
    "malformed",
    [
        None,
        {"claim": None},
        {"evidence": [None]},
        {"positions": [None]},
        {"claim": {"scripture_spans": [None]}},
    ],
)
def test_malformed_cards_report_g23_and_continue(tmp_path, malformed):
    def patch(bundle):
        bundle["cases"]["T01"]["cards"][0]["overrides"] = malformed

    bundle = write_bundle(tmp_path / "malformed.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    assert case(report, "T01")["status"] == "fail"
    assert assertion(report, "T01", "schema_valid")["status"] == "fail"
    assert gate(report, "G23")["status"] == "fail"
    assert "T01" in gate(report, "G23")["detail"]
    assert case(report, "T02")["status"] == "pass"
    assert len(report["cases"]) == len(records())
    assert report["metrics"]["cases_executed"] == len(records()) - 1
    assert harness.render_markdown(report)


@pytest.mark.parametrize("endpoint", ["extract", "check"])
@pytest.mark.parametrize("body", [None, [], "text", 42])
def test_http_non_object_bodies_report_client_error(tmp_path, monkeypatch, endpoint, body):
    from io import BytesIO

    def urlopen(request, **kwargs):
        payload = (
            body
            if request.full_url.endswith(endpoint)
            else {
                "claims": [{"id": "c1", "text_ar": "synthetic", "level": "A"}],
                "input_kind": "question",
            }
        )
        return BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    output = tmp_path / "http-error.json"
    code = harness.main(
        [
            "--api-base",
            "http://fixture.invalid",
            "--only",
            "T01,T02",
            "--json",
            str(output),
            "--quiet",
        ]
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert code == 1
    for case_id in ("T01", "T02"):
        assert case(report, case_id)["status"] == "fail"
        assert "non-object JSON body" in case(report, case_id)["error"]


def test_invalid_corpus_is_a_setup_error(tmp_path):
    args = corpus_args(tmp_path, "synthetic:e1")
    Path(args[1]).write_text('{"corpus_id":"synthetic:e1"}\n', encoding="utf-8")
    assert harness.main(["--stub", str(BUNDLE), *args, "--quiet"]) == 2


def test_malformed_pair_does_not_compare_null_observations_as_a_pass(tmp_path):
    def patch(bundle):
        for case_id in ("T09", "T13"):
            bundle["cases"][case_id]["cards"][0]["overrides"] = None

    bundle = write_bundle(tmp_path / "pair-malformed.json", patch)
    code, report = run(tmp_path, testset=countable_testset(tmp_path), bundle=bundle)
    assert code == 1
    for case_id in ("T09", "T13"):
        assert assertion(report, case_id, "pair_consistency")["status"] == "not_evaluated"
    assert case(report, "T18")["status"] == "pass"


def test_no_matching_evidence_consistency_reads_actual_card(tmp_path):
    items = load_testset(countable_testset(tmp_path))
    next(item for item in items if item["case_id"] == "T15")["expect"]["abstained_reason"] = (
        "NO_CHECKABLE_CLAIM"
    )
    path = write_testset(tmp_path / "actual-reason.jsonl", items)

    def patch(bundle):
        overrides(bundle, "T15")["evidence"] = [
            json.loads(
                (ROOT / "contracts/fixtures/supported-confirms.json").read_text(encoding="utf-8")
            )["evidence"][0]
        ]

    bundle = write_bundle(tmp_path / "actual-reason-bundle.json", patch)
    code, report = run(tmp_path, testset=path, bundle=bundle)
    assert code == 1
    assert assertion(report, "T15", "schema_valid")["status"] == "pass"
    assert assertion(report, "T15", "must_not_fabricate")["status"] == "fail"
