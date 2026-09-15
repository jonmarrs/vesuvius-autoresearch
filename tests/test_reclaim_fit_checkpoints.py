"""Guards on the checkpoint reclaimer.

Written when `/` hit 99% full mid-study. The temptation was to delete whole fit
directories; that would have destroyed the 287M of meshes (3 hours of compute to
recreate) to reclaim space that is 93% optimizer checkpoint. These tests hold the
tool to deleting only the resumable part, never the irreplaceable part.
"""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "rfc",
    Path(__file__).resolve().parents[1] / "scripts" / "reclaim_fit_checkpoints.py",
)
assert SPEC and SPEC.loader
rfc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rfc)


def _arm(root: Path, name: str, *, meshes: bool = True, size: int = 2048) -> Path:
    d = root / f"2026-09-01_s1_slice-1-2_38442-patch_{name}"
    d.mkdir(parents=True)
    (d / rfc.CKPT).write_bytes(b"\0" * size)
    if meshes:
        (d / "meshes").mkdir()
    return d


def test_live_study_arms_are_protected_by_default():
    for i in range(1, 10):
        assert f"curbase_s{i}" in rfc.PROTECTED
    assert "curbase_s1rr" in rfc.PROTECTED


def test_arm_of_parses_the_dated_fit_dir_name():
    assert (
        rfc.arm_of(Path("2026-09-13_s1_slice-13056-18432_38442-patch_nosamecur_s2"))
        == "nosamecur_s2"
    )


def test_dry_run_deletes_nothing(tmp_path, monkeypatch, capsys):
    d = _arm(tmp_path, "nosamecur_s1")
    monkeypatch.setattr("sys.argv", ["x", "--spiral-out", str(tmp_path)])
    rfc.main()
    assert (d / rfc.CKPT).exists()
    assert "DRY RUN" in capsys.readouterr().out


def test_apply_removes_the_checkpoint_but_keeps_the_meshes(tmp_path, monkeypatch):
    d = _arm(tmp_path, "nosamecur_s1")
    monkeypatch.setattr("sys.argv", ["x", "--spiral-out", str(tmp_path), "--apply"])
    rfc.main()
    assert not (d / rfc.CKPT).exists()
    assert (d / "meshes").is_dir()


def test_apply_never_touches_a_protected_arm(tmp_path, monkeypatch):
    d = _arm(tmp_path, "curbase_s4")
    monkeypatch.setattr("sys.argv", ["x", "--spiral-out", str(tmp_path), "--apply"])
    rfc.main()
    assert (d / rfc.CKPT).exists(), "a live-study checkpoint was deleted"


def test_refuses_to_strip_an_arm_that_has_no_meshes(tmp_path, monkeypatch, capsys):
    """Deleting the checkpoint must never be what leaves an arm unrenderable."""
    d = _arm(tmp_path, "nosamecur_s2", meshes=False)
    monkeypatch.setattr("sys.argv", ["x", "--spiral-out", str(tmp_path), "--apply"])
    rfc.main()
    assert (d / rfc.CKPT).exists()
    assert "refusing to strip its last artifact" in capsys.readouterr().out


def test_also_can_release_a_protected_arm_explicitly(tmp_path, monkeypatch):
    d = _arm(tmp_path, "curbase_s1")
    monkeypatch.setattr(
        "sys.argv",
        ["x", "--spiral-out", str(tmp_path), "--apply", "--also", "curbase_s1"],
    )
    rfc.main()
    assert not (d / rfc.CKPT).exists()
