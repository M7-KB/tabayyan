"""Original source text authorization for one request; no model-owned provenance."""

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

from api.span_detector import DetectorConfig, Record, SpanDetector
from corpus.normalize import normalize_arabic
from corpus.quran_binding import display_text, matching_text

_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[1] / "contracts/card.schema.json").read_text("utf-8")
)
_EVIDENCE = Draft202012Validator(
    {"$ref": "#/$defs/evidence", "$defs": _SCHEMA["$defs"]}, format_checker=FormatChecker()
)

# SPEC section 0.3. Unrecorded connector hosts stay disabled. This table is a
# provenance check, not an HTTP transport or permission to call a source.
SOURCES = {
    "bayyinat": ("bayenat.net", {"faq"}, "بينات"),
    "jamhara-glossary": ("islamic-content.com", {"glossary"}, "الجمهرة"),
    "dorar-hadith": ("dorar.net", {"hadith"}, "الدرر السنية"),
    "dorar-tafsir": ("dorar.net", {"tafsir"}, "الدرر السنية"),
    "dorar-aqeeda": ("dorar.net", {"aqeeda"}, "الدرر السنية"),
    "dorar-fiqh": ("dorar.net", {"fiqh"}, "الدرر السنية"),
    "dorar-history": ("dorar.net", {"seerah"}, "الدرر السنية"),
    "islamqa": ("islamqa.info", {"faq", "fiqh"}, "الإسلام سؤال وجواب"),
    "binbaz": ("binbaz.org.sa", {"faq", "fiqh"}, "موقع الشيخ ابن باز"),
    "binothaimeen": ("binothaimeen.net", {"faq", "fiqh"}, "موقع الشيخ ابن عثيمين"),
    "terminologyenc": ("mcp.islamiccontent.org", {"glossary"}, "الموسوعة الإسلامية للمصطلحات"),
    "hadeethenc": ("hadeethenc.com", {"hadith"}, "موسوعة الأحاديث النبوية"),
    "quranenc": ("mcp.islamiccontent.org", {"quran_translation"}, "موسوعة القرآن الكريم"),
    "byenah": ("mcp.islamiccontent.org", {"faq"}, "بينات"),
    "islamhouse": ("mcp.islamiccontent.org", {"faq"}, "الإسلام هاوس"),
    "islamenc": ("mcp.islamiccontent.org", {"faq"}, "الموسوعة الإسلامية"),
}

# The transport reaches only the MCP host. Its item links point to the original
# publisher, never to a model-selected fetch target.
MCP_PUBLISHER_HOSTS = {
    "islamhouse": {"islamcontent.com", "islamhouse.com"},
    "quranenc": {"islamenc.com", "quranenc.com"},
}


def allowed_url(url: object, host: str) -> bool:
    if not isinstance(url, str) or any(c.isspace() for c in url):
        return False
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname == host
            and parsed.port in {None, 443}
            and not parsed.username
            and not parsed.password
            and not parsed.fragment
        )
    except ValueError:
        return False


@dataclass(frozen=True)
class ReceivedResult:
    """Created by a connector adapter in its current SourceRequest, never a model."""

    request_token: object
    record: dict


class SourceRequest:
    """Request-local raw connector records. Never expose this to the HTTP caller.

    Connectors must enforce their outbound host/redirect/IP policy before calling
    receive. The mapping must be parsed raw source output, never an LLM summary.
    The token is an in-memory identity and is never serialized or given to a model.
    """

    def __init__(self):
        self._token = object()
        self._received: list[ReceivedResult] = []
        self._used = False

    def receive(self, record: dict) -> ReceivedResult:
        if self._used:
            raise ValueError("Source request already closed")
        result = ReceivedResult(self._token, copy.deepcopy(record))
        self._received.append(result)
        return result


