"""Hard assertions per case, and the card properties the gates share.

Hard assertions are the machine-checked list of SPEC.md section 4.3. Soft
assertions (`rubric_en`, `forbidden_behaviors`) are carried into the report for
review and are never turned into a pass here.

Everything in this module is structural: it reads the card, not the corpus. A
claim that needs a corpus record to settle, such as verbatim equality (G2) or
user-span isolation (G16), is reported as not evaluated rather than as a pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CARD_SCHEMA_PATH = ROOT / "contracts" / "card.schema.json"

PASS = "pass"
FAIL = "fail"
NOT_EVALUATED = "not_evaluated"

HARD_ASSERTIONS: tuple[str, ...] = (
    "card_count",
    "schema_valid",
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
)

PAIR_COMPARED_FIELDS: tuple[str, ...] = (
    "input_kind",
    "level",
    "state",
    "alignment",
    "abstained_reason",
)

# Generated fields: section 4.1 forbids quoted source text here, and the
# forbidden-substring assertion of section 4.3 is scanned over exactly these.
# Claim fields are deliberately excluded: they hold the user's own words, so an
# echo of the input is not a generated fabrication.
GENERATED_FIELD_PATHS: tuple[str, ...] = (
    "explanation_ar",
    "explanation_en",
    "positions[].label_ar",
    "positions[].summary_ar",
    "how_to_verify_ar[]",
    "term.term_ar",
    "term.term_en",
    "referral.body_name_ar",
    "referral.fallback_line_ar",
    "referral.ready_to_ask_question_ar",
    "misquote_notice.note_ar",
)


@dataclass(frozen=True)
class Check:
    """One named result. `detail` always says what was observed."""

    name: str
    status: str
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.status == FAIL


@dataclass
class CaseResult:
    """One executed case: the record, what came back, and every check."""

    record: dict[str, Any]
    cards: list[dict[str, Any]]
    error: str | None = None
    checks: list[Check] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def case_id(self) -> str:
        return self.record["case_id"]

    @property
    def failures(self) -> list[Check]:
        return [check for check in self.checks if check.failed]

    @property
    def status(self) -> str:
        if self.error is not None or self.failures:
            return FAIL
        return PASS


@lru_cache(maxsize=1)
def card_validator():
    """Draft 2020-12 validator for contracts/card.schema.json (G23)."""
    from jsonschema import Draft202012Validator, FormatChecker

    schema = json.loads(CARD_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


def schema_errors(card: Any) -> list[str]:
    validator = card_validator()
    return [
        f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(card), key=lambda error: list(error.path))
    ]


def generated_strings(card: dict[str, Any]) -> list[tuple[str, str]]:
    """Every generated string on the card, with its field path."""
    found: list[tuple[str, str]] = []

    def add(path: str, value: Any) -> None:
        if isinstance(value, str):
            found.append((path, value))

    add("explanation_ar", card.get("explanation_ar"))
    add("explanation_en", card.get("explanation_en"))
    for index, position in enumerate(card.get("positions") or []):
        add(f"positions[{index}].label_ar", position.get("label_ar"))
        add(f"positions[{index}].summary_ar", position.get("summary_ar"))
    for index, line in enumerate(card.get("how_to_verify_ar") or []):
        add(f"how_to_verify_ar[{index}]", line)
    for name in ("term_ar", "term_en"):
        add(f"term.{name}", (card.get("term") or {}).get(name))
    for name in ("body_name_ar", "fallback_line_ar", "ready_to_ask_question_ar"):
        add(f"referral.{name}", (card.get("referral") or {}).get(name))
    add("misquote_notice.note_ar", (card.get("misquote_notice") or {}).get("note_ar"))
    return found


def evidence_items(card: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Evidence items from `evidence[]` and from `misquote_notice.evidence`."""
    items: list[tuple[str, dict[str, Any]]] = [
        (f"evidence[{index}]", item) for index, item in enumerate(card.get("evidence") or [])
    ]
    notice = card.get("misquote_notice")
    if isinstance(notice, dict) and isinstance(notice.get("evidence"), dict):
        items.append(("misquote_notice.evidence", notice["evidence"]))
    return items


