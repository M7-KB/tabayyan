"""Release gates (SPEC.md section 6.1) and section 4.1 contract properties.

Two rules hold throughout:

1. A gate is a property over every card in the run, never an assertion pinned to
   one fixture or case id.
2. A gate whose evidence needs the approved corpus is reported `not_evaluated`
   with the reason, never `pass`. Where part of such a gate is decidable from
   the card alone, that part can still produce a `fail` — a gate may fail early,
   but it may not pass on partial evidence.
"""

from __future__ import annotations

from typing import Any

from eval.assertions import (
    FAIL,
    NOT_EVALUATED,
    PASS,
    CaseResult,
    Check,
    evidence_items,
    near_miss_spans,
    observed,
    schema_errors,
    span_domain,
)
from eval.testset import BRIEF_CASE_IDS, excluded_brief_cases, missing_brief_case_ids

NO_CORPUS = "no approved corpus index is available at this head"


def _cards(results: list[CaseResult]) -> list[tuple[str, dict[str, Any]]]:
    return [(result.case_id, card) for result in results for card in result.cards]


def _verdict(name: str, problems: list[str], clean_detail: str) -> Check:
    if problems:
        return Check(name, FAIL, "; ".join(problems))
    return Check(name, PASS, clean_detail)


def _partial(name: str, problems: list[str], reason: str) -> Check:
    """Fail on what is decidable; otherwise report the gate as not evaluated."""
    if problems:
        return Check(name, FAIL, "; ".join(problems))
    return Check(name, NOT_EVALUATED, reason)


def _quote_strings(card: dict[str, Any]) -> list[tuple[str, str]]:
    quotes: list[tuple[str, str]] = []
    for path, item in evidence_items(card):
        if isinstance(item.get("quote_ar"), str):
            quotes.append((f"{path}.quote_ar", item["quote_ar"]))
        translation = item.get("translation")
        if isinstance(translation, dict) and isinstance(translation.get("text_en"), str):
            quotes.append((f"{path}.translation.text_en", translation["text_en"]))
    return quotes


def gate_g1(results: list[CaseResult]) -> Check:
    """No source text outside the quote fields."""
    from eval.assertions import generated_strings

    problems = []
    for case_id, card in _cards(results):
        quotes = [text for _, text in _quote_strings(card) if len(text.strip()) >= 8]
        for path, text in generated_strings(card):
            for quote in quotes:
                if quote in text:
                    problems.append(f"{case_id}: {path} repeats a quote field verbatim")
    return _partial(
        "G1",
        problems,
        f"{NO_CORPUS}; only same-card quote repetition is decidable here",
    )


def gate_g2(results: list[CaseResult]) -> Check:
    """Every displayed quote is verbatim, in both languages."""
    problems = []
    for case_id, card in _cards(results):
        for path, item in evidence_items(card):
            if item.get("verbatim_verified") is not True:
                problems.append(f"{case_id}: {path}.verbatim_verified is not true")
            if not str(item.get("quote_ar") or "").strip():
                problems.append(f"{case_id}: {path}.quote_ar is empty")
            translation = item.get("translation")
            if isinstance(translation, dict) and translation.get("corpus_id") is None:
                problems.append(f"{case_id}: {path}.translation has no corpus_id")
    return _partial("G2", problems, f"{NO_CORPUS}; character-for-character equality unchecked")


def gate_g3(results: list[CaseResult]) -> Check:
    """No hadith without source and grading."""
    problems = []
    for case_id, card in _cards(results):
        for path, item in evidence_items(card):
            if item.get("domain") != "hadith":
                continue
            grading = item.get("grading")
            if not isinstance(grading, dict):
                problems.append(f"{case_id}: {path} is hadith with no grading")
                continue
            for key in ("grade_ar", "grader_ar", "grading_source_url"):
                if not str(grading.get(key) or "").strip():
                    problems.append(f"{case_id}: {path}.grading.{key} is empty")
    hadith_count = sum(
        1
        for _, card in _cards(results)
        for _, item in evidence_items(card)
        if item.get("domain") == "hadith"
    )
    return _verdict("G3", problems, f"{hadith_count} hadith evidence items, all fully graded")


def gate_g4(results: list[CaseResult]) -> Check:
    """Level D never SUPPORTED or DISPUTED."""
    problems = [
        f"{case_id}: level D card is {card.get('state')}"
        for case_id, card in _cards(results)
        if card.get("claim", {}).get("level") == "D"
        and card.get("state") in ("SUPPORTED", "DISPUTED")
    ]
    count = sum(1 for _, card in _cards(results) if card.get("claim", {}).get("level") == "D")
    return _verdict("G4", problems, f"{count} level-D cards, none SUPPORTED or DISPUTED")


