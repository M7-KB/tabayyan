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
        # Copy an original span; do not summarize or append generated ellipses.
        return re.split(r"\r?\n[ \t]*\r?\n", row["detailed_answer"], maxsplit=1)[0][:400]
