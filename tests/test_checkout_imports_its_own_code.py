"""Tests must exercise the checkout they live in.

Every checkout shares the main checkout's .venv (a worktree symlinks it), whose
editable install points at one checkout's src/. `uv run` re-points it at the
checkout it runs in: the loop's cycles point it at main, a worktree's hooks at
the worktree. Tests that imported through it tested whichever checkout ran
`uv run` last (seen 2026-10-12, PR #39).

The top level is a namespace package (no __init__.py), so its __path__ spans
every checkout on sys.path; this checkout's src must come first. Its
subpackages are regular packages and load whole from the first entry.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"


def test_the_package_is_imported_from_this_checkout():
    import vesuvius_autoresearch
    import vesuvius_autoresearch.core

    assert Path(vesuvius_autoresearch.__path__[0]).resolve().is_relative_to(SRC)
    assert Path(vesuvius_autoresearch.core.__file__).resolve().is_relative_to(SRC)


def test_subprocesses_import_the_package_from_this_checkout():
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            "import vesuvius_autoresearch.core as m; print(m.__file__)",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert Path(out.strip()).resolve().is_relative_to(SRC)


def test_hooks_never_sync_the_shared_environment():
    # A plain `uv run` in a worktree re-points the shared editable install at the
    # worktree, under the running loop.
    import yaml

    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    entries = [h.get("entry", "") for r in config["repos"] for h in r["hooks"]]
    assert entries
    for entry in entries:
        if entry.startswith("uv run"):
            assert entry.startswith("uv run --no-sync"), entry
