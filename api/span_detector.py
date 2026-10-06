"""Deterministic scripture matching; comparison keys never authorize displayed quotes."""

import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from api.config import TuningMetadata, load_config
from api.deadline import DeadlineExceeded, check_deadline

_VARIANTS = str.maketrans("أإآٱىة", "اااايه")
_MARK_RANGES = (
    (0x0610, 0x061A),
    (0x064B, 0x065F),
    (0x0670, 0x0670),
    (0x06D6, 0x06ED),
    (0x0898, 0x089F),
    (0x08CA, 0x08FF),
)


def comparison_key(text: str, *, fold_variants: bool = True) -> str:
    """Harden both triggers and the veto against Unicode retyping/insertion.

    NFKC expands presentation forms; Cf characters and Arabic marks are removed.
    Arabic-Indic decimal digits and Arabic letter variants are folded. This lossy
    comparison is independent of ar-v1 and retains no authority over source text.
    Set fold_variants=False to retain letter identity when checking a short,
    unmarked hit; mark and format normalization still applies.
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
    normalized = unicodedata.normalize("NFKC", "".join(chars))
    if fold_variants:
        normalized = normalized.translate(_VARIANTS)
    return " ".join(normalized.split())


def words(text: str, *, fold_variants: bool = True) -> tuple[str, ...]:
    """Unicode words; punctuation delimits words rather than changing word identity."""
    return tuple(re.findall(r"[^\W_]+", comparison_key(text, fold_variants=fold_variants)))


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
    # True when a marked span matched a window inside a longer record (an excerpt)
    # rather than the whole record. Window matching never runs for unmarked text.
    partial: bool = False


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


# Marked excerpts shorter than these token counts are not window-matched: exact
# excerpts need three tokens and near misses five, so a short common phrase cannot
# be flagged as a misquote against one of thousands of record windows.
EXCERPT_VERBATIM_MIN_TOKENS = 3
EXCERPT_NEAR_MIN_TOKENS = 5


class _Lookup:
    """Derived read-only search structures for one index tuple; never a second key."""

    def __init__(self, index: tuple):
        self.index = index
        self.exact: dict[tuple[str, ...], int] = {}
        self.lengths = tuple(len(target) for _, target in index)
        postings: dict[str, list[int]] = {}
        by_length: dict[int, list[int]] = {}
        for position, (_, target) in enumerate(index):
            self.exact.setdefault(target, position)
            by_length.setdefault(len(target), []).append(position)
            for token in set(target):
                postings.setdefault(token, []).append(position)
        self.postings = {token: tuple(found) for token, found in postings.items()}
        self.by_length = {length: tuple(found) for length, found in by_length.items()}


class SpanDetector:
    def __init__(
        self,
        records: Sequence[Record] | None,
        config: DetectorConfig,
        *,
        index: tuple[tuple[Record, tuple[str, ...]], ...] | None = None,
    ):
        self.config = config
        self.index = None
        self._lookup = None
        if index is not None:
            # Already tokenized (record, words) pairs from another detector built
            # with the same config; the tuple is immutable and safely shared.
            if records is not None:
                raise ValueError("pass records or index, not both")
            self.index = index
        elif records is not None:
            self.index = self._build(records, ())
        if self.index:
            self._lookup = _Lookup(self.index)

    @staticmethod
    def _build(records: Sequence[Record], existing: tuple) -> tuple:
        index = list(existing)
        ids = {record.corpus_id for record, _ in existing}
        for record in records:
            if record.domain not in {"quran", "hadith"}:
                continue
            tokens = words(record.text_ar)
            if not tokens or not record.corpus_id or record.corpus_id in ids:
                raise ValueError("invalid or duplicate scripture record")
            ids.add(record.corpus_id)
            index.append((record, tokens))
        return tuple(index)

    def extend(self, records: Sequence[Record]) -> "SpanDetector":
        """A detector over this index plus more records, tokenizing only the new ones."""
        if self.index is None:
            return SpanDetector(records, self.config)
        if not any(record.domain in {"quran", "hadith"} for record in records):
            return self
        return SpanDetector(None, self.config, index=self._build(records, self.index))

    def _lookup_for(self) -> _Lookup:
        # Rebuilt only when the index tuple itself is replaced.
        if self._lookup is None or self._lookup.index is not self.index:
            self._lookup = _Lookup(self.index)
        return self._lookup

    def classify(self, text: str, trigger: str = "A") -> Match:
        if trigger not in {"A", "B"}:
            raise ValueError("invalid trigger")
        tokens = words(text)
        match = self._classify(tokens, trigger)
        if trigger == "A" and match.classification == "UNRELATED":
            # A marked quotation may be an excerpt of a longer record. Compare it
            # with same-length windows of records that share enough of its tokens.
            excerpt = self._excerpt_match(tokens)
            if excerpt is not None:
                return excerpt
        return match

    def _excerpt_match(self, tokens: tuple[str, ...]) -> Match | None:
        """Match a marked span against windows inside longer records.

        An exact window anywhere in the index wins: a correctly quoted excerpt is
        never a misquote, even when another record holds a near twin. A near miss
        needs at least EXCERPT_NEAR_MIN_TOKENS tokens and the ordinary word budget
        for the span length, and reports the first best record in index order.
        Comparison equality only classifies; the composer still copies any
        displayed text from the loader-validated record by ID.
        """
        n = len(tokens)
        if not self.index or n < EXCERPT_VERBATIM_MIN_TOKENS:
            return None
        lookup = self._lookup_for()
        budget = self.config.budget(n) if n >= EXCERPT_NEAR_MIN_TOKENS else 0
        # A window within budget shares at least n - budget of the span's tokens.
        hits: Counter = Counter()
        for token in set(tokens):
            hits.update(lookup.postings.get(token, ()))
        needed = max(1, n - budget)
        best = None
        for position in sorted(p for p, h in hits.items() if h >= needed):
            record, target = lookup.index[position]
            if len(target) <= n + budget:
                continue  # The whole-record comparison already covered this record.
            for start in range(len(target) - n + 1):
                window = target[start : start + n]
                if window == tokens:
                    return Match("VERBATIM", record, 0, n, 0, partial=True)
                if budget and (best is None or best.distance > 1):
                    distance = word_distance(tokens, window)
                    if distance <= budget and (best is None or distance < best.distance):
                        best = Match("NEAR_MISS", record, distance, n, 0, partial=True)
        return best

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

    def _window_match(self, tokens: tuple[str, ...], lookup: _Lookup) -> Match | None:
        """Trigger-B classification of one window, or None when it is UNRELATED.

        Returns exactly what _classify(tokens, "B") returns whenever that result
        is VERBATIM or NEAR_MISS. Records that cannot reach the near-miss budget
        are skipped before any edit distance is computed: a near miss within
        budget b differs in length by at most b and keeps at least
        len(tokens) - b window tokens unchanged, so it shares at least
        (counted - b) of any counted window positions. Survivors are compared
        in index order, so ties resolve exactly as the full scan resolves them.
        """
        n = len(tokens)
        exact = lookup.exact.get(tokens)
        if exact is not None:
            return Match("VERBATIM", lookup.index[exact][0], 0, n, 0)
        config = self.config
        if n < config.trigger_b_min_window_tokens:
            return None
        budgets = {
            m: config.budget(max(n, m))
            for m in lookup.by_length
            if m >= config.trigger_b_min_window_tokens
        }
        budgets = {m: b for m, b in budgets.items() if abs(n - m) <= b}
        if not budgets:
            return None
        bound = max(budgets.values())
        # Count only the rarest distinct window tokens, with their multiplicity.
        rarest = sorted(set(tokens), key=lambda t: (len(lookup.postings.get(t, ())), t))
        counted = rarest[: max(bound + 1, 12)]
        needed = {m: sum(tokens.count(t) for t in counted) - b for m, b in budgets.items()}
        survivors = [p for m, need in needed.items() if need <= 0 for p in lookup.by_length[m]]
        positive = [need for need in needed.values() if need > 0]
        if positive:
            hits: Counter = Counter()
            for token in counted:
                for _ in range(tokens.count(token)):
                    hits.update(lookup.postings.get(token, ()))
            floor, lengths = min(positive), lookup.lengths
            survivors.extend(
                p for p, h in hits.items() if h >= floor and 0 < needed.get(lengths[p], 0) <= h
            )
        best = None
        for position in sorted(survivors):
            record, target = lookup.index[position]
            m = len(target)
            distance = word_distance(tokens, target)
            if distance > budgets[m]:
                continue
            match = Match("NEAR_MISS", record, distance, max(n, m), abs(n - m))
            if best is None or (distance, match.length_difference) < (
                best.distance,
                best.length_difference,
            ):
                best = match
        return best

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
        lookup = self._lookup_for()
        candidates = []
        for length in sorted(lengths):
            for i in range(len(tokens) - length + 1):
                check_deadline()
                window = tokens[i : i + length]
                start, end = window[0][1], window[-1][2]
                match = self._window_match(tuple(t[0] for t in window), lookup)
                if match is not None:
                    # A one-word hit has no surrounding scripture context. Letter
                    # folding alone must not turn ordinary prose (an interrogative,
                    # for example) into a quotation and an extra source dependency.
                    # Keep marks/format normalization, but require the same letters.
                    # Explicitly marked spans above retain the full safety scan.
                    if match.token_count == 1 and words(
                        text[start:end], fold_variants=False
                    ) != words(match.record.text_ar, fold_variants=False):
                        continue
                    candidates.append(Finding(start, end, None, match))
        verbatim = [f for f in findings + candidates if f.match.classification == "VERBATIM"]
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
        # Deduplicate only classified matches, never coarse UNRELATED marked spans.
        windows = [f for f in candidates if f.match.classification == "VERBATIM"] + selected
        windows = [
            f
            for f in windows
            if not any(
                m.start <= f.start
                and f.end <= m.end
                and m.match.classification == f.match.classification
                and m.match.record.corpus_id == f.match.record.corpus_id
                for m in findings
            )
        ]
        return tuple(sorted(findings + windows, key=lambda f: (f.start, f.end)))

    def detect(self, text: str, required_corpus_ids: Sequence[str] = ()) -> Detection:
        """Catch detector failures without logging or returning input/exception text."""
        if not self.index:
            return Detection("index_unavailable")
        if not set(required_corpus_ids) <= {r.corpus_id for r, _ in self.index}:
            return Detection("corpus_id_unresolved")
        try:
            return Detection("ran", self._scan(text))
        except DeadlineExceeded:
            # The request deadline passed; stop scanning and release the CPU.
            raise
        except TimeoutError:
            return Detection("timeout")
        except Exception:
            return Detection("error")
