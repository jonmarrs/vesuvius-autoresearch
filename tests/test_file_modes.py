"""A file written under a temporary name and renamed into place keeps the mode of the file it replaces, or gets
the umask's when new. mkstemp and NamedTemporaryFile create their file 0600, and renamed as it was it left the
output readable by its owner alone: every checkpoint and the loop's new state files until 2026-10-17, and the
writers below until the fix that added this file."""

import ast
import os
import stat
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import pytest

from vesuvius_autoresearch.core import file_modes

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def umask_027():
    """A umask other than the usual 022, so a mode that ignored it would show."""
    previous = os.umask(0o027)
    try:
        yield
    finally:
        os.umask(previous)


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_the_umask_is_read_without_being_changed(umask_027):
    assert file_modes.current_umask() == 0o027
    assert os.umask(0o027) == 0o027


def test_without_proc_the_umask_is_read_by_setting_it_back(umask_027, monkeypatch):
    def no_proc(*args, **kwargs):
        raise OSError("no /proc")

    monkeypatch.setattr(file_modes, "open", no_proc, raising=False)
    assert file_modes.current_umask() == 0o027
    assert os.umask(0o027) == 0o027


def test_replacement_mode_is_the_replaced_files_else_the_umasks(tmp_path, umask_027):
    existing = tmp_path / "existing"
    existing.write_text("")
    os.chmod(existing, 0o604)
    assert file_modes.replacement_mode(existing) == 0o604
    assert file_modes.replacement_mode(tmp_path / "new") == 0o640


def _bench_json(path):
    from vesuvius_autoresearch.fibers.provenance import write_json

    write_json(path, {"a": 1})


def _bench_npy(path):
    import numpy as np

    from vesuvius_autoresearch.fibers.provenance import atomic_file

    with atomic_file(path, "w+b") as f:
        np.save(f, np.zeros(2))


def _candidate_json(path):
    from scripts.candidate_artifacts import write_json

    write_json(path, {"a": 1})


@pytest.mark.parametrize("write", [_bench_json, _bench_npy, _candidate_json])
def test_an_atomic_writer_gives_the_umasks_mode_and_keeps_a_replaced_files(
    tmp_path, umask_027, write
):
    new = tmp_path / "new.out"
    write(new)
    assert _mode(new) == 0o640

    replaced = tmp_path / "replaced.out"
    replaced.write_text("old")
    os.chmod(replaced, 0o644)
    write(replaced)
    assert _mode(replaced) == 0o644 and replaced.read_bytes() != b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["new.out", "replaced.out"]


def _replace_with_a_0600_file(staging):
    """As another process may: a new file renamed over the staging path, not the file publish_new_file made."""
    fd, other = tempfile.mkstemp(dir=staging.parent)
    os.write(fd, b"png")
    os.close(fd)
    os.replace(other, staging)


@pytest.mark.parametrize(
    "write", [lambda staging: staging.write_bytes(b"png"), _replace_with_a_0600_file]
)
def test_a_published_label_artifact_gets_the_umasks_mode(tmp_path, umask_027, write):
    from scripts.labeling.label_artifacts import publish_new_file

    output = tmp_path / "out" / "label.png"
    with publish_new_file(output, tmp_path / "source.png") as staging:
        write(staging)
    assert output.read_bytes() == b"png" and _mode(output) == 0o640
    assert [p.name for p in output.parent.iterdir()] == ["label.png"]


def test_a_downloaded_obj_gets_the_umasks_mode(tmp_path, umask_027, monkeypatch):
    from repro.sota_data import obj_geometry

    class FS:
        def get(self, key, path):
            Path(path).write_text(key)

    fake = types.SimpleNamespace(S3FileSystem=lambda **kwargs: FS())
    monkeypatch.setitem(sys.modules, "s3fs", fake)
    monkeypatch.chdir(tmp_path)
    path = obj_geometry.fetch_obj("s3://bucket/a/s.obj")
    assert Path(path).read_text() == "bucket/a/s.obj" and _mode(path) == 0o640


# Functions that make a 0600 temporary file or a 0700 temporary directory without setting a mode, and why.
NOT_CHECKED = {
    # Frozen into the registered neural-tracer chains' work directories, which refuse to resume when the
    # repository's copy differs.
    "scripts/make_tracer_presence.py::write_presence",
    "scripts/resample_cube_pitch.py::write_ct",
    "scripts/resample_cube_pitch.py::write_prob",
    # They move a subdirectory they create with mkdir, never the temporary directory.
    "scripts/candidate_artifacts.py::staged_directory",
    "scripts/export_fiber_targets.py::main",
    # Scratch, never renamed into place.
    "scripts/f1_noise_probe.py::execute",
    "scripts/tracer_rescore_analysis.py::v1_scorer",
}
TEMPORARY = {"mkstemp", "mkdtemp", "NamedTemporaryFile"}
SETS_MODE = {"replacement_mode", "chmod", "fchmod"}


def _called(call, aliases):
    """The name a call calls (`f(...)`, `x.f(...)`), with `from tempfile import f as g` undone."""
    func = call.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    return aliases.get(name, name)


def _own_calls(scope):
    """The calls in a function's body, or a module's top level, not in a function nested in it."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Call):
            yield node
        stack.extend(ast.iter_child_nodes(node))


def _temporaries_without_a_mode(tree):
    aliases = {
        alias.asname or alias.name: alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "tempfile"
        for alias in node.names
    }
    scopes = [tree] + [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for scope in scopes:
        names = set()
        for call in _own_calls(scope):
            name = _called(call, aliases)
            kept = any(
                k.arg == "delete" and getattr(k.value, "value", True) is False
                for k in call.keywords
            )
            if name in ("mkstemp", "mkdtemp") or (
                name == "NamedTemporaryFile" and kept
            ):
                names.add(name)
            elif name in SETS_MODE:
                names.add("mode")
        if names & TEMPORARY and "mode" not in names:
            yield getattr(scope, "name", "<module>")


def test_the_scan_finds_a_temporary_however_it_is_spelled():
    source = """
from tempfile import mkstemp as _mk
import tempfile as tf

def a(path):
    fd, tmp = _mk(dir=path.parent)

def b(out):
    with tf.NamedTemporaryFile(dir=str(out.parent), delete=False) as f:
        pass

def c(out):
    build = tf.mkdtemp(dir=out.parent)

def d(path):
    fd, tmp = tf.mkstemp(dir=path.parent)
    os.fchmod(fd, replacement_mode(path))

def e(out):
    def inner():
        os.chmod(out, 0o644)
    fd, tmp = tf.mkstemp()

def f():
    with tf.NamedTemporaryFile() as scratch:
        pass
"""
    found = list(_temporaries_without_a_mode(ast.parse(source)))
    assert sorted(found) == ["a", "b", "c", "e"]


def test_every_temporary_file_writer_sets_the_mode():
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "*.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    missing = []
    for name in tracked:
        # The retired scripts in scripts/archive/ are left as they were.
        if name.startswith(
            ("tests/", "villa/", "repro/villa_preserved/", "scripts/archive/")
        ):
            continue
        tree = ast.parse((ROOT / name).read_text(errors="replace"))
        missing += [
            f"{name}::{function}"
            for function in _temporaries_without_a_mode(tree)
            if f"{name}::{function}" not in NOT_CHECKED
        ]
    assert missing == [], (
        "these make a 0600 temporary file or 0700 directory and set no mode: give a file "
        "vesuvius_autoresearch.core.file_modes.replacement_mode(path) before it is renamed into place, "
        "or name the function in NOT_CHECKED with the reason"
    )
