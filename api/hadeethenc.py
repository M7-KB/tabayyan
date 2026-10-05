"""HadeethEnc item adapter; source text and grade are copied from one response."""

import re

from api.gatekeeper import ReceivedResult, SourceRequest
from api.source_http import BoundedSourceHTTP, JsonSource, SourceUnavailable

SOURCE_NAME_AR = "موسوعة الأحاديث النبوية"


class HadeethEncConnector:
    def __init__(self, http: JsonSource | None = None):
        self.http = http or BoundedSourceHTTP()

    def receive(self, item_id: str, request: SourceRequest) -> ReceivedResult | None:
        """One item call, no retries, cache, model text or inferred grading.

        IDs must be selected by a source-backed discovery adapter, never treated
        as evidence on their own. This item adapter does not implement search.
        """
        if not isinstance(item_id, str) or not re.fullmatch(r"[1-9][0-9]{0,7}", item_id):
            return None
        try:
            raw = self.http.get(
                "hadeethenc.com", "/api/v1/hadeeths/one/", {"language": "ar", "id": item_id}
            )
        except SourceUnavailable:
            return None
        if not isinstance(raw, dict) or str(raw.get("id")) != item_id:
            return None
        limits = {"hadeeth": 12000, "grade": 1000, "attribution": 3000, "reference": 12000}
        if any(
            not isinstance(raw.get(k), str) or not raw[k].strip() or len(raw[k]) > limit
            for k, limit in limits.items()
        ):
            return None
        url = f"https://hadeethenc.com/ar/browse/hadith/{item_id}"
        return request.receive(
            {
                "source_id": "hadeethenc",
                "domain": "hadith",
                "record_ref": item_id,
                "source_url": url,
                "text_ar": raw["hadeeth"],
                "ref": {
                    "collection": SOURCE_NAME_AR,
                    "number": item_id,
                    "attribution": raw["attribution"],
                    "reference": raw["reference"],
                },
                "grading": {
                    "grading_source_id": "hadeethenc",
                    "grade_ar": raw["grade"],
                    "grader_ar": SOURCE_NAME_AR,
                    "grading_source_url": url,
                },
            }
        )
