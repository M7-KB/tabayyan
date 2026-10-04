"""Test-set loading and record validation (SPEC.md section 4.3).

A record that breaks the section 4.3 shape is a load error, not a failing case:
an unreadable test set cannot produce an evaluation result. Coverage of the
twelve brief case ids is reported as gate G9 instead, so a missing id still
fails the run but does so with a report attached.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BRIEF_CASE_IDS: tuple[str, ...] = tuple(f"T{number:02d}" for number in range(1, 13))

RECORD_KEYS = frozenset(
    {
        "case_id",
        "origin",
        "category",
        "input",
        "expect",
        "rubric_en",
        "notes_en",
        "reviewed_by",
        "needs_sharia_review",
        "g9_countable",
        "blocked_reason_en",
        "paired_case_id",
    }
)
INPUT_KEYS = frozenset({"text", "lang", "kind"})
EXPECT_KEYS = frozenset(
    {
        "input_kind",
        "level",
        "state",
        "alignment",
        "abstained_reason",
        "state_label_key",
        "must_refer",
        "must_not_fabricate",
        "required_evidence_domains",
        "required_corpus_ids",
        "forbidden_substrings_ar",
        "forbidden_behaviors",
    }
)

ORIGINS = ("brief", "team")
CATEGORIES = ("safety", "redteam", "injection", "control")
INPUT_KINDS = ("claim", "question", "term")
INPUT_SOURCE_KINDS = ("text", "link", "audio", "image")
LEVELS = ("A", "B", "C", "D")
STATES = ("SUPPORTED", "DISPUTED", "CANNOT_CONFIRM")
ALIGNMENTS = ("CONFIRMS", "CONTRADICTS")
STATE_LABEL_KEYS = ("supported_confirms", "supported_contradicts", "disputed", "cannot_confirm")
ABSTAINED_REASONS = (
    "NO_MATCHING_EVIDENCE",
    "LOW_CONFIDENCE",
    "LEVEL_D_PERSONAL_CASE",
    "VERBATIM_GATE_FAILED",
    "CONFLICTING_EVIDENCE",
    "ALIGNMENT_UNDETERMINED",
    "NO_CHECKABLE_CLAIM",
)
STRING_LIST_KEYS = (
    "required_evidence_domains",
    "required_corpus_ids",
    "forbidden_substrings_ar",
    "forbidden_behaviors",
)


class TestsetError(Exception):
    """The test set cannot be loaded as a section 4.3 file."""


def _require(condition: object, where: str, message: str) -> None:
    if not condition:
        raise TestsetError(f"{where}: {message}")


def _validate_input(record: dict[str, Any], where: str) -> None:
    value = record["input"]
    _require(isinstance(value, dict), where, "input must be an object")
    _require(set(value) == INPUT_KEYS, where, f"input keys must be exactly {sorted(INPUT_KEYS)}")
    _require(
        isinstance(value["text"], str) and value["text"].strip(), where, "input.text must be text"
    )
    _require(value["lang"] in ("ar", "en"), where, "input.lang must be ar or en")
    _require(
        value["kind"] in INPUT_SOURCE_KINDS, where, f"input.kind must be in {INPUT_SOURCE_KINDS}"
    )


def _validate_expect(record: dict[str, Any], where: str) -> None:
    expect = record["expect"]
    _require(isinstance(expect, dict), where, "expect must be an object")
    _require(
        set(expect) == EXPECT_KEYS, where, f"expect keys must be exactly {sorted(EXPECT_KEYS)}"
    )
    _require(
        expect["input_kind"] in INPUT_KINDS, where, f"expect.input_kind must be in {INPUT_KINDS}"
    )
    _require(expect["level"] in LEVELS, where, f"expect.level must be in {LEVELS}")
    _require(expect["state"] in STATES, where, f"expect.state must be in {STATES}")

    supported = expect["state"] == "SUPPORTED"
    alignment = expect["alignment"]
    _require(
        (alignment is not None) == supported,
        where,
        "expect.alignment is non-null exactly when expect.state is SUPPORTED",
    )
    if supported:
        _require(alignment in ALIGNMENTS, where, f"expect.alignment must be in {ALIGNMENTS}")

    abstains = expect["state"] == "CANNOT_CONFIRM"
    reason = expect["abstained_reason"]
    _require(
        (reason is not None) == abstains,
        where,
        "expect.abstained_reason is non-null exactly when expect.state is CANNOT_CONFIRM",
    )
    if abstains:
        _require(
            reason in ABSTAINED_REASONS,
            where,
            f"expect.abstained_reason must be in {ABSTAINED_REASONS}",
        )

    _require(
        expect["state_label_key"] in STATE_LABEL_KEYS,
        where,
        f"expect.state_label_key must be in {STATE_LABEL_KEYS}",
    )
    for key in ("must_refer", "must_not_fabricate"):
        _require(isinstance(expect[key], bool), where, f"expect.{key} must be a boolean")
    for key in STRING_LIST_KEYS:
        values = expect[key]
        _require(isinstance(values, list), where, f"expect.{key} must be a list")
        _require(
            all(isinstance(item, str) and item.strip() for item in values),
            where,
            f"expect.{key} must hold non-empty strings",
        )


def validate_record(record: Any, where: str) -> None:
    """Validate one record against section 4.3, including the four review fields."""
    _require(isinstance(record, dict), where, "record must be an object")
    missing = sorted(RECORD_KEYS - set(record))
    extra = sorted(set(record) - RECORD_KEYS)
    _require(not missing, where, f"missing required fields: {missing}")
    _require(not extra, where, f"unknown fields are rejected: {extra}")
    _require(
        isinstance(record["case_id"], str) and record["case_id"].strip(),
        where,
        "case_id must be text",
    )
    _require(record["origin"] in ORIGINS, where, f"origin must be in {ORIGINS}")
    _require(record["category"] in CATEGORIES, where, f"category must be in {CATEGORIES}")
    for key in ("rubric_en", "notes_en"):
        _require(isinstance(record[key], str) and record[key].strip(), where, f"{key} must be text")
    _validate_input(record, where)
    _validate_expect(record, where)

    reviewed_by = record["reviewed_by"]
    _require(
        isinstance(reviewed_by, str) and reviewed_by.strip(), where, "reviewed_by must be text"
    )
    needs_review = record["needs_sharia_review"]
    _require(isinstance(needs_review, bool), where, "needs_sharia_review must be a boolean")
    _require(
        needs_review == (reviewed_by == "pending"),
        where,
        "needs_sharia_review is true exactly when reviewed_by is pending",
    )

    countable = record["g9_countable"]
    _require(isinstance(countable, bool), where, "g9_countable must be a boolean")
    blocked = record["blocked_reason_en"]
    if countable:
        _require(blocked is None, where, "blocked_reason_en must be null when g9_countable is true")
    else:
        _require(
            isinstance(blocked, str) and blocked.strip(),
            where,
            "blocked_reason_en must be a non-empty string when g9_countable is false",
        )

    paired = record["paired_case_id"]
    _require(
        paired is None or isinstance(paired, str), where, "paired_case_id must be text or null"
    )
    if isinstance(paired, str):
        _require(paired.strip(), where, "paired_case_id must not be blank")
        _require(paired != record["case_id"], where, "paired_case_id must not be a self-reference")


def validate_pairs(records: list[dict[str, Any]], where: str) -> None:
    """Both halves of a pair must exist and name each other (section 4.3)."""
    by_id = {record["case_id"]: record for record in records}
    for record in records:
        paired = record["paired_case_id"]
        if paired is None:
            continue
        target = by_id.get(paired)
        _require(
            target is not None,
            where,
            f"{record['case_id']} pairs with {paired}, which is not in the file",
        )
        _require(
            target is not None and target["paired_case_id"] == record["case_id"],
            where,
            f"{record['case_id']} pairs with {paired}, which does not name it back",
        )


def load_testset(path: Path) -> list[dict[str, Any]]:
    """Read and validate the test set. Raises TestsetError on any shape failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TestsetError(f"{path}: cannot read test set: {exc}") from exc

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{path}:{lineno}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TestsetError(f"{where}: invalid JSON: {exc}") from exc
        validate_record(record, where)
        _require(record["case_id"] not in seen, where, f"duplicate case_id {record['case_id']}")
        seen.add(record["case_id"])
        records.append(record)

    _require(records, str(path), "test set is empty")
    validate_pairs(records, str(path))
    return records


def missing_brief_case_ids(records: list[dict[str, Any]]) -> list[str]:
    """Brief case ids that are absent from the file, reported by G9."""
    present = {record["case_id"] for record in records if record["origin"] == "brief"}
    return [case_id for case_id in BRIEF_CASE_IDS if case_id not in present]


def excluded_brief_cases(records: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Brief case ids present but not countable, with their blocked reason (G9)."""
    return [
        (record["case_id"], record["blocked_reason_en"] or "")
        for record in records
        if record["origin"] == "brief" and not record["g9_countable"]
    ]
