"""Read a validated, approved local artifact; no fetching, ingesting or repairs."""

from pathlib import Path

from corpus.validate import ROOT, read_records, read_register, read_sources, validate_records


def load_corpus(
    path: Path = ROOT / "corpus/corpus.jsonl",
    *,
    sources_path: Path = ROOT / "corpus/approved_sources.json",
    register_path: Path = ROOT / "SOURCES.md",
) -> list[dict]:
    """Return all records only after all checks pass; pending review is never usable."""
    records = read_records(path)
    validate_records(records, read_sources(sources_path), read_register(register_path))
    return records
