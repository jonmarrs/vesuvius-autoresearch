"""The offset sweep's rule, tested before any arm was built.

The branch that matters is the one where MY MODEL is refuted, not the
hypothesis: the quadratic was assumed from two points, and if the sweep does
not support it no vertex may be claimed. A per-voxel ratio has failed to
extrapolate three times in this project.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyse_ink_maximum_offset.py"
sys.path.insert(0, str(REPO / "scripts"))
from analyse_ink_maximum_offset import ARMS  # noqa: E402

SHA, IMG = "be09a8503", "sha256:cafe"


def _write(root: Path, arm: str, val: float, sha: str = SHA, img: str = IMG) -> None:
    d = root / arm / "ink_metric"
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps({"summary": {"total_fg_pixels": val}}))
    (root / arm / "VILLA_SHA").write_text(sha + "\n")
    (root / arm / "RENDER_IMAGE").write_text(f"image_id={img}\n")


def _sweep(root: Path, f, **kw) -> Path:
    for x, arm in ARMS.items():
        _write(root, arm, f(x), **kw)
    return root


def run(root: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--spiral-out", str(root)],
        capture_output=True,
        text=True,
    )


def test_partial_sweep_is_refused_before_provenance(tmp_path):
    """A missing arm must give the registered refusal, not a FileNotFoundError."""
    for x, arm in list(ARMS.items())[:-1]:
        _write(tmp_path, arm, 1e6)
    r = run(tmp_path)
    assert r.returncode != 0
    assert "refused" in (r.stdout + r.stderr)
    assert "FileNotFoundError" not in r.stderr


def test_mixed_instrument_voids_the_sweep(tmp_path):
    _sweep(tmp_path, lambda x: 1e6)
    (tmp_path / ARMS[2.0] / "VILLA_SHA").write_text("otherSHA\n")
    r = run(tmp_path)
    assert r.returncode == 1 and "VOID" in r.stdout


def test_a_vertex_at_the_predicted_offset_is_reported(tmp_path):
    """Peak at +1.4 with 1.4% gain -- the registered prediction."""
    z = 1_698_914
    peak_gain = 0.0136
    k = peak_gain / (1.42**2)
    r = run(_sweep(tmp_path, lambda x: z * (1 + peak_gain - k * (x - 1.42) ** 2)))
    assert "LEVER EXISTS, PREDICTION MET" in r.stdout, r.stdout
    assert "MET" in r.stdout


def test_a_vertex_at_zero_is_no_free_lever(tmp_path):
    z = 1_698_914
    r = run(_sweep(tmp_path, lambda x: z * (1 - 0.012 * x * x)))
    assert "NO FREE LEVER" in r.stdout


def test_a_badly_fitting_sweep_claims_no_vertex(tmp_path):
    """THE model-refutation branch: a sawtooth is not a parabola."""
    z = 1_698_914
    r = run(_sweep(tmp_path, lambda x: z * (1 + 0.3 * ((int(x) % 2) - 0.5))))
    assert "NO VERTEX CLAIMED" in r.stdout, r.stdout
    assert "LEVER EXISTS" not in r.stdout


def test_an_upward_parabola_claims_no_vertex(tmp_path):
    """A minimum is not a maximum; the script must not report its vertex as a peak."""
    z = 1_698_914
    r = run(_sweep(tmp_path, lambda x: z * (1 + 0.01 * x * x)))
    assert "NO VERTEX CLAIMED" in r.stdout


def test_constants_match_the_registration():
    src = SCRIPT.read_text()
    assert "PRED_LO, PRED_HI = 0.4, 2.4" in src
    assert "R2_MIN = 0.8" in src
    assert "F = 0.000141" in src
