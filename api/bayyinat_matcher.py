"""Bayyinat question-title and similar-phrasing hybrid candidate index."""

import re

from api.private_index_search import PrivateIndexMatcher


class BayyinatMatcher(PrivateIndexMatcher):
    source_id = "bayyinat"

    @staticmethod
    def search_text(row: dict) -> str:
        if "question_text" in row:
            # Detailed text aids retrieval but is never the display field.
            return "\n".join(
                [row["title"], row["question_text"], *row["keywords"], row["detailed_answer"]]
            )
        return "\n".join([row["title"], *row["similar_phrasings"]])

    @staticmethod
    def display_text(row: dict) -> str:
        if "question_text" not in row:
            return row["short_answer"]
        if row["summary"].strip():
            return row["summary"]
        return first_paragraph(row["detailed_answer"])


# Publisher section labels that can open the detailed answer (alone on a line, or as a
# "label:" prefix), and the sections after which the displayed excerpt never continues
# (the reference list, the index of cited verses). Markers match whole words only.
_SECTION_LABEL = re.compile(
    r"^(?:الجواب التفصيلي|الخلاصة|مضمون الشبهة|نص السؤال|الجواب)\s*[:：]?\s*"
)
_STOP_MARKERS = re.compile(
    r"(?:^|(?<=[\s:：،.؛()\-]))(?:المراجع|الآيات التي ورد\S*)(?=$|[\s:：،.؛()*\-])"
)
_SENTENCE_END = re.compile(r"[.!؟؛]")
_WHITESPACE = re.compile(r"\s")
EXCERPT_LIMIT = 400


def first_paragraph(detailed_answer: str, limit: int = EXCERPT_LIMIT) -> str:
    """The first paragraph of the publisher's detailed answer, as a display excerpt.

    Copies an original span only: a leading section label is skipped, the excerpt
    stops before the reference list or verse index, and the cap falls on a sentence
    end (or the last whitespace) inside the limit. No ellipsis or summary is added.
    """
    lines = [line.strip() for line in detailed_answer.replace("\r", "").split("\n")]
    while lines:
        if not lines[0]:
            lines.pop(0)
            continue
        stripped = _SECTION_LABEL.sub("", lines[0], count=1)
        if stripped == lines[0]:
            break
        lines[0] = stripped
    paragraph = []
    for line in lines:
        if not line and paragraph:
            break
        if line:
            paragraph.append(line)
    text = "\n".join(paragraph)
    stop = _STOP_MARKERS.search(text)
    if stop:
        text = text[: stop.start()].rstrip(" \n:،-")
    if len(text) > limit:
        head = text[:limit]
        ends = [m.end() for m in _SENTENCE_END.finditer(head)]
        spaces = [m.start() for m in _WHITESPACE.finditer(head)]
        if ends and ends[-1] >= limit // 4:
            cut = ends[-1]
        elif spaces and spaces[-1] > 0:
            cut = spaces[-1]
        else:
            cut = limit
        text = head[:cut]
    return text.strip()
