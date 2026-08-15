"""Probes must resolve their inputs from the repo, not the process cwd.

Both probes used `sys.path.insert(0, os.path.abspath("."))` and cwd-relative `local_data/`
paths, so they worked only when launched from the repo root. That is worse than an ordinary
bug in a measurement tool: probe_placement_field would report on the targets it happened to
find and stay silent about the rest, so a reader could not tell a clean result from a
partial one. It also hardcoded "../scrollgt/data/..." for a single target, which resolved
to nothing from anywhere else.
"""

import ast
import os
import pathlib

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
PROBES = ["probe_placement_field.py", "probe_registration_offset.py"]


def _code_only(path):
    """Source with comments stripped.

    The fix documents the old pattern in prose, so a naive substring check matches the
    explanation rather than live code. This is the second time that has caught me today;
    check code, not commentary.
    """
    return "\n".join(ln.split("#")[0] for ln in path.read_text().splitlines())


@pytest.mark.parametrize("name", PROBES)
def test_probe_does_not_resolve_paths_from_cwd(name):
    src = _code_only(SCRIPTS / name)
    assert 'os.path.abspath(".")' not in src, (
        f"{name} resolves sys.path from the process cwd; use REPO_ROOT from __file__"
    )
    assert "REPO_ROOT" in src, f"{name} should anchor paths to REPO_ROOT"


@pytest.mark.parametrize("name", PROBES)
def test_probe_has_no_bare_relative_data_paths(name):
    """A bare "local_data/..." or "../scrollgt/..." literal is a cwd dependency."""
    tree = ast.parse((SCRIPTS / name).read_text())
    bad = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and (n.value.startswith("local_data/") or n.value.startswith("../"))
        and not _inside_join(tree, n)
    ]
    assert not bad, (
        f"{name} has cwd-relative literals not wrapped in a REPO_ROOT join: {bad}"
    )


def _inside_join(tree, target):
    """True if the string constant is an argument to an os.path.join call."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "join"
        ):
            for arg in node.args:
                if arg is target:
                    return True
    return False


@pytest.mark.parametrize("name", PROBES)
def test_probe_repo_root_points_at_the_repo(name):
    """REPO_ROOT must land on the repo, not one level off."""
    src = (SCRIPTS / name).read_text()
    ns: dict = {}
    for line in src.splitlines():
        if line.startswith("REPO_ROOT"):
            exec(
                "import os\n" + line.replace("__file__", repr(str(SCRIPTS / name))), ns
            )
            break
    assert "REPO_ROOT" in ns, f"{name} defines no REPO_ROOT"
    assert os.path.isdir(os.path.join(ns["REPO_ROOT"], "repro", "sota_data")), (
        f"{name} REPO_ROOT={ns['REPO_ROOT']} does not contain repro/sota_data"
    )
