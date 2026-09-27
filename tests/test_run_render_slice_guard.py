"""run_render.sh refuses a work dir that already holds per-slice TIFFs (finding 65's trap)."""

import os
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1] / "repro" / "spiral_render" / "run_render.sh"
)


def _workdir(tmp_path: Path, with_slices: bool) -> Path:
    w = tmp_path / "w"
    (w / "spiral-fitting").mkdir(parents=True)
    ink = w / "meshes" / "concat" / "w120-129_flat" / "ink"
    ink.mkdir(parents=True)
    if with_slices:
        (ink / "00.tif").write_bytes(b"II*\x00")
    return w


def _run(w: Path, **env) -> subprocess.CompletedProcess:
    # VENV points at a program that exits 0 immediately: reaching it means the guard let the run through.
    e = {**os.environ, "VENV": "/bin/true", **env}
    return subprocess.run(
        ["bash", str(SCRIPT), str(w)], capture_output=True, text=True, env=e
    )


def test_existing_slices_are_refused(tmp_path):
    r = _run(_workdir(tmp_path, with_slices=True))
    assert r.returncode == 3
    assert "would SKIP and re-score" in r.stderr


def test_the_explicit_override_lets_it_through(tmp_path):
    r = _run(_workdir(tmp_path, with_slices=True), RENDER_ALLOW_EXISTING_SLICES="1")
    assert r.returncode == 0, r.stderr


def test_a_clean_workdir_is_not_blocked(tmp_path):
    r = _run(_workdir(tmp_path, with_slices=False))
    assert r.returncode == 0, r.stderr
