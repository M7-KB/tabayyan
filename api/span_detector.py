"""Deterministic scripture matching; comparison keys never authorize displayed quotes."""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from api.config import TuningMetadata, load_config

_VARIANTS = str.maketrans("أإآٱىة", "اااايه")
_MARK_RANGES = (
    (0x0610, 0x061A),
    (0x064B, 0x065F),
    (0x0670, 0x0670),
    (0x06D6, 0x06ED),
    (0x0898, 0x089F),
    (0x08CA, 0x08FF),
)


def comparison_key(text: str) -> str:
    """Harden both triggers and the veto against Unicode retyping/insertion.

    NFKC expands presentation forms; Cf characters and Arabic marks are removed.
    Arabic-Indic decimal digits and Arabic letter variants are folded. This lossy
    comparison is independent of ar-v1 and retains no authority over source text.
    """
    if not isinstance(text, str):
        raise TypeError("comparison_key expects a string")
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    text = unicodedata.normalize("NFKC", text)
    chars = []
    for char in text:
        code = ord(char)
        category = unicodedata.category(char)
        if category == "Cf" or char == "ـ":
            continue
        if category.startswith("M") and any(a <= code <= b for a, b in _MARK_RANGES):
            continue
        if 0x0660 <= code <= 0x0669 or 0x06F0 <= code <= 0x06F9:
            char = str(unicodedata.decimal(char))
        chars.append(char)
    return " ".join(unicodedata.normalize("NFKC", "".join(chars)).translate(_VARIANTS).split())


def words(text: str) -> tuple[str, ...]:
    """Unicode words; punctuation delimits words rather than changing word identity."""
    return tuple(re.findall(r"[^\W_]+", comparison_key(text)))


