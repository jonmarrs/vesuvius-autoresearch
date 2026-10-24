"""reports/neural_tracer_ct_context.md (finding 97): every figure from reports/neural_tracer_ct_context.json."""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_ct_context as cc  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_ct_context.json").read_text())
REPORT = " ".join((ROOT / "reports/neural_tracer_ct_context.md").read_text().split())
PEN, COV = cc.PEN, cc.COV
NOW, F91, NOW4, F94 = (
    D["rows_tol2"],
    D["finding_91_rows_tol2"],
    D["rows_tol4"],
    D["finding_94_rows_tol4"],
)
OURS, OURS4 = D["our_tracer_tol2"], D["our_tracer_tol4"]
IN_SAMPLE = cc.IN_SAMPLE + cc.S1_CUBES
HELD_OUT = [c for c in cc.CUBES if c not in cc.IN_SAMPLE]


def _span(vals, fmt="{:.3f}"):
    return f"{fmt.format(min(vals))}–{fmt.format(max(vals))}"


def _dropped_before(c):
    f = D["finding_96_records"][c]
    return f["no_heading"] / f["dots"]


def _out(row):
    return row["pred_length"] / row["gt_length"]


def test_the_run_is_complete_and_identical_where_it_must_be():
    assert D["status"] == D["status_scroll1"] == "OK"
    assert (
        D["smoke_identical"] is True and not D["identity_problems"] and not D["failed"]
    )
    assert list(NOW) == cc.ALL_CUBES and D["margin_ct_voxels"] == 128
    # the same seed dots as finding 91 on every cube; only their headings changed
    assert all(
        D["records"][c]["dots"] == D["finding_96_records"][c]["dots"]
        for c in cc.ALL_CUBES
    )
    near = {c: D["records"][c]["min_seed_face_distance_grid"] for c in cc.ALL_CUBES}
    assert {c for c, v in near.items() if v == 0} == set(cc.ALL_CUBES) - set(HELD_OUT)
    assert [near[c] for c in HELD_OUT] == [1.0, 2.0]
    assert {
        D["finding_96_records"][c]["min_seed_face_distance_grid"] for c in cc.ALL_CUBES
    } == {19.0}
    assert (
        "Here it lies 0 voxels from a face on eight cubes, and 1 and 2 on the two held-out ones."
        in REPORT
    )


def test_the_table_is_the_json():
    for c in cc.ALL_CUBES:
        t2, t4 = OURS[c][PEN], OURS4[c][PEN]

        def bold(v, ours):
            return f"**{v:.2f}**" if v > ours else f"{v:.2f}"

        split = "in sample" if c in IN_SAMPLE else "held out"
        row = (
            f"| {c.removesuffix('_256')} | {split} | {_dropped_before(c):.3f} → {D['records'][c]['no_heading_share']:.3f} | "
            f"{F91[c][COV]:.3f} → {NOW[c][COV]:.3f} | {_out(F91[c]):.2f} → {_out(NOW[c]):.2f} | "
            f"{F91[c][PEN]:.2f} → {bold(NOW[c][PEN], t2)} ({t2:.2f}) | {F94[c][PEN]:.2f} → {bold(NOW4[c][PEN], t4)} ({t4:.2f}) |"
        )
        assert row in REPORT, c


def test_the_predictions_and_their_ranges():
    for v, cubes, label in (
        (D, cc.CUBES, "Scroll 5"),
        (D["scroll1"], cc.S1_CUBES, "Scroll 1"),
    ):
        assert v["prediction_P1"] and v["prediction_P2"] and v["prediction_P3"], label
        assert v["reading"].startswith(
            "the cube-only protocol held the neural tracer back"
        ), label
        assert v["reading"] in REPORT
        nh, f = v["no_heading_share"], v["coverage_factor"]
        assert f"**held** ({_span(nh.values())})" in REPORT, label
        assert (
            f"**held** (×{_span(f.values(), '{:.2f}')}, median {v['median_coverage_factor']:.2f})"
            in REPORT
        ), label
        assert (
            f"**held** ({_span(v['pred_over_gt_in_sample'].values(), '{:.2f}')})"
            in REPORT
        ), label
    before = [_dropped_before(c) for c in IN_SAMPLE]
    after = [D["records"][c]["no_heading_share"] for c in IN_SAMPLE]
    assert (
        f"falls from {_span(before)} to {_span(after)} on the eight in-sample cubes, and from "
        f"{_span([_dropped_before(c) for c in HELD_OUT])} to {_span([D['records'][c]['no_heading_share'] for c in HELD_OUT])} "
        "on the two held-out ones" in REPORT
    )
    factors = [NOW[c][COV] / F91[c][COV] for c in cc.ALL_CUBES]
    assert f"it rises {_span(factors, '{:.2f}')}× on every cube" in REPORT
    assert (
        f"its coverage is {_span(factors, '{:.2f}')} times its published row on all ten"
        in REPORT
    )
    assert (
        f"on the eight in-sample cubes it is now {_span([_out(NOW[c]) for c in IN_SAMPLE], '{:.2f}')} of the "
        "ground-truth length" in REPORT
    )


