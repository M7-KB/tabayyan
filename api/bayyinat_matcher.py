"""Bayyinat question-title and similar-phrasing hybrid candidate index."""

from api.private_index_search import PrivateIndexMatcher


class BayyinatMatcher(PrivateIndexMatcher):
    source_id = "bayyinat"

    @staticmethod
    def search_text(row: dict) -> str:
        return "\n".join([row["title"], *row["similar_phrasings"]])
