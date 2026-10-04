"""Bind finding 78's report (reports/scorer_tracking_gap.md) to the JSON its scripts wrote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def _load(name: str) -> dict:
    p = REPORTS / name
    if not p.exists():
        pytest.skip(f"{name} not present")
    return json.loads(p.read_text())


@pytest.fixture(scope="module")
def report() -> str:
    return (REPORTS / "scorer_tracking_gap.md").read_text()


def test_registered_cells_match_the_table(report: str) -> None:
    for c in _load("scorer_tracking_gap.json")["cells"]:
        s, k = c["strip"], c["scorer"]
        cell = (
            f"| {c['tile']} | {c['n_tiles']} | {s['rho']:+.3f} [{s['ci'][0]:+.2f}, {s['ci'][1]:+.2f}] | "
            f"{k['rho']:+.3f} [{k['ci'][0]:+.2f}, {k['ci'][1]:+.2f}] | {c['gap']:+.3f} |"
        ).replace("-", "−")
        assert cell in report.replace("-", "−"), cell


def test_both_registered_predictions_held(report: str) -> None:
    held = _load("scorer_tracking_gap.json")["predictions_held"]
    assert all(held.values())
    assert report.count("HELD") >= 2


def test_descriptive_gap_and_independence(report: str) -> None:
    d = _load("scorer_tracking_gap_descriptive.json")
    for tile, v in d["reference"].items():
        g = v["gap_strip_minus_scorer"]
        assert (
            f"| {tile} | {g['gap']:+.3f} | [{g['ci'][0]:+.2f}, {g['ci'][1]:+.2f}] |".replace(
                "-", "−"
            )
            in report.replace("-", "−")
        )
    ind = d["arm_independence_256"]
    assert min(min(v.values()) for v in ind.values()) > 0.96
    assert f"{ind['f73_coarse_linear']['scorer']:.3f}" in report


def test_sparsity_numbers(report: str) -> None:
    p = _load("scorer_sparsity_annotated.json")["pooled"]
    assert f"**{100 * p['fg_inside']:.2f}%**" in report
    assert f"{100 * p['label_ink_inside']:.1f}%" in report
    assert f"{100 * p['precision_inside']:.1f}%" in report
    assert f"**{100 * p['recall_inside']:.1f}%**" in report
    assert f"{p['inside_over_outside']:.2f}×" in report
    assert (
        f"{100 * p['fg_inside'] / p['label_ink_inside']:.1f}% of labelled ink" in report
    )