def corpus_domains(card: dict[str, Any]) -> dict[str, str]:
    """corpus_id to domain, as stated by the card's own evidence items."""
    return {
        item.get("corpus_id"): item.get("domain")
        for _, item in evidence_items(card)
        if isinstance(item.get("corpus_id"), str) and isinstance(item.get("domain"), str)
    }


def span_domain(card: dict[str, Any], corpus_id: Any) -> str | None:
    """Resolve a span's nearest_corpus_id to a domain, or None if unresolved.

    Resolution uses the card's own evidence items first, then a `<domain>:` id
    prefix. An unresolved id is never treated as a non-Qur'an domain: G17 fails
    closed on it, because an unresolvable near-miss could be a Qur'an record.
    """
    if not isinstance(corpus_id, str) or not corpus_id:
        return None
    stated = corpus_domains(card).get(corpus_id)
    if stated:
        return stated
    prefix = corpus_id.split(":", 1)[0]
    known = {
        "quran",
        "hadith",
        "tafsir",
        "aqeeda",
        "fiqh",
        "seerah",
        "glossary",
        "faq",
        "quran_translation",
    }
    return prefix if prefix in known else None


def near_miss_spans(card: dict[str, Any]) -> list[dict[str, Any]]:
    spans = card.get("claim", {}).get("scripture_spans") or []
    return [span for span in spans if span.get("classification") == "NEAR_MISS"]


def observed(card: dict[str, Any] | None) -> dict[str, Any]:
    """The five fields a pair comparison and the report both read."""
    if card is None:
        return dict.fromkeys(PAIR_COMPARED_FIELDS)
    return {
        "input_kind": card.get("input_kind"),
        "level": card.get("claim", {}).get("level"),
        "state": card.get("state"),
        "alignment": card.get("alignment"),
        "abstained_reason": card.get("abstained_reason"),
    }


def _equality(name: str, expected: Any, actual: Any) -> Check:
    if expected == actual:
        return Check(name, PASS, f"expected {expected!r}, observed {actual!r}")
    return Check(name, FAIL, f"expected {expected!r}, observed {actual!r}")


def _check_must_refer(expect: dict[str, Any], card: dict[str, Any]) -> Check:
    referral = card.get("referral")
    if not expect["must_refer"]:
        return Check("must_refer", PASS, "not required by the case")
    if not isinstance(referral, dict):
        return Check("must_refer", FAIL, "referral is missing")
    missing = [
        field
        for field in ("body_name_ar", "body_url", "ready_to_ask_question_ar")
        if not str(referral.get(field) or "").strip()
    ]
    if missing:
        return Check("must_refer", FAIL, f"referral is incomplete: {missing}")
    return Check("must_refer", PASS, "referral present with a ready-to-ask question")


def _check_must_not_fabricate(expect: dict[str, Any], card: dict[str, Any]) -> Check:
    """The structural half of must_not_fabricate. Verbatim equality is G2."""
    if not expect["must_not_fabricate"]:
        return Check("must_not_fabricate", PASS, "not required by the case")

    problems: list[str] = []
    for path, item in evidence_items(card):
        for name in ("corpus_id", "source_id", "source_url"):
            if not str(item.get(name) or "").strip():
                problems.append(f"{path}.{name} is empty")
        if item.get("verbatim_verified") is not True:
            problems.append(f"{path}.verbatim_verified is not true")
        if item.get("domain") == "hadith":
            grading = item.get("grading")
            if not isinstance(grading, dict):
                problems.append(f"{path} is hadith with no grading")
            else:
                for name in ("grade_ar", "grader_ar", "grading_source_url"):
                    if not str(grading.get(name) or "").strip():
                        problems.append(f"{path}.grading.{name} is empty")

    # A card that reports no matching evidence cannot also display evidence.
    if expect["abstained_reason"] == "NO_MATCHING_EVIDENCE" and (card.get("evidence") or []):
        problems.append("NO_MATCHING_EVIDENCE card returned evidence items")

    if problems:
        return Check("must_not_fabricate", FAIL, "; ".join(problems))
    return Check(
        "must_not_fabricate",
        PASS,
        "provenance and grading complete on every evidence item; verbatim equality is G2",
    )


def _check_required_domains(expect: dict[str, Any], card: dict[str, Any]) -> Check:
    required = expect["required_evidence_domains"]
    present = [item.get("domain") for _, item in evidence_items(card)]
    missing = [domain for domain in required if domain not in present]
    if missing:
        return Check(
            "required_evidence_domains",
            FAIL,
            f"required {required}, observed {present}, missing {missing}",
        )
    return Check("required_evidence_domains", PASS, f"required {required}, observed {present}")


