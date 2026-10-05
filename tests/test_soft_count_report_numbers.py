"""Bind finding 79's report (reports/soft_count_study.md) to the JSON its registered and secondary analyses wrote."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def _j(name: str) -> dict:
    p = REPORTS / name
    if not p.exists():
        pytest.skip(f"{name} not present")
    return json.loads(p.read_text())


@pytest.fixture(scope="module")
def report() -> str:
    return (REPORTS / "soft_count_study.md").read_text().replace("−", "-")


def test_registered_verdicts_and_predictions(report: str) -> None:
    r = _j("soft_count_study.json")
    for key in ("pinned_q1", "current_q1"):
        t = r[key]
        assert (
            f"**{t['R']:.3f}** | [{t['ci'][0]:.3f}, {t['ci'][1]:.3f}] | {t['verdict']}"
            in report
        )
    q = r["q2"]
    assert (
        f"**{q['D']:.3f}** | [{q['D_ci'][0]:.3f}, {q['D_ci'][1]:.3f}] | {q['verdict']}"
        in report
    )
    assert r["predictions"] == {"P1_pinned_less_noisy": False, "P2_no_detectable_difference": True,
                                "P3_current_less_noisy": True}  # fmt: skip
    assert r["recommend_S"] is False
    assert "**P1 FAILED**" in report and "NOT MET" in report


def test_offset_table_matches(report: str) -> None:
    for k, p in _j("soft_count_study.json")["q2"]["per_offset"].items():
        row = f"| {int(k):+d} | {p['dH']:+.4f} | {p['dS']:+.4f} | {p['a']:.2f} | {p['z_H']:.2f} | {p['z_S']:.2f} |"
        assert row in report, row


def test_threshold_table_matches(report: str) -> None:
    t = _j("soft_count_thresholds.json")
    for th in ("0.1", "0.2", "0.3", "0.4"):
        p, c, o = t["tiers"]["pinned"][th], t["tiers"]["current"][th], t["offsets"][th]
        row = (
            f"| {th} | {p['R']:.3f} [{p['ci'][0]:.3f}, {p['ci'][1]:.3f}] | {c['R']:.3f} [{c['ci'][0]:.3f}, "
            f"{c['ci'][1]:.3f}] | {o['D']:.3f} [{o['D_ci'][0]:.3f}, {o['D_ci'][1]:.3f}] |"
        )
        assert row in report, row
