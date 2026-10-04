"""Read a validated, approved local artifact; no fetching, ingesting or repairs."""

from pathlib import Path

from corpus.validate import ROOT, read_records, read_register, read_sources, validate_records


def load_corpus(
    path: Path = ROOT / "corpus/corpus.jsonl",
    *,
    sources_path: Path = ROOT / "corpus/approved_sources.json",
    register_path: Path = ROOT / "SOURCES.md",
    allow_pending_review: bool = False,
    require_redistribution: bool = True,
) -> list[dict]:
    """Return all records only after checks pass, with explicit review/use modes."""
    records = read_records(path)
    validate_records(
        records,
        read_sources(sources_path),
        read_register(register_path),
        allow_pending_review=allow_pending_review,
        require_redistribution=require_redistribution,
    )
    return records
