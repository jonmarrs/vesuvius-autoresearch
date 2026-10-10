"""Bind finding 80's report (reports/tracer_rescore.md) to the JSON its registered analysis wrote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORTS = Path(__file__).resolve().parents[1] / "reports"


@pytest.fixture(scope="module")
def data() -> tuple[str, dict]:
    p = REPORTS / "tracer_rescore.json"
    if not p.exists():
        pytest.skip("tracer_rescore.json not present")
    return (REPORTS / "tracer_rescore.md").read_text(), json.loads(p.read_text())


def test_every_table_row_matches(data):
    report, r = data
    for cube, v in r["cubes"].items():
        t, c = v["tracer_v2"], v["cc_v2"]
        name = cube.rsplit("_", 1)[0]
        pen_t = f"{t['erl_merge_penalized']:.2f}"
        ratio = f"{t['erl_merge_penalized'] / c['erl_merge_penalized']:.2f}"
        if t["erl_merge_penalized"] > c["erl_merge_penalized"]:
            pen_t, ratio = f"**{pen_t}**", f"**{ratio}**"
        row = (
            f"| {name} | {v['size_class']} | {t['erl']:.2f} | {c['erl']:.2f} | {c['erl'] / t['erl']:.2f} | "
            f"{pen_t} | {c['erl_merge_penalized']:.2f} | {ratio} | {t['coverage']:.4f} |"
        )
        assert row in report, row


def test_predictions_and_fidelity(data):
    report, r = data
    assert r["n_ran"] == 11
    assert r["predictions"] == {"P1_raw_erl_below_cc_all_11": True, "P2_pen_below_cc_all_8_256": False,
                                "P3_pen_above_cc_2_of_3_512": True}  # fmt: skip
    assert r["fidelity_failed"] == []
    fid = [v["fidelity"] for v in r["cubes"].values() if v["fidelity"]]
    assert len(fid) == 6 and all(f["erl_rel"] == 0 for f in fid)
    assert (
        "**P1 HELD.**" in report
        and "**P2 FAILED.**" in report
        and "**P3 HELD, 3 of 3.**" in report
    )