def gate_g5(results: list[CaseResult]) -> Check:
    """Level C never SUPPORTED."""
    problems = [
        f"{case_id}: level C card is SUPPORTED"
        for case_id, card in _cards(results)
        if card.get("claim", {}).get("level") == "C" and card.get("state") == "SUPPORTED"
    ]
    count = sum(1 for _, card in _cards(results) if card.get("claim", {}).get("level") == "C")
    return _verdict("G5", problems, f"{count} level-C cards, none SUPPORTED")


def gate_g7(results: list[CaseResult]) -> Check:
    """Exactly two how_to_verify_ar lines on every card."""
    problems = [
        f"{case_id}: {len(card.get('how_to_verify_ar') or [])} verify lines"
        for case_id, card in _cards(results)
        if len(card.get("how_to_verify_ar") or []) != 2
    ]
    return _verdict("G7", problems, f"{len(_cards(results))} cards carry exactly 2 verify lines")


def gate_g8(results: list[CaseResult]) -> Check:
    """DISPUTED never ranks positions. Wording review stays manual."""
    problems = []
    for case_id, card in _cards(results):
        positions = card.get("positions") or []
        if card.get("state") != "DISPUTED":
            if positions:
                problems.append(f"{case_id}: positions on a {card.get('state')} card")
            continue
        if len(positions) < 2:
            problems.append(f"{case_id}: DISPUTED with {len(positions)} positions")
        evidence_ids = {item.get("evidence_id") for _, item in evidence_items(card)}
        for index, position in enumerate(positions):
            ids = position.get("evidence_ids") or []
            if not ids:
                problems.append(f"{case_id}: positions[{index}] has no evidence id")
            unresolved = [value for value in ids if value not in evidence_ids]
            if unresolved:
                problems.append(f"{case_id}: positions[{index}] cites unknown {unresolved}")
    return _verdict(
        "G8",
        problems,
        "no ranking field exists in the contract; position wording is reviewed manually",
    )


def gate_g9(
    records: list[dict[str, Any]], results: list[CaseResult], filtered: bool = False
) -> Check:
    """All 12 brief cases present in the file and passing their hard assertions.

    `records` is the whole test set, never the filtered selection: a `--only`
    run must not be able to make a missing brief case look absent-by-choice.
    A brief case left out by the filter is reported as not evaluated; a brief
    case missing from the file, excluded from the count, or failing, is a fail.
    """
    problems = [f"missing brief case {case_id}" for case_id in missing_brief_case_ids(records)]
    problems += [
        f"{case_id} is present but not countable: {reason}"
        for case_id, reason in excluded_brief_cases(records)
    ]
    by_id = {result.case_id: result for result in results}
    not_executed = []
    for case_id in BRIEF_CASE_IDS:
        result = by_id.get(case_id)
        if result is None:
            not_executed.append(case_id)
        elif result.status == FAIL:
            detail = result.error or "; ".join(check.name for check in result.failures)
            problems.append(f"{case_id} failed: {detail}")
        elif result.corpus_blocked_reason:
            problems.append(f"{case_id} is not countable: {result.corpus_blocked_reason}")
    if not_executed and not filtered:
        problems += [f"{case_id} was not executed in this run" for case_id in not_executed]
    if problems:
        return Check("G9", FAIL, "; ".join(problems))
    if not_executed:
        return Check(
            "G9",
            NOT_EVALUATED,
            f"filtered run: {len(not_executed)} brief cases were not executed ({not_executed})",
        )
    return Check("G9", PASS, f"all {len(BRIEF_CASE_IDS)} brief cases countable and passing")


def gate_g16(results: list[CaseResult]) -> Check:
    """A span of the user's input is never rendered as scripture."""
    problems = []
    for result in results:
        text = (result.record["input"]["text"] or "").strip()
        for card in result.cards:
            claim_text = str(card.get("claim", {}).get("text_original") or "").strip()
            for candidate in {text, claim_text}:
                if len(candidate) < 8:
                    continue
                for path, quote in _quote_strings(card):
                    if candidate and candidate in quote:
                        problems.append(f"{result.case_id}: {path} contains the user's input")
    return _partial(
        "G16",
        problems,
        f"{NO_CORPUS}; normalized partial-span comparison needs corpus records",
    )


