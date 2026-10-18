"""Tests for the render-equivalence checker.

It answers the question that follows the monitor's: the monitor says whether the
hot path changed, this says whether that change can reach a render. On
2026-09-14 those had different answers.

The dangerous failure is a false INTERCHANGEABLE -- declaring two refs equivalent
when a render would differ -- because it would let a corpus split silently, which
is exactly what happened on 2026-09-11 and took mtime archaeology to find. So the
tests weight that direction.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))

import check_render_equivalence as mod  # noqa: E402

_VILLA = _REPO / "villa"
_needs = pytest.mark.skipif(
    not (_VILLA / ".git").exists(), reason="villa submodule absent"
)


def test_it_checks_exactly_what_setup_workdir_extracts():
    """If these drift apart, the checker is inspecting paths the render does not
    use, or missing ones it does."""
    setup = (_REPO / "repro/spiral_render/setup_workdir.sh").read_text()
    for p in mod.EXTRACTED:
        assert p in setup, f"{p} is checked but not extracted by setup_workdir.sh"


def test_the_entry_points_are_the_two_the_pipeline_runs():
    assert mod.ENTRY_POINTS == (
        "spiral-fitting/render_ink.py",
        "spiral-fitting/get_ink_metrics.py",
    )


@_needs
def test_a_ref_against_itself_is_interchangeable():
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            "be09a8503",
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" in out.stdout


@_needs
@pytest.mark.parametrize("ref", ["38c2b4278", "bfef6abe0", "3b398f7cc", "d82e13edf"])
def test_the_four_cleared_refs_still_read_interchangeable(ref):
    """These were cleared by hand on 2026-09-14. If the checker ever disagrees,
    either it broke or one of those clearances was wrong."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            ref,
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" in out.stdout, f"{ref} no longer reads as interchangeable"


@_needs
def test_the_one_real_hot_path_change_is_NOT_called_interchangeable():
    """The load-bearing test. d9d70bef1 changes tifxyz.py, which render_ink
    imports. A checker that called this interchangeable would let a corpus split
    silently."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            "d9d70bef1",
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" not in out.stdout
    assert "NEEDS A HUMAN" in out.stdout
    assert "tifxyz.py" in out.stdout


@_needs
def test_the_old_09_11_split_would_have_been_caught():
    """The bump that actually split the corpus. If the checker had existed, this
    is the verdict it would have given -- lasagna and vesuvius/src both differ."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "d8c5f488a",
            "--to-ref",
            "be09a8503",
        ],
        capture_output=True,
        text=True,
    )
    assert "INTERCHANGEABLE" not in out.stdout
    assert "lasagna" in out.stdout and "DIFFERS" in out.stdout


@_needs
def test_imports_of_finds_a_known_import():
    mods = mod.imports_of(str(_VILLA), "be09a8503", "spiral-fitting/render_ink.py")
    assert "tifxyz" in mods, "render_ink.py imports tifxyz; the tracer missed it"


def test_lasagna_is_treated_as_a_pipeline_stage_not_a_library():
    """The bug this tool shipped with. `lasagna` is the flatten, invoked by
    run_render.sh as its own step, so NOTHING in ENTRY_POINTS imports it. The
    first version only flagged files the entry points import, so a commit titled
    "lasagna flatten memory" that rewrote 571 lines of it came back with only
    tifxyz.py named -- and a lasagna-ONLY change would have read RENDER-INERT.

    A false INTERCHANGEABLE is the failure that lets a corpus split silently,
    which is what happened on 2026-09-11.
    """
    assert "lasagna" in mod.STAGE_PATHS
    assert not any("lasagna" in e for e in mod.ENTRY_POINTS), (
        "if an entry point ever imports lasagna, the stage/library split needs "
        "rethinking rather than both applying"
    )


@_needs
def test_a_lasagna_change_is_never_called_inert():
    """1f544fa71 changes lasagna/fit.py, fit2tifxyz.py, model.py and optimizer.py.
    Whatever else it reports, it must not report that a render is unaffected."""
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            "1f544fa71",
        ],
        capture_output=True,
        text=True,
    )
    assert "RENDER-INERT" not in out.stdout
    assert "INTERCHANGEABLE" not in out.stdout
    assert "lasagna/fit.py" in out.stdout, "the flatten must be named explicitly"


def test_documentation_is_not_a_render_suspect():
    """A .md inside a pipeline stage cannot change a render. The stage rule
    flagged lasagna/docs/flatten.md, which is obviously wrong and makes the six
    genuine entries beside it look less trustworthy."""
    assert ".md" in mod.DOC_SUFFIXES


@_needs
def test_a_docs_only_change_in_a_stage_is_not_flagged():
    out = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts/check_render_equivalence.py"),
            "--from-ref",
            "be09a8503",
            "--to-ref",
            "0e01fe1c7",
        ],
        capture_output=True,
        text=True,
    )
    assert "flatten.md" not in out.stdout, "documentation named as a render suspect"
    assert "lasagna/fit.py" in out.stdout, "the real flatten change must still be named"


