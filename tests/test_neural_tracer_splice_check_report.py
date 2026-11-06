"""reports/neural_tracer_link_splice.md's polyline section: every figure from
reports/evidence/neural_tracer_splice_polylines_2026-11-06.json, and that record's agreement with finding 105's."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import neural_tracer_link_splice as ls  # noqa: E402
import neural_tracer_splice_check as chk  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "reports/evidence/neural_tracer_splice_polylines_2026-11-06.json"
F105 = ROOT / "reports/neural_tracer_link_splice.json"
REPORT = ROOT / "reports/neural_tracer_link_splice.md"


def section() -> str:
    text = REPORT.read_text()
    start = text.index("## As polylines")
    return " ".join(text[start : text.index("## What it cannot say")].split())


def test_the_record_passed_its_gate_and_matches_finding_105():
    d, f = json.loads(RECORD.read_text()), json.loads(F105.read_text())["per_cube"]
    assert d["status"] == "OK" and all(v == [] for v in d["gate"].values())
    assert set(d["per_cube"]) == set(ls.HELD_OUT + ls.IN_SAMPLE)
    for c, r in d["per_cube"].items():
        assert r["splices"] == f[c]["splices"] and r["arc_limit"] == ls.SPLICE_ARC
        for t in ("tol2", "tol4"):
            assert all(r[t]["base"][k] == f[c][t]["base"][k] for k in ls.FIELDS)
            assert r[t]["labelling_gain"] == f[c][t]["splice"]["gain"]
    assert d["summary"]["held_out"] == chk.summarize(d["per_cube"], ls.HELD_OUT)


def test_the_joint_figures():
    rows = json.loads(RECORD.read_text())["per_cube"].values()
    t = section()
    dropped, joints = (
        sum(r["dropped_points"] for r in rows),
        sum(r["splices"] for r in rows),
    )
    assert (
        f"{dropped:,} points over {joints:,} joints, {dropped / joints:.1f} per joint on average"
        in t
    )
    med = [r["joint_gap_median"] for r in rows]
    assert (
        f"a median of {min(med):.2f} to {max(med):.2f} voxels, by cube (at most {max(r['joint_gap_max'] for r in rows):.2f})"
        in t
    )


def test_the_table_and_precision():
    s = json.loads(RECORD.read_text())["summary"]["held_out"]
    a, b = s["tol2"], s["tol4"]
    t = section()
    row = (f"| median ERLpen gain, polylines | {a['median_gain_poly']:.3f} ({a['cubes_gaining']} of 10 gain) | "
           f"{b['median_gain_poly']:.3f} ({b['cubes_gaining']} of 10 gain) |")  # fmt: skip
    assert row in t, row
    assert (
        f"| median ERLpen gain, finding 105's labelling | {a['median_gain_labelling']:.3f} | {b['median_gain_labelling']:.3f} |"
        in t
    )
    assert (f"| summed merges, baseline → polylines | {a['merges']['base']:,} → {a['merges']['poly']:,} | "
            f"{b['merges']['base']:,} → {b['merges']['poly']:,} |") in t  # fmt: skip
    cov = f"| median coverage change | {a['median_coverage_change']:.4f} | {b['median_coverage_change']:.4f} |"
    assert cov.replace("-", "−") in t
    assert f"a median change of +{a['median_precision_change']:.4f} at τ = 2" in t
    assert (
        a["median_gain_poly"] < a["median_gain_labelling"]
        and b["median_gain_poly"] < b["median_gain_labelling"]
    )
    assert statistics.median([a["median_gain_poly"], b["median_gain_poly"]]) > 0
