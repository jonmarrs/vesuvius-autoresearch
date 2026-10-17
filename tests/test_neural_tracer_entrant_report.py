"""reports/neural_tracer_entrant.md (finding 91) quotes its registered analysis output correctly."""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = " ".join(
    (ROOT / "reports/neural_tracer_entrant.md").read_text().split()
)  # line wraps
RESULT = json.loads((ROOT / "reports/neural_tracer_entrant.json").read_text())
ROWS, COMP = RESULT["neural_rows"], RESULT["comparators"]
PEN, COV = "erl_merge_penalized", "coverage"
S3 = [c for c in ROWS if c.startswith("s3")]
HELDOUT_S5 = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
IN_SAMPLE = [c for c in ROWS if c not in S3 and c not in HELDOUT_S5]


def _median(cubes, value) -> float:
    return st.median(value(c) for c in cubes)


def test_the_registered_analysis_is_ok_with_every_prediction_held():
    assert RESULT["status"] == "OK" and RESULT["failed_runs"] == []
    assert all(RESULT["predictions"].values()) and len(RESULT["predictions"]) == 4
    assert RESULT["scoring_version"] == 3 and RESULT["tolerance"] == 2.0
    assert "all four held" in REPORT


def test_every_table_row_matches_the_json():
    for c, r in ROWS.items():
        t, g, k = COMP[c]["tracer"], COMP[c]["generator"], COMP[c]["cc"]
        split = "in sample" if c in IN_SAMPLE else "held out"
        row = (
            f"| {c.rsplit('_', 1)[0]} | {split} | {r[PEN]:.2f} | {r[COV]:.3f} | {r['merges']} | "
            f"{r['n_pred_instances']} | {t[PEN]:.2f} | {t[COV]:.3f} | {g[PEN]:.2f} | {g[COV]:.3f} | {k[PEN]:.2f} |"
        )
        assert row in REPORT, row


def test_prediction_counts_and_the_one_exception():
    above = lambda name: sum(ROWS[c][PEN] > COMP[c][name][PEN] for c in S3)  # noqa: E731
    assert above("generator") == above("tracer") == above("cc") == 8
    below = [c for c in S3 if not ROWS[c][COV] < COMP[c]["tracer"][COV]]
    assert below == ["s3_00994_00494_01994_512"]
    c = below[0]
    assert f"{ROWS[c][COV]:.4f} against {COMP[c]['tracer'][COV]:.4f}" in REPORT
    ratios = [ROWS[c][PEN] / COMP[c]["tracer"][PEN] for c in S3]
    assert f"by {min(ratios):.2f}–{max(ratios):.2f}×" in REPORT
    s3_median = _median(S3, lambda c: ROWS[c][COV])
    assert (
        f"{ROWS[HELDOUT_S5[0]][COV]:.3f} and {ROWS[HELDOUT_S5[1]][COV]:.3f}" in REPORT
    )
    assert f"Scroll-3 median of {s3_median:.3f}" in REPORT


def test_in_sample_cubes_all_trail_our_tracer():
    assert (
        all(ROWS[c][PEN] < COMP[c]["tracer"][PEN] for c in IN_SAMPLE)
        and len(IN_SAMPLE) == 11
    )
    assert "trails our tracer on all 11" in REPORT


def test_group_medians():
    for label, cubes in [
        ("Scroll 3, 8 cubes", S3),
        ("in sample for the mask, 11 cubes", IN_SAMPLE),
        ("held-out Scroll 5, 2 cubes", HELDOUT_S5),
    ]:
        cells = [
            f"{_median(cubes, lambda c, s=s: s(c)[PEN]):.2f} / {_median(cubes, lambda c, s=s: s(c)[COV]):.3f}"
            for s in (
                lambda c: ROWS[c],
                lambda c: COMP[c]["tracer"],
                lambda c: COMP[c]["generator"],
            )
        ]
        assert f"| {label} | " + " | ".join(cells) + " |" in REPORT


def test_descriptive_claims():
    repeat = RESULT["descriptive_repeat"]
    assert set(repeat) == {"s3_00994_00494_01994_512", "s1_00497_01497_03997_256"}
    assert all(v == 0 for r in repeat.values() for v in r["abs_difference"].values())
    # The reasons villa ccb431818 records (tracing/volume.py, trace.py, inference.py). It writes the outside-the-scan
    # stop as "outside_ct"; a key it never writes would pass any count.
    recorded = {k for r in ROWS.values() for k in r["stop_reasons"]}
    assert recorded <= {"confidence", "owned_or_live", "bounds", "outside_ct", "max_len"}
    totals = {
        k: sum(r["stop_reasons"].get(k, 0) for r in ROWS.values())
        for k in ("confidence", "owned_or_live", "bounds", "outside_ct")
    }
    assert totals["outside_ct"] == 0
    assert (
        f"{totals['confidence']:,} `confidence` stops, {totals['owned_or_live']:,} `owned_or_live` and {totals['bounds']} `bounds`"
        in REPORT
    )
    loose = RESULT["descriptive_tolerance_4"]
    assert f"{_median(S3, lambda c: loose[c]['tracer'][COV]):.3f} on Scroll 3" in REPORT
    assert (
        f"{_median(IN_SAMPLE, lambda c: loose[c]['tracer'][COV]):.3f} on the in-sample"
        in REPORT
    )
    assert (
        f"median on Scroll 3 is {_median(S3, lambda c: ROWS[c]['precision']):.3f}"
        in REPORT
    )
    assert (
        f"against the generator's {_median(S3, lambda c: COMP[c]['generator']['precision']):.3f}"
        in REPORT
    )


def test_coverage_gap_to_connected_components():
    n = _median(S3, lambda c: ROWS[c][COV])
    cc = _median(S3, lambda c: COMP[c]["cc"][COV])
    assert f"{round(100 * (1 - n / cc))}% less coverage" in REPORT
    assert f"(median {n:.3f} against {cc:.3f})" in REPORT
