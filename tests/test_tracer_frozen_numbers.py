"""Bind finding 81's report (reports/tracer_frozen_v2.md) to the JSON its registered analysis wrote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORTS = Path(__file__).resolve().parents[1] / "reports"


@pytest.fixture(scope="module")
def data() -> tuple[str, dict]:
    p = REPORTS / "tracer_frozen_v2.json"
    if not p.exists():
        pytest.skip("tracer_frozen_v2.json not present")
    return (REPORTS / "tracer_frozen_v2.md").read_text().replace("−", "-"), json.loads(
        p.read_text()
    )


def test_every_table_row_matches(data):
    report, r = data
    for cube, v in r["cubes"].items():
        f, b = v["frozen_v2"], v["baseline_v2"]
        pen = 100 * (f["erl_merge_penalized"] / b["erl_merge_penalized"] - 1)
        erl = 100 * (f["erl"] / b["erl"] - 1)
        row = (
            f"| {cube.rsplit('_', 1)[0]} | {v['size_class']} | {b['erl_merge_penalized']:.2f} → "
            f"{f['erl_merge_penalized']:.2f} | {pen:+.1f}% | {b['erl']:.2f} → {f['erl']:.2f} | {erl:+.1f}% | "
            f"{b['merges']} → {f['merges']} |"
        )
        assert row in report, row


def test_predictions_fidelity_and_descriptives(data):
    report, r = data
    assert r["n_ran"] == 11
    assert all(r["predictions"].values())
    assert (
        len(r["descriptive"]["fidelity_exact"]) == 6
        and r["descriptive"]["fidelity_inexact"] == []
    )
    assert (
        r["descriptive"]["frozen_pen_above_cc"]
        == r["descriptive"]["baseline_pen_above_cc"]
        == 4
    )
    assert (
        "**P1 HELD, 6 of 6.**" in report
        and "**P2 HELD, 11 of 11.**" in report
        and "**P3 HELD, 11 of 11.**" in report
    )