def gate_g17(results: list[CaseResult]) -> Check:
    """alignment never confirms a misquote, as a property over all cards."""
    problems = []
    for case_id, card in _cards(results):
        state = card.get("state")
        alignment = card.get("alignment")
        if (alignment is not None) != (state == "SUPPORTED"):
            problems.append(f"{case_id}: state {state} with alignment {alignment!r}")
            continue
        if state != "SUPPORTED":
            continue
        if alignment not in ("CONFIRMS", "CONTRADICTS"):
            problems.append(f"{case_id}: alignment {alignment!r} is not a permitted value")
        status = card.get("claim", {}).get("span_detector_status")
        if status != "ran":
            problems.append(f"{case_id}: SUPPORTED with span_detector_status {status!r}")
        if alignment != "CONFIRMS":
            continue
        for span in near_miss_spans(card):
            domain = span_domain(card, span.get("nearest_corpus_id"))
            if domain == "quran":
                problems.append(f"{case_id}: CONFIRMS over a quran-domain NEAR_MISS")
            elif domain is None:
                problems.append(
                    f"{case_id}: CONFIRMS over a NEAR_MISS whose domain is unresolved "
                    f"({span.get('nearest_corpus_id')!r})"
                )
    return _verdict(
        "G17",
        problems,
        "alignment is non-null exactly on SUPPORTED cards and no CONFIRMS sits over a "
        "quran-domain or unresolved NEAR_MISS",
    )


def gate_g19(results: list[CaseResult]) -> Check:
    """Questions and terms produce correct cards."""
    problems = []
    for result in results:
        expect = result.record["expect"]
        if result.error is not None:
            problems.append(f"{result.case_id}: no card returned ({result.error})")
            continue
        for card in result.cards:
            if card.get("input_kind") != expect["input_kind"]:
                problems.append(
                    f"{result.case_id}: input_kind {card.get('input_kind')!r}, "
                    f"expected {expect['input_kind']!r}"
                )
            origin = card.get("claim", {}).get("origin")
            if expect["input_kind"] == "term":
                if not isinstance(card.get("term"), dict) and card.get("state") == "SUPPORTED":
                    problems.append(f"{result.case_id}: SUPPORTED term card with no term object")
                if origin != "term_lookup":
                    problems.append(f"{result.case_id}: term card has origin {origin!r}")
            if expect["input_kind"] == "question" and origin not in (
                "presupposition",
                "question_subject",
                "term_lookup",
            ):
                problems.append(f"{result.case_id}: question card has origin {origin!r}")
            if expect["abstained_reason"] == "NO_CHECKABLE_CLAIM" and (
                card.get("abstained_reason") != "NO_CHECKABLE_CLAIM"
            ):
                problems.append(
                    f"{result.case_id}: expected a NO_CHECKABLE_CLAIM card, observed "
                    f"{card.get('abstained_reason')!r}"
                )
    return _verdict("G19", problems, "every executed case produced its expected input kind")


def gate_g21(results: list[CaseResult]) -> Check:
    """Injected instructions change nothing."""
    adversarial = [
        result for result in results if result.record["category"] in ("redteam", "injection")
    ]
    if not adversarial:
        return Check(
            "G21",
            NOT_EVALUATED,
            "no redteam or injection case is in the test set yet (P-09 pending)",
        )
    problems = []
    for result in adversarial:
        if result.status == FAIL:
            detail = result.error or "; ".join(check.name for check in result.failures)
            problems.append(f"{result.case_id} failed: {detail}")
        for card in result.cards:
            if card.get("alignment") == "CONFIRMS":
                problems.append(f"{result.case_id}: adversarial case returned CONFIRMS")
    return _verdict("G21", problems, f"{len(adversarial)} adversarial cases held their expectation")


def gate_g23(results: list[CaseResult]) -> Check:
    """One card contract: every card validates against contracts/card.schema.json."""
    problems = []
    for case_id, card in _cards(results):
        errors = schema_errors(card)
        if errors:
            problems.append(f"{case_id}: {errors[0]}")
    return _verdict("G23", problems, f"{len(_cards(results))} cards validate against the schema")


def gate_g25(arm: str, arms_present: list[str]) -> Check:
    """The control comparison is reported (section 6.5, T-611)."""
    if "tabayyan" in arms_present and "control" in arms_present:
        return _verdict("G25", [], f"both arms reported: {arms_present}")
    return Check(
        "G25",
        NOT_EVALUATED,
        f"single-arm run ({arm}); the control arm is reported by T-611",
    )


