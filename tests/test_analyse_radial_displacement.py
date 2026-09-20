"""The radial study's decision rule, tested before any arm produced a number.

The gate is the part worth pinning: ZERO re-renders the source meshes displaced by
zero, so it must reproduce the source. At a 1.42% floor almost any real effect
looks significant, which is exactly when a broken rebuild path would be invisible.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyse_radial_displacement.py"
BASE = 1_000_000


def _arm(tmp_path: Path, name: str, value: float) -> str:
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps({"summary": {"total_fg_pixels": value}}))
    return f"{name}={p}"


def run(tmp_path, *, zero, inn=None, out=None, extra=()):
    args = [
        sys.executable,
        str(SCRIPT),
        _arm(tmp_path, "baseline", BASE),
        _arm(tmp_path, "zero", zero),
    ]
    if inn is not None:
        args.append(_arm(tmp_path, "in", inn))
    if out is not None:
        args.append(_arm(tmp_path, "out", out))
    args += list(extra)
    return subprocess.run(args, capture_output=True, text=True)


def test_drift_outside_the_floor_is_reported_but_does_not_void(tmp_path):
    """AMENDED 2026-09-19, before any arm scored. baseline was rendered on an
    older villa tree, so a mismatch can be render-code drift rather than a broken
    rebuild -- and this number cannot tell them apart. IN/OUT are measured against
    ZERO on one pinned tree, so they stay interpretable either way."""
    r = run(tmp_path, zero=BASE * 0.90, inn=BASE * 0.81, out=BASE * 0.90)
    assert r.returncode == 0
    assert "OUTSIDE the floor" in r.stdout
    assert "not separable" in r.stdout.lower()
    assert "SUFFICIENT" in r.stdout, "IN vs ZERO must still be evaluated"


def test_drift_within_the_floor_is_reported_as_clean(tmp_path):
    r = run(tmp_path, zero=BASE * 1.005, inn=BASE * 0.90, out=BASE * 1.02)
    assert r.returncode == 0
    assert "within the floor" in r.stdout


def test_effects_are_measured_against_zero_not_baseline(tmp_path):
    """THE amendment. With baseline 1e6 and ZERO 0.9e6, an IN of 0.81e6 is -10%
    against ZERO and -19% against baseline. Only the former is the manipulation."""
    r = run(tmp_path, zero=BASE * 0.90, inn=BASE * 0.81, out=BASE * 0.90)
    assert "-10.00%" in r.stdout, r.stdout
    assert "-19" not in r.stdout


def test_in_inside_the_registered_band_is_sufficient(tmp_path):
    r = run(tmp_path, zero=BASE, inn=BASE * 0.90, out=BASE)
    assert "SUFFICIENT" in r.stdout


def test_in_below_the_floor_is_not_the_cause(tmp_path):
    r = run(tmp_path, zero=BASE, inn=BASE * 0.999, out=BASE)
    assert "NOT THE CAUSE" in r.stdout


def test_in_far_outside_the_band_is_a_different_effect(tmp_path):
    r = run(tmp_path, zero=BASE, inn=BASE * 0.50, out=BASE)
    assert "DIFFERENT EFFECT" in r.stdout


def test_partial_sample_is_refused(tmp_path):
    r = run(tmp_path, zero=BASE, inn=BASE * 0.9)  # no OUT
    assert r.returncode != 0
    assert "refused" in (r.stdout + r.stderr)


def test_allow_partial_reports_the_gate_only(tmp_path):
    r = run(tmp_path, zero=BASE, extra=("--allow-partial",))
    assert r.returncode == 0
    assert "Drift check only" in r.stdout
    assert "VERDICT: SUFFICIENT" not in r.stdout


def test_the_conservative_floor_is_used():
    """1.42% and 0.0016% were both measured; using the tighter one would
    overstate every result in the study."""
    src = SCRIPT.read_text()
    assert "PIPELINE_FLOOR = 0.0142" in src
