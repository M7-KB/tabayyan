"""Publisher term/translation hybrid candidate index; no machine translation."""

from api.private_index_search import PrivateIndexMatcher


class GlossaryMatcher(PrivateIndexMatcher):
    source_id = "jamhara-glossary"

    @staticmethod
    def search_text(row: dict) -> str:
        return "\n".join([row["term_ar"], *row["translations"].values()])