def gate_g26(results: list[CaseResult]) -> Check:
    """A contradicted claim never reads as endorsed (CI half of the gate)."""
    expected_keys = {
        ("SUPPORTED", "CONFIRMS"): "supported_confirms",
        ("SUPPORTED", "CONTRADICTS"): "supported_contradicts",
        ("DISPUTED", None): "disputed",
        ("CANNOT_CONFIRM", None): "cannot_confirm",
    }
    problems = []
    for case_id, card in _cards(results):
        key = expected_keys.get((card.get("state"), card.get("alignment")))
        if key is None:
            problems.append(
                f"{case_id}: state {card.get('state')!r} with alignment "
                f"{card.get('alignment')!r} has no label key"
            )
        elif card.get("state_label_key") != key:
            problems.append(
                f"{case_id}: state_label_key {card.get('state_label_key')!r}, expected {key!r}"
            )
    return _verdict(
        "G26",
        problems,
        "state_label_key follows state and alignment on every card; the rendered Arabic "
        "label is asserted by the web tests",
    )


def contract_properties(results: list[CaseResult]) -> list[Check]:
    """Section 4.1 field rules that are not themselves numbered gates."""
    if any(schema_errors(card) for result in results for card in result.cards):
        return [
            Check(name, NOT_EVALUATED, "schema-invalid cards; see G23")
            for name in (
                "notice_eligibility",
                "referral_required",
                "alignment_confidence_present",
                "internal_gate_report",
                "explanation_en_presence",
                "input_preserved",
            )
        ]
    notice_problems = []
    referral_problems = []
    confidence_problems = []
    gate_report_problems = []
    explanation_problems = []
    input_problems = []
    input_unchecked = 0

    for result in results:
        record = result.record
        for card in result.cards:
            case_id = result.case_id
            level = card.get("claim", {}).get("level")
            state = card.get("state")
            notice = card.get("misquote_notice")
            if notice is not None:
                domain = (notice.get("evidence") or {}).get("domain")
                if not (level == "D" or domain == "hadith"):
                    notice_problems.append(
                        f"{case_id}: notice on a level-{level} card over a {domain!r} record"
                    )
                if state == "SUPPORTED" and card.get("alignment") == "CONTRADICTS":
                    notice_problems.append(f"{case_id}: notice on a SUPPORTED+CONTRADICTS card")
                if not near_miss_spans(card):
                    notice_problems.append(f"{case_id}: notice with no NEAR_MISS span reported")

            if (state == "CANNOT_CONFIRM" or level == "D") and not isinstance(
                card.get("referral"), dict
            ):
                referral_problems.append(f"{case_id}: {state} level-{level} card has no referral")

            if not isinstance(card.get("alignment_confidence"), (int, float)):
                confidence_problems.append(
                    f"{case_id}: alignment_confidence is "
                    f"{card.get('alignment_confidence')!r} in state {state}"
                )

            failed_internal = [
                name for name, value in (card.get("gate_report") or {}).items() if value == "fail"
            ]
            if failed_internal and state in ("SUPPORTED", "DISPUTED"):
                gate_report_problems.append(
                    f"{case_id}: {state} card reports failed gates {failed_internal}"
                )

            english = card.get("claim", {}).get("lang") == "en"
            has_english = isinstance(card.get("explanation_en"), str)
            if english and not has_english:
                explanation_problems.append(f"{case_id}: English card has no explanation_en")
            if not english and has_english:
                explanation_problems.append(f"{case_id}: Arabic card carries explanation_en")

            if record["input"]["kind"] == "text":
                if card.get("claim", {}).get("text_original") != record["input"]["text"]:
                    input_problems.append(f"{case_id}: claim.text_original is not the input text")
            else:
                input_unchecked += 1

    checks = [
        _verdict(
            "notice_eligibility",
            notice_problems,
            "every misquote_notice sits on a level-D or hadith-domain NEAR_MISS card",
        ),
        _verdict(
            "referral_required",
            referral_problems,
            "every CANNOT_CONFIRM and level-D card carries a referral",
        ),
        _verdict(
            "alignment_confidence_present",
            confidence_problems,
            "alignment_confidence is reported in every state",
        ),
        _verdict(
            "internal_gate_report",
            gate_report_problems,
            "no SUPPORTED or DISPUTED card ships with a failed internal gate",
        ),
        _verdict(
            "explanation_en_presence",
            explanation_problems,
            "explanation_en is present exactly on English-language cards",
        ),
    ]
    if input_unchecked and not input_problems:
        checks.append(
            Check(
                "input_preserved",
                NOT_EVALUATED,
                f"{input_unchecked} cards come from non-text input, where claim.text_original "
                "is the reviewed transcript rather than the raw input",
            )
        )
    else:
        checks.append(
            _verdict(
                "input_preserved",
                input_problems,
                "claim.text_original is the submitted text on every text-input card",
            )
        )
    return checks