def test_test_files_are_excluded_from_suspects():
    """43 changed files reduced to 1 only because tests are dropped. If that
    stopped working the output would be unusable rather than wrong."""
    src = (_REPO / "scripts/check_render_equivalence.py").read_text()
    assert '"/tests/" not in f' in src
    assert 'startswith("test_")' in src


# --- what it cannot answer, in a throwaway villa-shaped repository --------------
#
# Each of these read as an empty tree or no imports, so as INTERCHANGEABLE or
# RENDER-INERT: the false verdicts this checker exists to prevent.

_ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}
_FILES = {
    "spiral-fitting/render_ink.py": "from tifxyz import load_tifxyz\n",
    "spiral-fitting/get_ink_metrics.py": "import numpy\n",
    "spiral-fitting/tifxyz.py": "def load_tifxyz(): pass\n",
    "lasagna/fit.py": "x = 1\n",
    "vesuvius/src/a.py": "a = 1\n",
    "vesuvius/src/vc3d_fiber_format/__init__.py": "def parse(): pass\n",
}


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        env=_ENV,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(path, files=_FILES):
    for name, text in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "add", ".")
    _git(path, "commit", "-q", "-m", "old")
    return path


def _commit(repo, name, text):
    (repo / name).write_text(text)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", f"change {name}")


def _check(repo, a="HEAD~1", b="HEAD", env=_ENV):
    return subprocess.run(
        [sys.executable, str(_REPO / "scripts/check_render_equivalence.py")]
        + ["--repo", str(repo), "--from-ref", a, "--to-ref", b],
        env=env,
        capture_output=True,
        text=True,
    )


def test_an_imported_module_change_needs_a_human(tmp_path):
    repo = _repo(tmp_path / "villa")
    _commit(repo, "spiral-fitting/tifxyz.py", "def load_tifxyz(): return 1\n")
    r = _check(repo)
    assert r.returncode == 0 and "NEEDS A HUMAN" in r.stdout, r.stdout + r.stderr
    assert "spiral-fitting/tifxyz.py" in r.stdout


def test_an_empty_directory_inside_another_repository_is_refused(tmp_path):
    """An uninitialised submodule: git answered for this repository, which has none
    of the three trees, so every one compared as the same nothing."""
    outer = _repo(tmp_path / "project", {"README": "x\n"})
    _commit(outer, "README", "y\n")
    (outer / "villa").mkdir()
    r = _check(outer / "villa")
    assert r.returncode == 2 and "not a repository of its own" in r.stderr, r.stdout
    assert "INTERCHANGEABLE" not in r.stdout


def test_a_tree_at_neither_ref_is_not_comparable(tmp_path):
    files = {k: v for k, v in _FILES.items() if not k.startswith("lasagna/")}
    repo = _repo(tmp_path / "villa", files)
    _commit(repo, "vesuvius/src/a.py", "a = 2\n")
    r = _check(repo)
    assert r.returncode == 2 and "lasagna: at neither ref" in r.stderr, r.stdout


def test_an_entry_point_at_neither_ref_is_not_comparable(tmp_path):
    """Its imports read as none, so a change to a module it imports was inert."""
    files = dict(_FILES)
    del files["spiral-fitting/get_ink_metrics.py"]
    repo = _repo(tmp_path / "villa", files)
    _commit(repo, "vesuvius/src/a.py", "a = 2\n")
    r = _check(repo)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "spiral-fitting/get_ink_metrics.py: at neither ref" in r.stderr


def test_a_ref_that_does_not_resolve_exits_2(tmp_path):
    repo = _repo(tmp_path / "villa")
    r = _check(repo, "HEAD", "no-such-ref")
    assert r.returncode == 2 and "failed" in r.stderr, r.stdout + r.stderr


def test_an_inherited_git_dir_is_ignored(tmp_path):
    """A hook exports GIT_DIR; inherited, every call read that repository."""
    repo = _repo(tmp_path / "villa")
    _commit(repo, "spiral-fitting/tifxyz.py", "def load_tifxyz(): return 1\n")
    other = _repo(tmp_path / "other", {"README": "x\n"})
    _commit(other, "README", "y\n")
    r = _check(repo, env=_ENV | {"GIT_DIR": str(other / ".git")})
    assert "NEEDS A HUMAN" in r.stdout, r.stdout + r.stderr


def test_an_unreadable_entry_point_exits_2_not_inert(tmp_path):
    """In villa's blob:none clone a blob may be missing; offline, git show fails.
    Read as no imports, a change to tifxyz.py, which render_ink.py imports, was
    RENDER-INERT."""
    repo = _repo(tmp_path / "villa")
    _commit(repo, "spiral-fitting/tifxyz.py", "def load_tifxyz(): return 1\n")
    blob = _git(repo, "rev-parse", "HEAD:spiral-fitting/render_ink.py")
    (repo / ".git" / "objects" / blob[:2] / blob[2:]).unlink()
    r = _check(repo)
    assert r.returncode == 2 and "failed" in r.stderr, r.stdout + r.stderr
    assert "RENDER-INERT" not in r.stdout


