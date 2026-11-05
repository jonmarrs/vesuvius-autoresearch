"""reports/fiber_eigenvalue_scales_2026-11-05.md, bound to its receipt (reports/evidence/fiber_eigenvalue_scales_2026-11-05.json):
every figure the report quotes is the receipt's, rounded as printed."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "reports/fiber_eigenvalue_scales_2026-11-05.md").read_text()
REPORT = " ".join(RAW.split())
E = json.loads(
    (ROOT / "reports/evidence/fiber_eigenvalue_scales_2026-11-05.json").read_text()
)
LABELS = {
    (2, 6): "Gaussian 2 / Hessian 6",
    (1, 2): "Gaussian 1 / Hessian 2",
    (2, 3): "Gaussian 2 / Hessian 3",
}


def e4(x: float) -> str:
    """The report's four-decimal scientific form: 1.2580e-5, not 1.2580e-05."""
    mantissa, exponent = f"{x:.4e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def test_the_receipt_is_complete_and_names_its_inputs():
    assert E["complete"] is True
    assert f"`{E['ct_sha256']}`" in REPORT
    assert f"--baseline-ref {E['baseline_commit']}" in REPORT
    z, y, x = E["roi_origin_zyx"]
    dz, dy, dx = E["roi_shape_zyx"]
    assert (dz, dy, dx) == (64, 64, 64)
    assert f"`ct[{z}:{z + dz}, {y}:{y + dy}, {x}:{x + dx}]`" in REPORT
    assert "evaluates the 64³ crop" in REPORT


def test_the_table_quotes_the_receipt():
    s = E["synthetic"]
    line = (
        f"| {s['matrices']:,} synthetic matrices, seed {s['rng_seed']}, scale {s['scale']:.0e}".replace(
            "e-0", "e-"
        )
        + f" | {e4(s['baseline']['max_absolute_error'])} | {e4(s['candidate']['max_absolute_error'])} |"
    )
    assert line in RAW, line
    for run in E["public_ct"]:
        c = run["comparisons"]
        label = LABELS[(run["gauss_sigma"], run["sigma"])]
        line = f"| Public CT, {label} | {e4(c['baseline']['max_absolute_error'])} | {e4(c['candidate']['max_absolute_error'])} |"
        assert line in RAW, line


def test_the_sign_gate_and_vesselness_figures_are_the_receipts():
    s = E["synthetic"]
    assert (
        f"{s['matrices']:,} deterministic symmetric matrices scaled by 1e-5, {s['baseline']['robust_sign_mismatches']} "
        "eigenvalue signs disagreed with NumPy" in REPORT
    )
    assert s["candidate"]["robust_sign_mismatches"] == 0
    assert (
        "The candidate has zero robust sign disagreements on the synthetic sample."
        in REPORT
    )
    runs = [r["comparisons"] for r in E["public_ct"]]
    for side in ("baseline", "candidate"):
        assert all(r[side]["robust_sign_mismatches"] == 0 for r in runs)
        assert all(r[side]["vesselness_gate_disagreements"] == 0 for r in runs)
    assert "zero sign or tube-gate disagreements on this public CT crop" in REPORT
    old = max(r["baseline"]["max_absolute_vesselness_error"] for r in runs)
    new = max(r["candidate"]["max_absolute_vesselness_error"] for r in runs)
    assert (
        f"The old public-CT vesselness error is at most {e4(old)}; version 2 is within {e4(new)}."
        in REPORT
    )


def test_the_runtime_is_the_receipts():
    r = E["runtime"]
    assert f"Python {r['python']}, NumPy {r['numpy']} and SciPy {r['scipy']}" in REPORT
