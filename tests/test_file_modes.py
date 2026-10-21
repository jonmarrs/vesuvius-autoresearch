"""A file written under a temporary name and renamed into place keeps the mode of the file it replaces, or gets
the umask's when new. mkstemp and NamedTemporaryFile create their file 0600, and renamed as it was it left the
output readable by its owner alone: promoted checkpoints and the loop's state until 2026-10-17, and the writers
below until the fix that added this file."""

import os
import re
import stat
import subprocess
import sys
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


def test_a_published_label_artifact_gets_the_umasks_mode(tmp_path, umask_027):
    from scripts.labeling.label_artifacts import publish_new_file

    output = tmp_path / "out" / "label.png"
    with publish_new_file(output, tmp_path / "source.png") as staging:
        staging.write_bytes(b"png")
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


# Writers that rename a mkstemp or NamedTemporaryFile file into place without replacement_mode, and why.
NOT_CHECKED = {
    # Frozen into the registered neural-tracer chains' work directories, which refuse to resume when the
    # repository's copy differs.
    "scripts/resample_cube_pitch.py",
}
TEMPORARY_FILE = re.compile(
    r"\bmkstemp\(|\bNamedTemporaryFile\([^)]*delete=False", re.S
)


def test_every_temporary_file_writer_sets_the_mode():
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "*.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    missing = []
    for name in tracked:
        if name.startswith(
            ("tests/", "villa/", "repro/villa_preserved/", "scripts/archive/")
        ):
            continue
        text = (ROOT / name).read_text(errors="replace")
        if (
            TEMPORARY_FILE.search(text)
            and "replacement_mode" not in text
            and name not in NOT_CHECKED
        ):
            missing.append(name)
    assert missing == [], (
        "these rename a 0600 temporary file into place: give it "
        "vesuvius_autoresearch.core.file_modes.replacement_mode(path) first"
    )