def test_the_descriptive_figures():
    traces = [
        D["records"][c]["traced"] / D["finding_96_records"][c]["traced"]
        for c in cc.ALL_CUBES
    ]
    assert f"it starts {_span(traces, '{:.1f}')} times as many traces" in REPORT
    for rows, old, tol in ((NOW, F91, 2), (NOW4, F94, 4)):
        r = [rows[c][PEN] / old[c][PEN] for c in cc.ALL_CUBES]
        assert (
            f"{_span(r, '{:.2f}')}× at tolerance {tol} (median {statistics.median(r):.2f})"
            in REPORT
        )
    assert (
        f"essentially unchanged, {_span([NOW[c]['precision'] for c in cc.ALL_CUBES])} against "
        f"{_span([F91[c]['precision'] for c in cc.ALL_CUBES])}" in REPORT
    )
    leads4 = [c for c in cc.ALL_CUBES if NOW4[c][PEN] > OURS4[c][PEN]]
    trails4 = [c for c in cc.ALL_CUBES if c not in leads4]
    assert len(leads4) == 8 and trails4 == [
        "s5_07997_02997_05497_256",
        "s1_00997_02497_02997_256",
    ]
    assert "at tolerance 4, it leads on 8 of 10." in REPORT
    for c in trails4:
        assert (
            f"`{c.removesuffix('_256')}` ({NOW4[c][PEN]:.2f} against {OURS4[c][PEN]:.2f})"
            in REPORT
        )
    assert (
        sum(c in leads4 for c in IN_SAMPLE) == 6
        and "at tolerance 4 it leads on 6 of the 8" in REPORT
    )
    assert (
        sum(c in leads4 for c in cc.S1_CUBES) == 4
        and "it now leads at tolerance 4 on 4 of the 5 cubes" in REPORT
    )
    assert all(NOW[c][PEN] < OURS[c][PEN] for c in IN_SAMPLE)
    ratio = {c: NOW[c][PEN] / OURS[c][PEN] for c in cc.ALL_CUBES}
    before = {c: F91[c][PEN] / OURS[c][PEN] for c in cc.ALL_CUBES}
    med = lambda cubes, r: statistics.median(r[c] for c in cubes)  # noqa: E731
    s5, s1 = cc.IN_SAMPLE, cc.S1_CUBES
    assert (
        f"rises from {med(s5, before):.2f} to {med(s5, ratio):.2f} on Scroll 5's three, and from {med(s1, before):.2f} "
        f"to {med(s1, ratio):.2f} on Scroll 1's five" in REPORT
    )
    assert (
        f"a median {med(s5, ratio):.2f}–{med(s1, ratio):.2f} of our tracer on the in-sample cubes"
        in REPORT
    )
    assert (
        f"at a median {med(s1, ratio):.2f} of our tracer rather than {med(s1, before):.2f}"
        in REPORT
    )
    assert (
        f"It leads on both held-out cubes ({ratio[HELD_OUT[0]]:.2f}× and {ratio[HELD_OUT[1]]:.2f}×)"
        in REPORT
    )
    assert (
        f"still drop {D['records'][HELD_OUT[0]]['no_heading_share']:.3f} and "
        f"{D['records'][HELD_OUT[1]]['no_heading_share']:.3f} of their seed dots"
        in REPORT
    )
    # "the padding reaches 64 trace-grid voxels beyond each face, past any window's 19-voxel reach"
    assert D["box_grid"] == [64, 192] and cc.MARGIN // 2 == 64
