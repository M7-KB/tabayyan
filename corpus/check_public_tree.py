"""Reject tracked private corpus/raw/index artifacts, including force-added files."""

import subprocess

from corpus.validate import ROOT


def is_private_artifact(path: str) -> bool:
    return path == "corpus/corpus.jsonl" or (
        path.startswith(
            (
                "corpus/private/",
                "corpus/index/",
                "corpus/indexes/",
                "data/private/",
                "data/raw/",
                "docs/raw/",
            )
        )
        and path != "data/raw/.gitkeep"
    )


def main() -> int:
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8")
    if any(is_private_artifact(path) for path in files.split("\0") if path):
        print("Public tree contains a forbidden private artifact")
        return 1
    print("Public tree contains no tracked private corpus, raw files or indexes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
