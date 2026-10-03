"""Eval harness entry point (T-407).

    python -m eval.run --stub eval/stubs/contract_pass.json
    python -m eval.run --api-base https://tabayyan-api.example --arm tabayyan

Reads `eval/testset.jsonl`, obtains cards for every case from one card source,
validates each card against `contracts/card.schema.json`, runs the hard
assertions of SPEC.md section 4.3 per case, then evaluates the release gates of
section 6.1 as properties over every card in the run.

Exit codes: 0 all checks pass, 1 at least one case, gate or contract property
failed, 2 the run could not be set up (test set unreadable, no card source).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.assertions import (
    CARD_SCHEMA_PATH,
    FAIL,
    HARD_ASSERTIONS,
    NOT_EVALUATED,
    PASS,
    CaseResult,
    Check,
    assert_case,
    assert_pair,
    observed,
)
from eval.clients import HttpApiClient, StubClient
from eval.gates import contract_properties, evaluate_gates, metrics
from eval.testset import TestsetError, load_testset

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TESTSET = ROOT / "eval" / "testset.jsonl"
HARNESS_VERSION = "1"
ARMS = ("tabayyan", "control")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_records(records: list[dict[str, Any]], only: list[str] | None) -> list[dict[str, Any]]:
    """Keep the requested case ids, plus the pair partner of anything requested.

    A pair comparison is a hard assertion, so a filtered run must not be able to
    drop one half of a pair and report the other as passing.
    """
    if not only:
        return records
    wanted = set(only)
    by_id = {record["case_id"]: record for record in records}
    unknown = sorted(wanted - set(by_id))
    if unknown:
        raise TestsetError(f"unknown case ids requested: {unknown}")
    for case_id in list(wanted):
        paired = by_id[case_id]["paired_case_id"]
        if paired:
            wanted.add(paired)
    return [record for record in records if record["case_id"] in wanted]


def run_cases(records: list[dict[str, Any]], client: Any) -> list[CaseResult]:
    results: list[CaseResult] = []
    for record in records:
        response = client.cards_for(record)
        if response.error is not None:
            checks = [Check("response", FAIL, response.error)]
            checks += [
                Check(name, NOT_EVALUATED, "no response to assert against")
                for name in HARD_ASSERTIONS
            ]
            results.append(CaseResult(record=record, cards=[], error=response.error, checks=checks))
            continue
        checks = [Check("response", PASS, f"{len(response.cards)} card(s) returned")]
        checks += assert_case(record, response.cards)
        results.append(
            CaseResult(
                record=record, cards=list(response.cards), checks=checks, meta=dict(response.meta)
            )
        )

    by_id = {result.case_id: result for result in results}
    for result in results:
        paired = result.record["paired_case_id"]
        partner = by_id.get(paired) if paired else None
        result.checks.append(
            assert_pair(
                result.record,
                result.cards,
                partner.record if partner else None,
                partner.cards if partner else None,
            )
        )
    return results


def build_report(
    records: list[dict[str, Any]],
    results: list[CaseResult],
    arm: str,
    client_name: str,
    testset_path: Path,
    selected: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """`records` is the whole test set; `selected` is what this run executed."""
    executed = selected if selected is not None else records
    filtered = len(executed) != len(records)
    gates = evaluate_gates(records, results, arm, [arm], filtered)
    properties = contract_properties(results)
    cases = [
        {
            "case_id": result.case_id,
            "origin": result.record["origin"],
            "category": result.record["category"],
            "g9_countable": result.record["g9_countable"],
            "blocked_reason_en": result.record["blocked_reason_en"],
            "paired_case_id": result.record["paired_case_id"],
            "reviewed_by": result.record["reviewed_by"],
            "status": result.status,
            "error": result.error,
            "expected": {
                name: result.record["expect"][name]
                for name in ("input_kind", "level", "state", "alignment", "abstained_reason")
            },
            "observed": observed(result.cards[0] if len(result.cards) == 1 else None),
            "assertions": [
                {"name": check.name, "status": check.status, "detail": check.detail}
                for check in result.checks
            ],
            "soft_review": {
                "rubric_en": result.record["rubric_en"],
                "forbidden_behaviors": result.record["expect"]["forbidden_behaviors"],
                "status": "awaiting manual review",
            },
            "meta": result.meta,
        }
        for result in results
    ]
    failing_checks = [check for result in results for check in result.failures]
    failing_checks += [check for check in gates + properties if check.failed]
    return {
        "harness_version": HARNESS_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "arm": arm,
        "card_source": client_name,
        "testset": {
            "path": str(testset_path.relative_to(ROOT))
            if testset_path.is_relative_to(ROOT)
            else str(testset_path),
            "records": len(records),
            "executed": len(executed),
            "sha256": _sha256(testset_path),
        },
        "card_schema": {
            "path": str(CARD_SCHEMA_PATH.relative_to(ROOT)),
            "sha256": _sha256(CARD_SCHEMA_PATH),
        },
        "metrics": metrics(results),
        "cases": cases,
        "gates": [
            {"id": check.name, "status": check.status, "detail": check.detail} for check in gates
        ],
        "contract_properties": [
            {"name": check.name, "status": check.status, "detail": check.detail}
            for check in properties
        ],
        "outcome": FAIL if failing_checks else PASS,
    }


def _status_mark(status: str) -> str:
    return {PASS: "pass", FAIL: "FAIL", NOT_EVALUATED: "not evaluated"}.get(status, status)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Eval run — arm `{report['arm']}` — {report['outcome'].upper()}",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Card source: `{report['card_source']}`",
        f"- Test set: `{report['testset']['path']}` "
        f"({report['testset']['records']} records, sha256 `{report['testset']['sha256'][:12]}`)",
        f"- Card schema: `{report['card_schema']['path']}` "
        f"(sha256 `{report['card_schema']['sha256'][:12]}`)",
        f"- Harness version: {report['harness_version']}",
        "",
        "## Metrics",
        "",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Cases",
        "",
        "| Case | Origin | Category | Status | Expected | Observed |",
        "|---|---|---|---|---|---|",
    ]
    for case in report["cases"]:
        expected = "/".join(str(case["expected"][key]) for key in ("level", "state", "alignment"))
        seen = "/".join(str(case["observed"][key]) for key in ("level", "state", "alignment"))
        lines.append(
            f"| {case['case_id']} | {case['origin']} | {case['category']} | "
            f"{_status_mark(case['status'])} | {expected} | {seen} |"
        )
    lines += ["", "## Hard assertions per case", ""]
    for case in report["cases"]:
        lines.append(f"### {case['case_id']} — {_status_mark(case['status'])}")
        if case["error"]:
            lines.append(f"- response error: {case['error']}")
        for assertion in case["assertions"]:
            lines.append(
                f"- {assertion['name']}: {_status_mark(assertion['status'])}"
                f"{' — ' + assertion['detail'] if assertion['detail'] else ''}"
            )
        lines.append(
            f"- soft review (not a pass): {case['soft_review']['status']}; "
            f"forbidden_behaviors {case['soft_review']['forbidden_behaviors']}"
        )
        lines.append("")
    lines += ["## Gates", "", "| Gate | Status | Detail |", "|---|---|---|"]
    for gate in report["gates"]:
        lines.append(f"| {gate['id']} | {_status_mark(gate['status'])} | {gate['detail']} |")
    lines += [
        "",
        "## Card contract properties (section 4.1)",
        "",
        "| Property | Status | Detail |",
        "|---|---|---|",
    ]
    for item in report["contract_properties"]:
        lines.append(f"| {item['name']} | {_status_mark(item['status'])} | {item['detail']} |")
    not_evaluated = [
        item["id"] if "id" in item else item["name"]
        for item in report["gates"] + report["contract_properties"]
        if item["status"] == NOT_EVALUATED
    ]
    lines += [
        "",
        "## Scope of this run",
        "",
        f"- Not evaluated here: {', '.join(not_evaluated) if not_evaluated else 'none'}. "
        "A not-evaluated gate is not a pass and this run is not a release sign-off.",
        "- Soft assertions (`rubric_en`, `forbidden_behaviors`) are listed for manual review "
        "and are never counted as passes.",
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="eval.run", description=__doc__)
    parser.add_argument("--testset", type=Path, default=DEFAULT_TESTSET)
    parser.add_argument("--stub", type=Path, help="stub bundle of card overrides")
    parser.add_argument("--api-base", help="base URL of a running API")
    parser.add_argument("--fixtures-dir", type=Path, help="card fixtures the stub builds on")
    parser.add_argument("--arm", choices=ARMS, default="tabayyan")
    parser.add_argument("--only", help="comma-separated case ids; pair partners are added")
    parser.add_argument("--json", dest="json_out", type=Path, help="write the JSON report here")
    parser.add_argument(
        "--markdown", dest="markdown_out", type=Path, help="write the Markdown report here"
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--quiet", action="store_true", help="print only the outcome line")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if bool(args.stub) == bool(args.api_base):
        print("error: pass exactly one of --stub or --api-base", file=sys.stderr)
        return 2

    try:
        records = load_testset(args.testset)
        selected = select_records(records, args.only.split(",") if args.only else None)
    except TestsetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.stub:
        try:
            client: Any = StubClient(args.stub, args.fixtures_dir)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read stub bundle: {exc}", file=sys.stderr)
            return 2
    else:
        client = HttpApiClient(args.api_base, timeout=args.timeout)

    results = run_cases(selected, client)
    report = build_report(records, results, args.arm, client.name, args.testset, selected)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    markdown = render_markdown(report)
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")
    if not args.quiet:
        print(markdown)
    else:
        print(f"{report['arm']}: {report['outcome']}")
    return 0 if report["outcome"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