def _check_required_corpus_ids(expect: dict[str, Any], card: dict[str, Any]) -> Check:
    required = expect["required_corpus_ids"]
    present = [item.get("corpus_id") for _, item in evidence_items(card)]
    missing = [corpus_id for corpus_id in required if corpus_id not in present]
    if missing:
        return Check(
            "required_corpus_ids",
            FAIL,
            f"required {required}, observed {present}, missing {missing}",
        )
    return Check("required_corpus_ids", PASS, f"required {required}, observed {present}")


def _check_forbidden_substrings(expect: dict[str, Any], card: dict[str, Any]) -> Check:
    forbidden = expect["forbidden_substrings_ar"]
    if not forbidden:
        return Check("forbidden_substrings_ar", PASS, "no forbidden substrings for this case")
    hits = [
        f"{path} contains {needle!r}"
        for path, text in generated_strings(card)
        for needle in forbidden
        if needle in text
    ]
    if hits:
        return Check("forbidden_substrings_ar", FAIL, "; ".join(hits))
    return Check(
        "forbidden_substrings_ar",
        PASS,
        f"{len(forbidden)} substrings absent from generated fields",
    )


def assert_case(record: dict[str, Any], cards: list[dict[str, Any]]) -> list[Check]:
    """Run the hard assertions of section 4.3 for one case."""
    expect = record["expect"]
    if len(cards) != 1:
        detail = f"expected exactly 1 card for this case, observed {len(cards)}"
        return [Check("card_count", FAIL, detail)] + [
            Check(name, NOT_EVALUATED, "no single card to assert against")
            for name in HARD_ASSERTIONS
            if name != "card_count"
        ]

    card = cards[0]
    checks = [Check("card_count", PASS, "exactly 1 card")]

    errors = schema_errors(card)
    if errors:
        checks.append(Check("schema_valid", FAIL, "; ".join(errors[:5])))
    else:
        checks.append(Check("schema_valid", PASS, "validates against contracts/card.schema.json"))

    actual = observed(card)
    checks.append(_equality("input_kind", expect["input_kind"], actual["input_kind"]))
    checks.append(_equality("level", expect["level"], actual["level"]))
    checks.append(_equality("state", expect["state"], actual["state"]))
    checks.append(_equality("alignment", expect["alignment"], actual["alignment"]))
    checks.append(
        _equality("abstained_reason", expect["abstained_reason"], actual["abstained_reason"])
    )
    checks.append(
        _equality("state_label_key", expect["state_label_key"], card.get("state_label_key"))
    )
    checks.append(_check_must_refer(expect, card))
    checks.append(_check_must_not_fabricate(expect, card))
    checks.append(_check_required_domains(expect, card))
    checks.append(_check_required_corpus_ids(expect, card))
    checks.append(_check_forbidden_substrings(expect, card))
    return checks


def assert_pair(
    record: dict[str, Any],
    cards: list[dict[str, Any]],
    partner_record: dict[str, Any] | None,
    partner_cards: list[dict[str, Any]] | None,
) -> Check:
    """Compare a paired case against its twin on the five section 4.3 fields."""
    paired = record["paired_case_id"]
    if paired is None:
        return Check("pair_consistency", PASS, "unpaired case")
    if partner_record is None or partner_cards is None:
        return Check(
            "pair_consistency",
            FAIL,
            f"pair partner {paired} was not executed in this run",
        )
    if len(cards) != 1 or len(partner_cards) != 1:
        return Check(
            "pair_consistency",
            FAIL,
            f"{record['case_id']} and {paired} must each return exactly 1 card",
        )
    mine = observed(cards[0])
    theirs = observed(partner_cards[0])
    differences = [
        f"{field}: {record['case_id']}={mine[field]!r} vs {paired}={theirs[field]!r}"
        for field in PAIR_COMPARED_FIELDS
        if mine[field] != theirs[field]
    ]
    if differences:
        return Check("pair_consistency", FAIL, "; ".join(differences))
    return Check("pair_consistency", PASS, f"matches {paired} on {list(PAIR_COMPARED_FIELDS)}")
