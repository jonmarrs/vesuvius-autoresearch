"""Guards on the scorer-weights check.

get_ink_metrics.py downloads the nnU-Net model with no `revision=`, so it follows
the repo's main. A silent weight change would make arms scored either side of it
incomparable with nothing in any log to show for it. These tests hold the check to
failing loudly in both ways that matter: more than one revision, or one that is not
the revision every existing measurement used.
"""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cswp",
    Path(__file__).resolve().parents[1] / "scripts" / "check_scorer_weights_pinned.py",
)
assert SPEC and SPEC.loader
cswp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cswp)


def _cache(root: Path, *revs: str) -> Path:
    for r in revs:
        (root / cswp.REPO_DIR / "snapshots" / r).mkdir(parents=True)
    return root


def test_known_revision_is_the_one_every_measurement_used():
    assert cswp.KNOWN == "d79c5860674fddd53370a59ee92f229c9b9de88c"


def test_passes_on_exactly_the_expected_revision(tmp_path, monkeypatch, capsys):
    _cache(tmp_path, cswp.KNOWN)
    monkeypatch.setattr("sys.argv", ["x", "--cache", str(tmp_path)])
    assert cswp.main() == 0
    assert "PASS" in capsys.readouterr().out


def test_fails_when_two_revisions_exist(tmp_path, monkeypatch, capsys):
    """The dangerous case: arms either side of the change are incomparable."""
    _cache(tmp_path, cswp.KNOWN, "0" * 40)
    monkeypatch.setattr("sys.argv", ["x", "--cache", str(tmp_path)])
    assert cswp.main() == 1
    assert "NOT comparable" in capsys.readouterr().out


def test_fails_when_the_single_revision_is_not_the_expected_one(
    tmp_path, monkeypatch, capsys
):
    _cache(tmp_path, "f" * 40)
    monkeypatch.setattr("sys.argv", ["x", "--cache", str(tmp_path)])
    assert cswp.main() == 1
    assert "upstream model moved" in capsys.readouterr().out


def test_absent_cache_is_reported_not_passed(tmp_path, monkeypatch, capsys):
    """No cache must never read as 'fine'."""
    monkeypatch.setattr("sys.argv", ["x", "--cache", str(tmp_path)])
    assert cswp.main() == 2
    assert "not cached" in capsys.readouterr().out