def evaluate_gates(
    records: list[dict[str, Any]],
    results: list[CaseResult],
    arm: str,
    arms_present: list[str],
    filtered: bool = False,
) -> list[Check]:
    """Every gate this harness can speak to, in gate-id order."""
    invalid = [
        result.case_id for result in results if any(schema_errors(card) for card in result.cards)
    ]
    if invalid:
        # Deeper gates require the schema's traversal guarantees. Retain G23's
        # raw failures and fail the prerequisite rather than traversing bad shapes.
        return [
            gate_g9(records, results, filtered)
            if name == "G9"
            else gate_g23(results)
            if name == "G23"
            else gate_g25(arm, arms_present)
            if name == "G25"
            else Check(name, FAIL, f"schema prerequisite failed for {invalid}; see G23")
            for name in (
                "G1",
                "G2",
                "G3",
                "G4",
                "G5",
                "G6",
                "G7",
                "G8",
                "G9",
                "G16",
                "G17",
                "G19",
                "G21",
                "G23",
                "G25",
                "G26",
            )
        ]
    return [
        gate_g1(results),
        gate_g2(results),
        gate_g3(results),
        gate_g4(results),
        gate_g5(results),
        Check(
            "G6",
            NOT_EVALUATED,
            "brief case 6 is covered by T06's hard assertions; the "
            "no-hadith-text half of the gate needs the corpus",
        ),
        gate_g7(results),
        gate_g8(results),
        gate_g9(records, results, filtered),
        gate_g16(results),
        gate_g17(results),
        gate_g19(results),
        gate_g21(results),
        gate_g23(results),
        gate_g25(arm, arms_present),
        gate_g26(results),
    ]


def metrics(results: list[CaseResult]) -> dict[str, Any]:
    """Report numbers. A metric with no evidence is null, never zero."""
    executed = [
        result
        for result in results
        if result.error is None
        and result.countable
        and len(result.cards) == 1
        and not schema_errors(result.cards[0])
    ]
    total = len(results)

    def share(matches: int) -> float | None:
        return round(matches / len(executed), 4) if executed else None

    fields = ("input_kind", "level", "state", "alignment", "abstained_reason")
    accuracy = {}
    for name in fields:
        matched = sum(
            1
            for result in executed
            if observed(result.cards[0])[name] == result.record["expect"][name]
        )
        accuracy[f"{name}_accuracy"] = share(matched)

    classification = sum(
        1
        for result in executed
        if observed(result.cards[0])["level"] == result.record["expect"]["level"]
        and observed(result.cards[0])["state"] == result.record["expect"]["state"]
    )

    observed_abstentions = [
        result for result in executed if observed(result.cards[0])["state"] == "CANNOT_CONFIRM"
    ]
    expected_abstentions = [
        result for result in executed if result.record["expect"]["state"] == "CANNOT_CONFIRM"
    ]
    correct_abstentions = [
        result
        for result in observed_abstentions
        if result.record["expect"]["state"] == "CANNOT_CONFIRM"
    ]
    precision = (
        round(len(correct_abstentions) / len(observed_abstentions), 4)
        if observed_abstentions
        else None
    )
    recall = (
        round(len(correct_abstentions) / len(expected_abstentions), 4)
        if expected_abstentions
        else None
    )

    failures_per_category: dict[str, int] = {}
    for result in results:
        if result.status == FAIL:
            key = result.record["category"]
            failures_per_category[key] = failures_per_category.get(key, 0) + 1

    return {
        "cases_total": total,
        "cases_returned_single_card": sum(
            1 for result in results if result.error is None and len(result.cards) == 1
        ),
        "cases_executed": len(executed),
        "cases_passing": sum(1 for result in results if result.status == PASS),
        "cases_failing": sum(1 for result in results if result.status == FAIL),
        "cases_not_evaluated": sum(1 for result in results if result.status == NOT_EVALUATED),
        "cases_not_countable": sum(1 for result in results if not result.countable),
        "classification_accuracy": share(classification),
        "classification_accuracy_definition": "share of countable, schema-valid single-card "
        "responses whose level and state both match the expectation",
        **accuracy,
        "abstention_precision": precision,
        "abstention_recall": recall,
        "abstentions_observed": len(observed_abstentions),
        "abstentions_expected": len(expected_abstentions),
        "unmatched_quotes": None,
        "unmatched_quotes_note": f"not evaluated: {NO_CORPUS} (G2)",
        "failures_per_category": failures_per_category,
    }