class QuoteGatekeeper:
    def __init__(
        self,
        *,
        local_records: list[dict],
        request: SourceRequest,
        detector_config: DetectorConfig,
        received: list[ReceivedResult] | None = None,
    ):
        if request._used:
            raise ValueError("Source request already consumed")
        request._used = True
        self.config = detector_config
        self.local_records = copy.deepcopy(local_records)
        self._records = {}
        self._live = set()
        self._source_names = {}
        self._titles = {}
        self._local_available = False
        embedded_comparison = []
        for record in local_records:
            r = copy.deepcopy(record)
            # Local records must already have passed the private artifact loader.
            if (r.get("domain"), r.get("source_id")) not in {
                ("quran", "kfc-mushaf"),
                ("hadith", "sahih-bukhari"),
                ("hadith", "hadeethenc"),
            }:
                continue
            if r.get("domain") == "quran":
                self._local_available = True
            self._records[r["corpus_id"]] = r
            embedded_comparison.append(Record(r["corpus_id"], r["domain"], matching_text(r)))
            if display_text(r) != matching_text(r):
                # Display spelling is safety knowledge, never a second matching key.
                embedded_comparison.append(
                    Record("display:" + r["corpus_id"], r["domain"], display_text(r))
                )
        blocked = set()
        for item in request._received if received is None else received:
            if item.request_token is not request._token:
                continue
            r = copy.deepcopy(item.record)
            source = SOURCES.get(r.get("source_id"))
            if source is None or r.get("domain") not in source[1]:
                continue
            if not any(
                allowed_url(r.get("source_url"), host)
                for host in {source[0]} | MCP_PUBLISHER_HOSTS.get(r.get("source_id"), set())
            ):
                continue
            if not all(
                isinstance(r.get(k), str) and r[k].strip() for k in ("record_ref", "text_ar")
            ):
                continue
            if len(r["text_ar"]) > 12000 or not normalize_arabic(r["text_ar"]):
                continue
            key = "live:" + r["source_id"] + ":" + r["record_ref"]
            if r["domain"] == "hadith":
                # Distinct safety handles retain every conflicting version;
                # only the original handle can authorize display below.
                embedded_comparison.append(
                    Record(f"unsafe:{len(embedded_comparison)}:{key}", r["domain"], r["text_ar"])
                )
            if key in blocked:
                continue
            if key in self._records:
                # Conflicting duplicates cannot authorize either version.
                self._records.pop(key)
                self._live.discard(key)
                blocked.add(key)
                continue
            r["corpus_id"] = key  # Internal retrieval handle, never live provenance.
            r["text_normalized"] = normalize_arabic(r["text_ar"])
            r["source_name_ar"] = source[2]
            r["source_ref"] = {
                "source_id": r["source_id"],
                "record_ref": r["record_ref"],
                "url": r["source_url"],
            }
            self._records[key] = r
            self._source_names[key] = source[2]
            self._titles[key] = r.get("title_ar")
            self._live.add(key)
        # An exact twin changes the verdict even when it is never displayed.
        # Apply the same reference/grading authorization before it can veto a
        # near match. Keep every authorized local/current-request scripture row.
        comparison = [
            Record(k, r["domain"], matching_text(r))
            for k, r in self._records.items()
            if r["domain"] in {"quran", "hadith"} and self._base_quote(k, r["text_ar"]) is not None
        ]
        self._local_available = any(
            r.domain == "quran" and r.corpus_id not in self._live for r in comparison
        )
        self.detector = SpanDetector(comparison if self._local_available else None, detector_config)
        # Rejected scripture still supplies unsafe-span knowledge. This index
        # never decides claim alignment or authorizes an exact-match veto.
        self._embedded_detector = SpanDetector(
            embedded_comparison if self._local_available else None, detector_config
        )

    @property
    def records(self) -> list[dict]:
        return copy.deepcopy(list(self._records.values()))

    def _base_quote(self, key: str, candidate: str) -> dict | None:
        r = self._records.get(key)
        if r is None or not isinstance(candidate, str) or not candidate.strip():
            return None
        try:
            matching = matching_text(r)
            display = display_text(r)
        except (ValueError, UnicodeError):
            return None
        if candidate != display and normalize_arabic(candidate) != normalize_arabic(matching):
            return None
        if not all(
            isinstance(r.get(k), str) and r[k].strip() for k in ("source_name_ar", "source_url")
        ):
            return None
        if r["domain"] == "hadith":
            grade = r.get("grading")
            if not isinstance(grade, dict) or not all(
                isinstance(grade.get(k), str) and grade[k].strip()
                for k in ("grade_ar", "grader_ar", "grading_source_url")
            ):
                return None
            # Grading is from this record. No look-up in another result may fill it.
            try:
                host = urlsplit(grade["grading_source_url"]).hostname
            except ValueError:
                return None
            permitted = {s[0] for s in SOURCES.values()}
            if key in self._live and (
                host not in permitted or not allowed_url(grade["grading_source_url"], host)
            ):
                return None
        # Nested scripture must be displayable with its reference and grading,
        # not merely present in the detector index.
        try:
            projected = {
                "evidence_id": key,
                "domain": r["domain"],
                "source_id": r["source_id"],
                "source_name_ar": r["source_name_ar"],
                "source_url": r["source_url"],
                "quote_ar": display_text(r),
                "translation": None,
                "ref": r["ref"],
                "grading": {
                    k: r["grading"][k] for k in ("grade_ar", "grader_ar", "grading_source_url")
                }
                if r["domain"] == "hadith"
                else None,
                "verbatim_verified": True,
                "retrieval_score": 0,
            }
            if key in self._live:
                projected["source_ref"] = r["source_ref"]
            else:
                projected["corpus_id"] = key
            _EVIDENCE.validate(projected)
        except Exception:
            return None
        return copy.deepcopy(r)

    def scan_scripture(self, text: str):
        """Scan safety knowledge without authorizing display or alignment vetoes."""
        return self._embedded_detector.detect(text)

    def _embedded(self, text: str) -> list[dict] | None:
        """Require each detected scripture span to have its own authorized record."""
        try:
            detection = self.scan_scripture(text)
        except Exception:
            return None
        if detection.span_detector_status != "ran":
            return None
        dependencies = {}
        for finding in detection.findings:
            if finding.match.classification != "VERBATIM":
                return None
            key = finding.match.record.corpus_id
            if key.startswith("display:"):
                key = key.removeprefix("display:")
            if key.startswith("unsafe:"):
                key = key.split(":", 2)[2]
            r = self._base_quote(key, text[finding.start : finding.end])
            if r is None:
                return None
            dependencies[key] = r
        return list(dependencies.values())

    def verify(self, key: str, candidate: str) -> dict | None:
        """Normalized matching only locates; output is always the original source."""
        r = self._base_quote(key, candidate)
        if r is None:
            return None
        if r["domain"] not in {"quran", "hadith"} and self._embedded(r["text_ar"]) is None:
            return None
        return r

    def dependencies(self, key: str, candidate: str) -> list[dict]:
        r = self.verify(key, candidate)
        if r is None or r["domain"] == "quran":
            return []
        if r["domain"] == "hadith":
            # Preserve both publishers' own grades when this request received
            # the same narrated text. Neither result fills the other's fields.
            pair = {"hadeethenc", "dorar-hadith"}
            if key not in self._live or r["source_id"] not in pair:
                return []
            peers = []
            for peer_key, peer in self._records.items():
                if (
                    peer_key in self._live
                    and peer["domain"] == "hadith"
                    and peer["source_id"] in pair - {r["source_id"]}
                    and normalize_arabic(peer["text_ar"]) == normalize_arabic(r["text_ar"])
                ):
                    authorized = self._base_quote(peer_key, peer["text_ar"])
                    if authorized is not None:
                        peers.append(authorized)
            return peers
        return self._embedded(r["text_ar"]) or []

    def published_answer(self, key: str, candidate: str, *, proposed_title: str | None = None):
        r = self.verify(key, candidate)
        if r is None or key not in self._live or r["domain"] not in {"faq", "fiqh"}:
            return None
        title = self._titles[key]
        # A caller's proposed title is never used, even when it exists elsewhere.
        if (
            not isinstance(title, str)
            or not title.strip()
            or proposed_title is not None
            and proposed_title != title
        ):
            title = self._source_names[key]
        dependencies = self._embedded(title)
        if dependencies is None:
            title = self._source_names[key]
            dependencies = []
        excerpt_dependencies = self._embedded(r["text_ar"])
        if excerpt_dependencies is None:
            return None
        return (
            {
                "source_id": r["source_id"],
                "title_ar": title,
                "excerpt_ar": r["text_ar"],
                "url": r["source_url"],
            },
            dependencies + excerpt_dependencies,
        )