def word_distance(left: Sequence[str], right: Sequence[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(previous[j] + 1, current[-1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class Record:
    """Adapter input from the approved loader, not a replacement for corpus validation."""

    corpus_id: str
    domain: str
    text_ar: str


@dataclass(frozen=True)
class DetectorConfig:
    quote_pairs: tuple[tuple[str, str, str], ...]
    formulas: tuple[str, ...]
    budgets: tuple[tuple[int, int], ...]
    final_budget: int
    trigger_b_min_window_tokens: int

    @classmethod
    def from_mappings(cls, policy: Mapping, tuning: Mapping):
        validated = TuningMetadata.model_validate(tuning)
        ceiling = policy["alignment"]["word_budget_ceiling"]
        if type(ceiling) is not int or ceiling < 1:
            raise ValueError("invalid word_budget_ceiling")
        if any(b > ceiling for b in validated.word_budget_table.values()):
            raise ValueError("word budget exceeds policy ceiling")
        markers = policy["scripture_span_markers"]
        pairs = []
        ornate = markers["ornate_brackets"]
        if len(ornate) != 2:
            raise ValueError("ornate brackets require two delimiters")
        # RTL ornate glyph order varies by serialization; recognize both directions.
        pairs.extend((a, b, "ornate_brackets") for a, b in (ornate, ornate[::-1]))
        asymmetric = []
        for mark in markers["quote_marks"]:
            if unicodedata.category(mark) == "Po":
                pairs.append((mark, mark, "quote_marks"))
            else:
                asymmetric.append(mark)
        if len(asymmetric) % 2:
            raise ValueError("quotation delimiters must be paired")
        pairs.extend(
            (asymmetric[i], asymmetric[i + 1], "quote_marks") for i in range(0, len(asymmetric), 2)
        )
        formulas = tuple(markers["attribution_allah"] + markers["attribution_prophet"])
        if any(not isinstance(m, str) or not m for p in pairs for m in p[:2]):
            raise ValueError("invalid delimiter")
        if any(not isinstance(f, str) or not words(f) for f in formulas):
            raise ValueError("invalid attribution formula")
        if not pairs or not formulas:
            raise ValueError("missing scripture markers")
        table = validated.word_budget_table
        return cls(
            tuple(pairs),
            formulas,
            tuple(sorted((int(k), v) for k, v in table.items() if k != "else")),
            table["else"],
            validated.trigger_b_min_window_tokens,
        )

    @classmethod
    def from_files(cls, policy_path: Path, tuning_path: Path):
        load_config(policy_path, tuning_path)
        return cls.from_mappings(
            yaml.safe_load(policy_path.read_text("utf-8")),
            yaml.safe_load(tuning_path.read_text("utf-8")),
        )

    def budget(self, length: int) -> int:
        return next((v for bound, v in self.budgets if length <= bound), self.final_budget)


@dataclass(frozen=True)
class Match:
    classification: str
    record: Record
    distance: int
    token_count: int
    length_difference: int


@dataclass(frozen=True)
class Finding:
    start: int
    end: int
    marker: str | None
    match: Match

    def card_span(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "marker": self.marker,
            "nearest_corpus_id": self.match.record.corpus_id,
            "normalized_distance": self.match.distance / max(1, self.match.token_count),
            "classification": self.match.classification,
        }


@dataclass(frozen=True)
class Detection:
    span_detector_status: str
    findings: tuple[Finding, ...] = ()

    def effects(self, level: str, note_ar: str) -> dict:
        """Expose inputs for the composer ratchet, never a model-generated verdict.

        Notice text comes only from an indexed record. The composer must retrieve
        its source/grading and apply original-text/provenance gates before display.
        """
        near = [f for f in self.findings if f.match.classification == "NEAR_MISS"]
        force = level != "D" and any(f.match.record.domain == "quran" for f in near)
        notice = None
        if near and not force:
            record = near[0].match.record
            notice = {"corpus_id": record.corpus_id, "quote_ar": record.text_ar, "note_ar": note_ar}
        return {"force_quran_contradicts": force, "misquote_notice": notice}


class SpanDetector:
    def __init__(self, records: Sequence[Record] | None, config: DetectorConfig):
        self.config = config
        self.index = None
        if records is not None:
            index = []
            ids = set()
            for record in records:
                if record.domain not in {"quran", "hadith"}:
                    continue
                tokens = words(record.text_ar)
                if not tokens or not record.corpus_id or record.corpus_id in ids:
                    raise ValueError("invalid or duplicate scripture record")
                ids.add(record.corpus_id)
                index.append((record, tokens))
            self.index = tuple(index)

    def classify(self, text: str, trigger: str = "A") -> Match:
        if trigger not in {"A", "B"}:
            raise ValueError("invalid trigger")
        return self._classify(words(text), trigger)

    def _classify(self, tokens: tuple[str, ...], trigger: str) -> Match:
        if not self.index:
            raise LookupError("scripture index unavailable")
        # Whole-index equality is checked before ANY candidate's near-miss budget.
        for record, target in self.index:
            if tokens == target:
                return Match("VERBATIM", record, 0, len(tokens), 0)
        candidates = []
        for record, target in self.index:
            distance = word_distance(tokens, target)
            length = max(len(tokens), len(target))
            eligible = trigger == "A" or min(len(tokens), len(target)) >= (
                self.config.trigger_b_min_window_tokens
            )
            near = bool(tokens) and eligible and distance <= self.config.budget(length)
            candidates.append(
                Match(
                    "NEAR_MISS" if near else "UNRELATED",
                    record,
                    distance,
                    length,
                    abs(len(tokens) - len(target)),
                )
            )
        # Eligible near matches precede ineligible short records at equal distance.
        return min(
            candidates,
            key=lambda m: (m.classification != "NEAR_MISS", m.distance, m.length_difference),
        )

    @staticmethod
    def _tokens(text: str) -> list[tuple[str, int, int]]:
        # Keep character provenance through compatibility expansion and mark removal.
        # Several words expanded from one ligature may share its original span.
        output = []
        for chunk in re.finditer(r"\S+", text):
            raw = chunk.group()
            transformed = ""
            offsets = []
            i = 0
            while i < len(raw):
                end = i + 1
                while end < len(raw) and (
                    unicodedata.category(raw[end]).startswith("M")
                    or unicodedata.category(raw[end]) == "Cf"
                ):
                    end += 1
                value = comparison_key(raw[i:end])
                transformed += value
                offsets.extend([(chunk.start() + i, chunk.start() + end)] * len(value))
                i = end
            output.extend(
                (m.group(), offsets[m.start()][0], offsets[m.end() - 1][1])
                for m in re.finditer(r"[^\W_]+", transformed)
            )
        return output

    def _marked(self, text: str) -> list[tuple[int, int, str]]:
        spans = []
        for opening, closing, marker in self.config.quote_pairs:
            pattern = re.escape(opening) + r"(.*?)" + re.escape(closing)
            spans.extend(
                (m.start(1), m.end(1), marker) for m in re.finditer(pattern, text, re.DOTALL)
            )
        tokens = self._tokens(text)
        # Longest formulas win when one configured formula prefixes another.
        formulas = sorted((words(f) for f in self.config.formulas), key=len, reverse=True)
        used = set()
        for i in range(len(tokens)):
            for formula in formulas:
                if i in used or tuple(t[0] for t in tokens[i : i + len(formula)]) != formula:
                    continue
                used.add(i)
                start = tokens[i + len(formula) - 1][2]
                following = [s for s in spans if s[0] >= start and not text[start : s[0]].strip()]
                # Delimiters may intervene before the quoted body.
                if not following:
                    following = [
                        s for s in spans if s[0] >= start and not words(text[start : s[0]])
                    ]
                if following:
                    continue  # Already represented by the explicit quote marker.
                boundary = re.search(r"[\n.!?؟؛]", text[start:])
                end = start + boundary.start() if boundary else len(text)
                while start < end and (text[start].isspace() or text[start] in ":،"):
                    start += 1
                if start < end:
                    spans.append((start, end, "attribution_formula"))
                break
        return sorted(set(spans))

    def _scan(self, text: str) -> tuple[Finding, ...]:
        marked = self._marked(text)
        findings = [Finding(a, b, m, self.classify(text[a:b])) for a, b, m in marked]
        tokens = self._tokens(text)
        lengths = {
            length
            for _, target in self.index
            for length in range(max(1, len(target) - 2), len(target) + 3)
        }
        candidates = []
        for length in sorted(lengths):
            for i in range(len(tokens) - length + 1):
                window = tokens[i : i + length]
                start, end = window[0][1], window[-1][2]
                if any(start < b and end > a for a, b, _ in marked):
                    continue
                match = self._classify(tuple(t[0] for t in window), "B")
                if match.classification != "UNRELATED":
                    candidates.append(Finding(start, end, None, match))
        verbatim = [f for f in candidates if f.match.classification == "VERBATIM"]
        target_lengths = {record.corpus_id: len(target) for record, target in self.index}
        # Do not reclassify cropped/extended windows inside a known correct quote.
        near = [
            f
            for f in candidates
            if f.match.classification == "NEAR_MISS"
            and not any(
                f.start < v.end
                and f.end > v.start
                and target_lengths[v.match.record.corpus_id]
                >= target_lengths[f.match.record.corpus_id]
                for v in verbatim
            )
        ]
        selected = []
        for finding in sorted(near, key=lambda f: (f.match.distance, f.match.length_difference)):
            if not any(finding.start < f.end and finding.end > f.start for f in selected):
                selected.append(finding)
        return tuple(sorted(findings + verbatim + selected, key=lambda f: (f.start, f.end)))

    def detect(self, text: str, required_corpus_ids: Sequence[str] = ()) -> Detection:
        """Catch detector failures without logging or returning input/exception text."""
        if not self.index:
            return Detection("index_unavailable")
        if not set(required_corpus_ids) <= {r.corpus_id for r, _ in self.index}:
            return Detection("corpus_id_unresolved")
        try:
            return Detection("ran", self._scan(text))
        except TimeoutError:
            return Detection("timeout")
        except Exception:
            return Detection("error")
