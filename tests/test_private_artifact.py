"""Synthetic engineering fixtures only; no private data, source excerpts or keys."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_corpus_loader import graded_hadith, metadata, record

from api.main import create_app
from api.settings import Settings
from corpus.check_public_tree import is_private_artifact
from corpus.check_public_tree import main as check_public_tree
from corpus.private_artifact import load_private_corpus
from corpus.validate import CorpusValidationError, read_register, read_sources, validate_records


@pytest.fixture
def private_files(tmp_path):
    item, sources, register = graded_hadith()
    item["approved_by"] = "pending"
    for source in sources.values():
        source["redistribution_allowed"] = False
        source["public_display_allowed"] = True
    corpus = tmp_path / "private-name.jsonl"
    manifest = tmp_path / "manifest.json"
    source_path = tmp_path / "sources.json"
    source_path.write_text(json.dumps({"sources": list(sources.values())}), encoding="utf-8")
    register_path = tmp_path / "SOURCES.md"
    register_path.write_text(
        "| Source id | domain | license | license_url |\n|---|---|---|---|\n"
        + "".join(
            f"| {key} | {row['domain']} | {row['license']} | {row['license_url']} |\n"
            for key, row in register.items()
        ),
        encoding="utf-8",
    )

    def write(items=None):
        corpus.write_bytes(
            (
                "\r\n".join(json.dumps(row, ensure_ascii=False) for row in items or [item]) + "\r\n"
            ).encode("utf-8")
        )
        manifest.write_text(
            json.dumps(
                {
                    "sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
                    "corpus_version": "test-v1",
                }
            ),
            encoding="utf-8",
        )

    write()
    return item, sources, corpus, manifest, source_path, register_path, write


def load(files, **kwargs):
    _, _, corpus, manifest, sources, register, _ = files
    return load_private_corpus(
        corpus, manifest, sources_path=sources, register_path=register, **kwargs
    )


def test_private_use_preserves_pending_text_and_file_bytes(private_files):
    item, _, corpus, _, _, _, _ = private_files
    before = corpus.read_bytes()
    with pytest.raises(CorpusValidationError):
        load(private_files)
    records, version = load(private_files, allow_pending_review=True)
    assert records == [item]
    assert version == "test-v1"
    assert records[0]["approved_by"] == "pending"
    assert corpus.read_bytes() == before


def test_public_distribution_still_rejects_private_collection_and_grader(private_files):
    item, sources, _, _, _, register, _ = private_files
    item["approved_by"] = "sharia-reviewer-1"
    rows = read_register(register)
    with pytest.raises(CorpusValidationError, match="rule 2"):
        validate_records([item], sources, rows)
    sources["dorar-hadith"]["redistribution_allowed"] = True
    with pytest.raises(CorpusValidationError, match="rule 5"):
        validate_records([item], sources, rows)
    validate_records([item], sources, rows, require_redistribution=False)


@pytest.mark.parametrize("source_id", ["hadith", "dorar-hadith"])
@pytest.mark.parametrize(
    "field,value", [("license_status", "pending"), ("ingestion_allowed", False)]
)
def test_pending_private_mode_never_waives_collection_or_grading_licence(
    private_files, source_id, field, value
):
    _, sources, _, _, source_path, _, _ = private_files
    sources[source_id][field] = value
    source_path.write_text(json.dumps({"sources": list(sources.values())}), encoding="utf-8")
    with pytest.raises(CorpusValidationError):
        load(private_files, allow_pending_review=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("approved_by", "someone-else"),
        ("approved_by", ""),
        ("checksum_sha256", "0" * 64),
        ("text_normalized", "edited"),
        ("grading", None),
        ("source_url", "https://unregistered.invalid/item"),
        ("license", "unknown"),
    ],
)
def test_one_invalid_row_blocks_entire_artifact(private_files, field, value):
    item, _, _, _, _, _, write = private_files
    bad = dict(item, corpus_id="fixture:bad")
    bad[field] = value
    write([item, bad])
    with pytest.raises(CorpusValidationError):
        load(private_files, allow_pending_review=True)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_file",
        "missing_manifest",
        "invalid_json",
        "bad_hash",
        "changed_bytes",
        "empty",
        "bad_encoding",
        "extra_field",
        "duplicate_key",
        "oversize",
        "bad_version",
        "directory",
    ],
)
def test_bad_artifacts_fail_without_private_diagnostics(private_files, mutation, monkeypatch):
    _, _, corpus, manifest, _, _, _ = private_files
    data = json.loads(manifest.read_text("utf-8"))
    if mutation == "missing_file":
        corpus.unlink()
    elif mutation == "directory":
        corpus.unlink()
        corpus.mkdir()
    elif mutation == "missing_manifest":
        manifest.unlink()
    elif mutation == "invalid_json":
        manifest.write_text("private-source-text: {broken", encoding="utf-8")
    elif mutation == "bad_hash":
        data["sha256"] = "wrong"
    elif mutation == "changed_bytes":
        corpus.write_bytes(corpus.read_bytes().replace(b"\r\n", b"\n"))
    elif mutation in {"empty", "bad_encoding"}:
        corpus.write_bytes(b"" if mutation == "empty" else b"\xff")
        data["sha256"] = hashlib.sha256(corpus.read_bytes()).hexdigest()
    elif mutation == "extra_field":
        data["url"] = "private-source-text"
    elif mutation == "duplicate_key":
        manifest.write_text('{"sha256":"a","sha256":"b"}', encoding="utf-8")
    elif mutation == "oversize":
        monkeypatch.setattr("corpus.private_artifact.MAX_ARTIFACT_BYTES", 1)
    elif mutation == "bad_version":
        data["corpus_version"] = "private-source-text\n"
    if mutation in {"bad_hash", "empty", "bad_encoding", "extra_field", "bad_version"}:
        manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CorpusValidationError) as caught:
        load(private_files, allow_pending_review=True)
    assert "private-name" not in str(caught.value)
    assert "private-source-text" not in str(caught.value)
    assert not isinstance(caught.value.__cause__, json.JSONDecodeError)


@pytest.mark.parametrize("flag", [False, True])
def test_app_publishes_only_fully_validated_corpus(private_files, monkeypatch, flag):
    _, _, corpus, manifest, source_path, register, _ = private_files

    def actual_loader(path, manifest_path, *, allow_pending_review):
        return load_private_corpus(
            path,
            manifest_path,
            allow_pending_review=allow_pending_review,
            sources_path=source_path,
            register_path=register,
        )

    monkeypatch.setattr("api.main.load_private_corpus", actual_loader)
    app = create_app(
        Settings(
            openai_api_key="inert-test-value",
            private_corpus_path=corpus,
            corpus_manifest_path=manifest,
            allow_pending_review=flag,
        )
    )
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["allow_pending_review"] is flag
        assert health["corpus_items"] == (1 if flag else 0)
        assert health["corpus_version"] == ("test-v1" if flag else None)
        assert health["corpus_status"] == ("loaded" if flag else "unavailable")
        assert health["pending_review_items"] == (1 if flag else 0)
        assert health["policy_approved_by"] == "pending"
        assert health["status"] == "degraded"  # Pipeline endpoints are still unimplemented.
        assert len(app.state.corpus) == health["corpus_items"]
        if flag:
            assert app.state.corpus[0]["approved_by"] == "pending"
        corpus.write_bytes(b"private-source-text")
    # A fresh startup cannot reuse a prior successfully loaded artifact.
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["corpus_items"] == 0
        assert health["corpus_status"] == "unavailable"
        assert health["corpus_error"] == "Private corpus checksum mismatch"
        assert app.state.corpus == []


@pytest.mark.parametrize("flag", [False, True])
def test_health_only_never_reads_private_artifact(tmp_path, monkeypatch, flag):
    def forbidden(*args, **kwargs):
        pytest.fail("Health-only must never read the private corpus")

    monkeypatch.setattr("api.main.load_private_corpus", forbidden)
    app = create_app(
        Settings(
            health_only=True,
            private_corpus_path=tmp_path / "absent.jsonl",
            allow_pending_review=flag,
        )
    )
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["allow_pending_review"] is flag
        assert health["corpus_items"] == 0
        assert health["corpus_version"] is None


def test_flag_default_off_and_environment_opt_in(monkeypatch):
    monkeypatch.delenv("ALLOW_PENDING_REVIEW", raising=False)
    assert Settings().allow_pending_review is False
    monkeypatch.setenv("ALLOW_PENDING_REVIEW", "true")
    assert Settings().allow_pending_review is True
    monkeypatch.setenv("PRIVATE_CORPUS_PATH", "/etc/secrets/corpus.jsonl")
    assert Settings().private_corpus_path == Path("/etc/secrets/corpus.jsonl")


def test_owner_clearance_is_scoped_to_three_sources():
    sources = read_sources(Path("corpus/approved_sources.json"))
    register = read_register(Path("SOURCES.md"))
    cleared = {"kfc-mushaf", "sahih-bukhari", "dorar-hadith"}
    for key, source in sources.items():
        assert source["redistribution_allowed"] is False
        assert source["approved_by"] == "pending"
        assert source["ingestion_allowed"] is (key in cleared)
        assert source["license_status"] == ("confirmed" if key in cleared else "pending")
        if key in cleared:
            assert register[key]["license"] == source["license_scope"]
            assert register[key]["license_url"] == source["license_url"]
            assert register[key]["Owner decision evidence URL"] == source["license_evidence_url"]
            assert "github.com/M7-KB/tabayyan" not in register[key]["license_url"]
        assert source["public_display_allowed"] is False


def test_private_tree_guard_and_public_manifest():
    assert check_public_tree() == 0
    for path in [
        "corpus/corpus.jsonl",
        "corpus/private/data.jsonl",
        "data/raw/file.txt",
        "corpus/index/data.bin",
        "docs/raw/file.pdf",
        "data/private/file.json",
    ]:
        assert is_private_artifact(path)
    assert not is_private_artifact("corpus/manifest.json")
    assert not is_private_artifact("data/raw/.gitkeep")


def test_force_added_private_file_fails_tree_guard(tmp_path, monkeypatch, capsys):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "corpus/private").mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("/corpus/private/\n", encoding="utf-8")
    artifact = tmp_path / "corpus/private/synthetic.jsonl"
    artifact.write_text("synthetic-private-content", encoding="utf-8")
    subprocess.run(["git", "add", "-f", "corpus/private/synthetic.jsonl"], cwd=tmp_path, check=True)
    monkeypatch.setattr("corpus.check_public_tree.ROOT", tmp_path)
    assert check_public_tree() == 1
    assert "synthetic-private-content" not in capsys.readouterr().out


def test_actual_ignore_rules_cover_private_artifacts():
    paths = [
        "corpus/private/data.jsonl",
        "corpus/corpus.jsonl",
        "corpus/index/data.bin",
        "data/raw/source.txt",
        "data/private/data.json",
    ]
    for path in paths:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True)
        assert result.returncode == 0


def test_private_mode_does_not_accept_unknown_source():
    item = record()
    item["source_id"] = "unknown"
    with pytest.raises(CorpusValidationError, match="rule 1"):
        validate_records(
            [item], *metadata("faq"), allow_pending_review=True, require_redistribution=False
        )


@pytest.mark.parametrize("source_id", ["hadith", "dorar-hadith"])
@pytest.mark.parametrize("permission", [None, False, "true"])
def test_runtime_rejects_unresolved_public_display(private_files, source_id, permission):
    _, sources, _, _, source_path, _, _ = private_files
    sources[source_id]["public_display_allowed"] = permission
    source_path.write_text(json.dumps({"sources": list(sources.values())}), encoding="utf-8")
    with pytest.raises(CorpusValidationError, match="row 1: .*public_display_allowed"):
        load(private_files, allow_pending_review=True)
    # Offline ingestion validation is distinct from runtime public display.
    assert load(private_files, allow_pending_review=True, require_public_display=False)[0]


def test_startup_retains_safe_row_error(private_files, monkeypatch, caplog):
    item, _, corpus, manifest, sources, register, write = private_files
    bad = dict(item, corpus_id="private-source-text", text_normalized="private-source-text")
    write([item, bad])

    def actual_loader(path, manifest_path, *, allow_pending_review):
        return load_private_corpus(
            path,
            manifest_path,
            allow_pending_review=allow_pending_review,
            sources_path=sources,
            register_path=register,
        )

    monkeypatch.setattr("api.main.load_private_corpus", actual_loader)
    app = create_app(
        Settings(
            openai_api_key="inert-test-value",
            private_corpus_path=corpus,
            corpus_manifest_path=manifest,
            allow_pending_review=True,
        )
    )
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["corpus_status"] == "unavailable"
        assert health["corpus_error"] == "row 2: text_normalized mismatch (rule 4)"
        assert health["corpus_items"] == health["pending_review_items"] == 0
        assert "private-source-text" not in client.get("/health").text
    messages = [r.getMessage() for r in caplog.records if r.name == "api.main"]
    assert messages == ["Private corpus unavailable: row 2: text_normalized mismatch (rule 4)"]
    assert str(corpus) not in caplog.text
    assert "private-source-text" not in caplog.text


@pytest.mark.parametrize("approved_by", ["pending", "sharia-reviewer-1"])
def test_health_counts_actual_pending_records(private_files, monkeypatch, approved_by):
    item, _, corpus, manifest, sources, register, write = private_files
    write([dict(item, approved_by=approved_by)])

    def actual_loader(path, manifest_path, *, allow_pending_review):
        return load_private_corpus(
            path,
            manifest_path,
            allow_pending_review=allow_pending_review,
            sources_path=sources,
            register_path=register,
        )

    monkeypatch.setattr("api.main.load_private_corpus", actual_loader)
    with TestClient(
        create_app(
            Settings(
                openai_api_key="inert-test-value",
                private_corpus_path=corpus,
                corpus_manifest_path=manifest,
                allow_pending_review=True,
            )
        )
    ) as client:
        health = client.get("/health").json()
        assert health["corpus_status"] == "loaded"
        assert health["corpus_error"] is None
        assert health["pending_review_items"] == (1 if approved_by == "pending" else 0)


@pytest.mark.parametrize(
    "path",
    [
        "corpus/corpus.v1.jsonl",
        "corpus/quran.jsonl",
        "corpus/build/corpus.jsonl",
        "corpus/corpus.jsonl.bak",
        "corpus/records/bukhari.jsonl",
        "data/corpus.jsonl",
        "corpus/faiss.index",
        "data/embeddings.npy",
        "data/vector.faiss.bak",
    ],
)
def test_alternate_build_outputs_are_ignored_and_rejected(path):
    assert is_private_artifact(path)
    assert subprocess.run(["git", "check-ignore", path], capture_output=True).returncode == 0
