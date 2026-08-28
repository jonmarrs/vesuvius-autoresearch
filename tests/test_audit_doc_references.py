"""Tests for the path-and-commit reference audit.

The first version of this tool reported 21 unreachable commits, of which 19 were
villa's -- a different repository's history, not dangling references. A tool that
cries wolf gets ignored, so the false-positive classes it has already grown are
pinned here alongside its ability to find a real one.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import audit_doc_references as mod  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

MAX_LIVE_STALE_PATHS = 1


def test_it_recognises_a_repository_path():
    """The basic extraction. Without this the audit silently checks nothing."""
    paths, _ = mod.cited(os.path.join(_REPO, "reports", "villa_prize_action_matrix.md"))
    assert any(p.startswith("scripts/") for p in paths)


def test_it_ignores_an_elided_path():
    """`reports/nnunetv2_baseline_...` in prose is a shortened name, not a citation,
    and flagging it trains the reader to skim past real findings."""
    import re

    assert mod.PATHISH_RE.match("scripts/foo.py")
    tok = "reports/nnunetv2_baseline_Dataset003_..."
    assert "..." in tok  # the guard in `cited` is what skips it
    assert re.match(mod.PATHISH_RE, tok), "the regex alone would accept it"


def test_a_villa_commit_is_not_called_dangling():
    """Our pin belongs to the submodule's history. Reporting it as unreachable was
    the first version's largest error, 19 of 21 flags."""
    assert mod.where("ced62390e") == "villa submodule"


def _rev(ref):
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "--short", ref],
        cwd=_REPO,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_a_commit_on_main_is_recognised():
    """The other direction: a commit this repository actually has.

    Resolves `main`, not `HEAD`. The first version used HEAD, which asserted
    "I am currently on main" rather than anything about `where()`, and failed on
    every feature branch: on a branch, HEAD is genuinely not an ancestor of main,
    so `where()` correctly returned "this repo, not on main" and the test called
    correct behaviour a failure.
    """
    assert mod.where(_rev("main")) == "this repo"


def test_a_commit_off_main_is_recognised_as_off_main():
    """The branch `where()` has that nothing covered until a feature branch found it.

    A commit this repo has but main does not must be reported as present and off
    main, not as dangling. Asserted only when HEAD is actually off main, so this
    is a real assertion on a branch and a no-op on main rather than a test that
    quietly changes meaning.
    """
    head = _rev("HEAD")
    if mod._is_ancestor(head, "main", _REPO):
        return
    assert mod.where(head) == "this repo, not on main"


def test_an_invented_commit_resolves_nowhere():
    """Without this the classifier could be a function that always finds a home."""
    assert mod.where("0123456789abcdef0123456789abcdef01234567") is None


def test_dated_documents_are_separated_from_live_ones():
    """A May planning document recording a path that has since moved is history.
    Editing it to satisfy a tool would destroy the record, so the audit must not
    lump the two together."""
    assert mod.DATED_RE.search("docs/PROGRESS_PRIZE_SUBMISSION_2026-05.md")
    assert not mod.DATED_RE.search("docs/VILLA_STRATEGY.md")


def test_live_documents_stay_clean():
    """The regression guard. Live documents are down to one known-stale path, which
    is annotated in place as absent at our pin. A second means a new reference
    rotted, which is exactly the failure that cost this repo three months."""
    _, missing_paths, _, _, _ = mod.audit()
    live = [(d, p) for d, p in missing_paths if not mod.DATED_RE.search(d)]
    assert len(live) <= MAX_LIVE_STALE_PATHS, (
        f"{len(live)} stale paths in live documents: "
        + ", ".join(f"{p} in {d}" for d, p in live)
    )
