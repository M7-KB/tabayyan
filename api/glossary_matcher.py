"""Publisher term/translation hybrid candidate index; no machine translation."""

from api.private_index_search import PrivateIndexMatcher


class GlossaryMatcher(PrivateIndexMatcher):
    source_id = "jamhara-glossary"

    @staticmethod
    def search_text(row: dict) -> str:
        if "terminological_meaning" in row:
            return "\n".join([row["term_ar"], row["short_explanation"], *row["translations"]])
        return "\n".join([row["term_ar"], *row["translations"].values()])

    @staticmethod
    def display_text(row: dict) -> str:
        return (
            row["terminological_meaning"]
            if "terminological_meaning" in row
            else row["definition_short"]
        )
