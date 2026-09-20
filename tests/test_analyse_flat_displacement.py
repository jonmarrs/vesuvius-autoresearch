"""The redesigned radial study's rule, tested before any arm scored.

The branch that matters is the failure branch: if removing the flatten did not
buy a tight floor, the study must refuse to interpret single arms rather than
quietly widen its threshold.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyse_flat_displacement.py"
BASE = 1_000_000


def arm(tmp: Path, name: str, val: float) -> str:
    p = tmp / f"{name}.json"
    p.write_text(json.dumps({"summary": {"total_fg_pixels": val}}))
    return f"{name}={p}"


def run(tmp, zero, inn=None, out=None, extra=()):
    args = [sys.executable, str(SCRIPT), arm(tmp, "rad0", BASE), arm(tmp, "zero", zero)]
    if inn is not None:
        args.append(arm(tmp, "in", inn))
    if out is not None:
        args.append(arm(tmp, "out", out))
    return subprocess.run(args + list(extra), capture_output=True, text=True)


def test_a_loose_floor_refuses_to_interpret_arms(tmp_path):
    """THE failure branch: F above 1.5% means vc_render is noisy, and a -10% IN
    must NOT be called sufficient."""
    r = run(tmp_path, zero=BASE * 1.03, inn=BASE * 0.90, out=BASE * 1.01)
    assert "REDESIGN FAILED" in r.stdout
    assert "SUFFICIENT" not in r.stdout


def test_a_tight_floor_permits_interpretation(tmp_path):
    r = run(tmp_path, zero=BASE * 1.002, inn=BASE * 0.90, out=BASE * 1.01)
    assert "REDESIGN FAILED" not in r.stdout
    assert "SUFFICIENT" in r.stdout


def test_effect_must_clear_three_times_the_floor(tmp_path):
    """F = 1%, so 3F = 3%. A 2% loss does not clear it even though it is 'real'."""
    r = run(tmp_path, zero=BASE * 1.01, inn=BASE * 1.01 * 0.98, out=BASE * 1.01)
    assert "NOT THE CAUSE" in r.stdout


def test_effect_outside_the_gap_fix_band_is_a_different_effect(tmp_path):
    r = run(tmp_path, zero=BASE, inn=BASE * 0.50, out=BASE)
    assert "DIFFERENT EFFECT" in r.stdout


def test_effects_are_measured_against_zero_not_rad0(tmp_path):
    """rad0 1e6, ZERO 1.002e6, IN 0.9018e6 -> -10% vs ZERO, -9.82% vs rad0."""
    r = run(tmp_path, zero=BASE * 1.002, inn=BASE * 1.002 * 0.90, out=BASE * 1.002)
    assert "-10.00%" in r.stdout


def test_floor_cannot_be_computed_without_both_references(tmp_path):
    p = tmp_path / "zero.json"
    p.write_text(json.dumps({"summary": {"total_fg_pixels": BASE}}))
    r = subprocess.run(
        [sys.executable, str(SCRIPT), f"zero={p}"], capture_output=True, text=True
    )
    assert r.returncode != 0
    assert "rad0" in (r.stdout + r.stderr)


def test_floor_only_emits_no_verdict(tmp_path):
    r = run(tmp_path, zero=BASE * 1.002, extra=("--floor-only",))
    assert r.returncode == 0
    assert "No verdict" in r.stdout
    assert "VERDICT: SUFFICIENT" not in r.stdout


def test_thresholds_match_the_registration():
    src = SCRIPT.read_text()
    assert "F_MAX = 0.015" in src
    assert "MARGIN = 3.0" in src
    assert "IN_LO, IN_HI = 0.05, 0.15" in src