def test_a_path_at_one_ref_only_still_differs(tmp_path):
    files = {k: v for k, v in _FILES.items() if not k.startswith("lasagna/")}
    repo = _repo(tmp_path / "villa", files)
    _commit_new(repo, "lasagna/fit.py", "x = 1\n")
    r = _check(repo)
    assert r.returncode == 0 and "NEEDS A HUMAN" in r.stdout, r.stdout + r.stderr
    assert "lasagna/fit.py" in r.stdout
    files = dict(_FILES)
    del files["spiral-fitting/get_ink_metrics.py"]
    repo = _repo(tmp_path / "villa2", files)
    _commit_new(repo, "spiral-fitting/get_ink_metrics.py", "import numpy\n")
    r = _check(repo)
    assert "RENDERS MAY DIFFER" in r.stdout, r.stdout + r.stderr


def _commit_new(repo, name, text):
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    _commit(repo, name, text)


def test_a_module_moved_away_from_its_import_needs_a_human(tmp_path):
    """Listed as a rename, only tifxyz_old.py showed, which nothing imports: inert,
    while render_ink.py's import of tifxyz broke."""
    repo = _repo(tmp_path / "villa")
    _git(repo, "mv", "spiral-fitting/tifxyz.py", "spiral-fitting/tifxyz_old.py")
    _git(repo, "commit", "-q", "-m", "move")
    r = _check(repo)
    assert "NEEDS A HUMAN" in r.stdout, r.stdout + r.stderr
    assert "spiral-fitting/tifxyz.py" in r.stdout


def test_a_package_the_entry_points_import_is_traced(tmp_path):
    """`import tifxyz` uses tifxyz/__init__.py, whose stem is __init__."""
    files = {k: v for k, v in _FILES.items() if k != "spiral-fitting/tifxyz.py"}
    files["spiral-fitting/tifxyz/__init__.py"] = "def load_tifxyz(): pass\n"
    repo = _repo(tmp_path / "villa", files)
    _commit(repo, "spiral-fitting/tifxyz/__init__.py", "def load_tifxyz(): return 1\n")
    r = _check(repo)
    assert "NEEDS A HUMAN" in r.stdout, r.stdout + r.stderr
    assert "spiral-fitting/tifxyz/__init__.py" in r.stdout


def test_a_library_the_flatten_imports_is_a_suspect(tmp_path):
    """lasagna's vc3d_fiber_format_adapter imports vesuvius/src/vc3d_fiber_format,
    which the entry points do not: its __init__.py alone read RENDER-INERT
    (villa 757f70c01..b944a656c)."""
    repo = _repo(tmp_path / "villa")
    _commit(repo, "vesuvius/src/vc3d_fiber_format/__init__.py", "def parse(): 1\n")
    r = _check(repo)
    assert "NEEDS A HUMAN" in r.stdout, r.stdout + r.stderr
    assert "vesuvius/src/vc3d_fiber_format/__init__.py" in r.stdout


def test_a_name_git_would_quote_is_named_as_it_is(tmp_path):
    repo = _repo(tmp_path / "villa")
    _commit_new(repo, "lasagna/ünï x.py", "y = 1\n")
    r = _check(repo)
    assert "lasagna/ünï x.py" in r.stdout, r.stdout + r.stderr


def test_an_entry_point_that_is_a_link_is_not_traced(tmp_path):
    """The link is compared, not what it points to."""
    repo = _repo(tmp_path / "villa")
    (repo / "spiral-fitting/real_render.py").write_text("from tifxyz import x\n")
    (repo / "spiral-fitting/render_ink.py").unlink()
    (repo / "spiral-fitting/render_ink.py").symlink_to("real_render.py")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "link")
    _commit(repo, "spiral-fitting/real_render.py", "from tifxyz import y\n")
    r = _check(repo)
    assert r.returncode == 2 and "not a regular file" in r.stderr, r.stdout


def test_a_symlinked_launch_finds_its_sibling(tmp_path):
    """Under -I the script's directory is not on sys.path, and the link's is not
    where check_villa_render_path.py lives."""
    repo = _repo(tmp_path / "villa")
    link = tmp_path / "bin" / "check_render_equivalence.py"
    link.parent.mkdir()
    link.symlink_to(_REPO / "scripts/check_render_equivalence.py")
    r = subprocess.run(
        [sys.executable, "-I", str(link), "--repo", str(repo)]
        + ["--from-ref", "HEAD", "--to-ref", "HEAD"],
        env=_ENV,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and "INTERCHANGEABLE" in r.stdout, r.stdout + r.stderr
