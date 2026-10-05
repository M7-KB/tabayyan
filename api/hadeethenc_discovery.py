"""Bounded source-metadata discovery; titles and category IDs are not evidence."""

import re

from api.gatekeeper import ReceivedResult, SourceRequest
from api.hadeethenc import HadeethEncConnector
from api.source_http import BoundedSourceHTTP, JsonSource, SourceUnavailable
from corpus.normalize import normalize_arabic


def _id(value):
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,7}", value) is not None


def _tokens(text):
    return set(normalize_arabic(text).split())


class HadeethEncDiscovery:
    """One category list, one page of 20 items, at most two full item calls.

    No guessed IDs, pagination loop, retry, cache, persistence or semantic-search
    claim. Limited lexical coverage may miss relevant evidence and must abstain.
    Callers run this only for non-personal hadith retrieval, before closing scope.
    """

    def __init__(self, http: JsonSource | None = None):
        self.http = http or BoundedSourceHTTP()
        self.items = HadeethEncConnector(self.http)

    def discover(self, query: str, request: SourceRequest) -> list[ReceivedResult]:
        if not isinstance(query, str) or not query.strip() or len(query) > 12000:
            return []
        if request._used:
            return []
        tokens = _tokens(query)
        if not tokens:
            return []
        try:
            categories = self.http.get(
                "hadeethenc.com", "/api/v1/categories/list/", {"language": "ar"}
            )
            if not isinstance(categories, list) or not 1 <= len(categories) <= 1000:
                return []
            candidates = self._rank(categories, tokens)
            if not candidates:
                return []
            page = self.http.get(
                "hadeethenc.com",
                "/api/v1/hadeeths/list/",
                {"language": "ar", "category_id": candidates[0], "page": "1", "per_page": "20"},
            )
            if not isinstance(page, dict) or not isinstance(page.get("data"), list):
                return []
            if len(page["data"]) > 20:
                return []
            selected = self._rank(page["data"], tokens)[:2]
        except SourceUnavailable:
            return []
        received = []
        for item_id in selected:
            receipt = self.items.receive(item_id, request)
            if receipt is not None:
                received.append(receipt)
        return received

    @staticmethod
    def _rank(rows, tokens):
        ranked = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or not _id(row.get("id")):
                return []
            title = row.get("title")
            if not isinstance(title, str) or not title.strip() or len(title) > 12000:
                return []
            if row["id"] in seen:
                return []
            seen.add(row["id"])
            score = len(tokens & _tokens(title))
            if score:
                ranked.append((-score, int(row["id"]), row["id"]))
        return [row[2] for row in sorted(ranked)]
