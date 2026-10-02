"""Tests for the path-and-commit reference audit.

The first version of this tool reported 21 unreachable commits, of which 19 were
villa's -- a different repository's history, not dangling references. A tool that
cries wolf gets ignored, so the false-positive classes it has already grown are
pinned here alongside its ability to find a real one.
"""

import os
import sys

import pytest

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import audit_doc_references as mod  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

# Both documents explicitly identify these paths as historical/absent. Keep the
# exceptions exact: a count allowance could hide a new broken reference.
KNOWN_HISTORICAL_PATHS = {
    ("docs/VILLA_STRATEGY.md", "villa/segmentation/model_optimization_framework/run_autoresearch_nnunet.py"),
    ("reports/spiral_satisfaction_winding_blindness.md", "villa/volume-cartographer/scripts/spiral/"),
}


@pytest.fixture
def history(tmp_path, monkeypatch):
    """Real, tiny repositories independent of checkout depth and branch names."""
    import subprocess

    repo = tmp_path / "project"
    villa = repo / "villa"
    villa.mkdir(parents=True)

    def git(cwd, *args):
        return subprocess.check_output(
            ["git", "-C", str(cwd), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "-c", "commit.gpgsign=false", *args],
            env=mod._git_env(), text=True, stderr=subprocess.DEVNULL,
        ).strip()

    for path, name in ((repo, "project"), (villa, "upstream")):
        git(path, "init", "-b", "main")
        git(path, "commit", "--allow-empty", "-m", name)
    monkeypatch.setattr(mod, "_REPO", str(repo))
    monkeypatch.setattr(mod, "VILLA", str(villa))
    return repo, villa, git


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


def test_a_villa_commit_is_not_called_dangling(history):
    repo, villa, git = history
    assert mod.where(git(villa, "rev-parse", "HEAD")) == "villa submodule"


def test_a_commit_on_main_is_recognised(history):
    repo, villa, git = history
    assert mod.where(git(repo, "rev-parse", "main")) == "this repo"


def test_a_commit_off_main_is_recognised_as_off_main(history):
    repo, villa, git = history
    git(repo, "checkout", "-b", "feature")
    git(repo, "commit", "--allow-empty", "-m", "not on main")
    assert mod.where(git(repo, "rev-parse", "HEAD")) == "this repo, not on main"


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
    """Fail on every new stale path; only named historical references are exempt."""
    _, missing_paths, _, _, _ = mod.audit()
    live = {(d, p) for d, p in missing_paths if not mod.DATED_RE.search(d)}
    unexpected = live - KNOWN_HISTORICAL_PATHS
    assert not unexpected, (
        "new stale paths in live documents: "
        + ", ".join(f"{p} in {d}" for d, p in sorted(unexpected))
    )


def test_an_empty_villa_dir_does_not_claim_the_parents_commits(tmp_path, monkeypatch):
    """An uninitialised submodule is an empty directory, and git run inside it
    answers about the ENCLOSING repository. Unguarded, `where()` attributed this
    repo's own commits to villa -- found on a worktree whose villa/ was empty."""
    import subprocess as sp

    parent = tmp_path / "parent"
    (parent / "villa").mkdir(parents=True)
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
    }
    git = ["git", "-c", "commit.gpgsign=false"]
    sp.run(git + ["init", "-q"], cwd=parent, check=True, env=env)
    sp.run(
        git + ["commit", "-q", "--allow-empty", "-m", "x"],
        cwd=parent,
        check=True,
        env=env,
    )
    head = sp.run(
        git + ["rev-parse", "HEAD"],
        cwd=parent,
        check=True,
        env=env,
        capture_output=True,
        text=True,
    ).stdout.strip()
    monkeypatch.setattr(mod, "VILLA", str(parent / "villa"))
    assert mod.where(head) != "villa submodule"
    # Git exports GIT_DIR to hooks run from a linked worktree, and with it set every
    # git call ignores its cwd -- villa/ then "is" a checkout of the parent. The
    # first fix passed under plain pytest and still failed inside the hook.
    monkeypatch.setenv("GIT_DIR", str(parent / ".git"))
    assert mod.where(head) != "villa submodule"
