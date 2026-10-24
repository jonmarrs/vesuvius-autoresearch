"""reports/neural_tracer_ct_context_512.md (finding 98): every figure from reports/neural_tracer_ct_context_512.json, that
JSON's copies of the findings it compares with bound to them, and its verdicts recomputed by the registered rule."""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_ct_context_512 as c5  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_ct_context_512.json").read_text())
F97 = json.loads((ROOT / "reports/neural_tracer_ct_context.json").read_text())
REPORT = " ".join(
    (ROOT / "reports/neural_tracer_ct_context_512.md").read_text().split()
)
PEN, COV = c5.PEN, c5.COV
NOW, F91, NOW4, F94 = (
    D["rows_tol2"],
    D["finding_91_rows_tol2"],
    D["rows_tol4"],
    D["finding_94_rows_tol4"],
)
OURS, OURS4 = D["our_tracer_tol2"], D["our_tracer_tol4"]
S5, S3, ALL = c5.S5_CUBES, c5.S3_CUBES, c5.ALL_CUBES


def _span(vals, fmt="{:.3f}"):
    return f"{fmt.format(min(vals))}–{fmt.format(max(vals))}"


def _dropped_before(c):
    f = D["finding_96_records"][c]
    return f["no_heading"] / f["dots"]


def _dropped(c):
    return D["records"][c]["no_heading_share"]


def _out(row):
    return row["pred_length"] / row["gt_length"]


def test_the_run_is_complete_and_identical_where_it_must_be():
    assert D["status_scroll5"] == D["status_scroll3"] == "OK"
    assert D["smoke_identical"] is True and D["smoke_cube"] == c5.SMOKE
    assert not D["identity_problems"] and not D["failed"]
    assert (
        list(NOW) == ALL and D["margin_ct_voxels"] == 128 and D["box_grid"] == [64, 320]
    )
    # the same seed dots as finding 91 on every cube; only their headings changed
    assert all(
        D["records"][c]["dots"] == D["finding_96_records"][c]["dots"] for c in ALL
    )
    assert {D["records"][c]["min_seed_face_distance_grid"] for c in ALL} == {0.0}
    assert {D["finding_96_records"][c]["min_seed_face_distance_grid"] for c in ALL} == {
        19.0
    }
    assert "Here it lies 0 voxels from a face on all eleven." in REPORT
    minutes = [D["records"][c]["seconds"] / 60 for c in ALL]
    assert (
        f"all eleven runs finished, in {_span(minutes, '{:.1f}')} minutes each"
        in REPORT
    )


def test_the_copied_rows_are_the_committed_findings():
    rep = json.loads((ROOT / "reports/neural_tracer_entrant.json").read_text())
    t94 = json.loads((ROOT / "reports/tolerance4_rescore.json").read_text())
    f96 = json.loads((ROOT / "reports/neural_tracer_boundary.json").read_text())["rows"]
    for c in ALL:
        assert F91[c] == rep["neural_rows"][c], c
        assert OURS[c] == rep["comparators"][c]["tracer"], c
        assert F94[c] == t94["rows_neural"][c], c
        assert OURS4[c] == t94["rows_tracer"][c], c
        rec = D["finding_96_records"][c]
        assert {
            k: rec[k]
            for k in ("dots", "no_heading", "traced", "min_seed_face_distance_grid")
        } == {
            k: f96[c][k]
            for k in ("dots", "no_heading", "traced", "min_seed_face_distance_grid")
        }, c
        assert (
            abs(D["records"][c]["no_heading"] / D["records"][c]["dots"] - _dropped(c))
            < 1e-12
        )


def test_the_stored_verdicts_are_the_registered_rules():
    identity = {c: [] for c in ALL}
    f91_records = D["finding_96_records"]
    for name, cubes in c5.SETS.items():
        status, v = c5.outcome(cubes, identity, D["smoke_identical"], NOW, NOW4, F91, f91_records, D["records"], OURS, OURS4)  # fmt: skip
        assert (status, v) == (D[f"status_{name}"], D[name]), name


def test_the_table_is_the_json():
    for c in ALL:
        t2, t4 = OURS[c][PEN], OURS4[c][PEN]

        def bold(v, ours):
            return f"**{v:.2f}**" if v > ours else f"{v:.2f}"

        split = "in sample" if c in c5.IN_SAMPLE else "held out"
        row = (
            f"| {c.removesuffix('_512')} | {split} | {_dropped_before(c):.3f} → {_dropped(c):.3f} | "
            f"{F91[c][COV]:.3f} → {NOW[c][COV]:.3f} | {_out(F91[c]):.2f} → {_out(NOW[c]):.2f} | "
            f"{F91[c][PEN]:.2f} → {bold(NOW[c][PEN], t2)} ({t2:.2f}) | {F94[c][PEN]:.2f} → {bold(NOW4[c][PEN], t4)} ({t4:.2f}) |"
        )
        assert row in REPORT, c


def test_the_predictions_and_their_ranges():
    for name, cubes, label in (
        ("scroll5", S5, "Scroll 5"),
        ("scroll3", S3, "Scroll 3"),
    ):
        v = D[name]
        assert v["prediction_P1"] and v["prediction_P2"] and v["prediction_P3"], label
        assert (
            v["reading"].startswith(
                "on the 512³ cubes too the cube-only protocol held it back"
            )
            and v["reading"] in REPORT
        )
        assert f"**held** ({_span(v['no_heading_share'].values())})" in REPORT, label
        f = v["coverage_factor"]
        assert (
            f"**held** (×{_span(f.values(), '{:.2f}')}, median {v['median_coverage_factor']:.2f})"
            in REPORT
        ), label
    assert (
        D["scroll5"]["prediction_P4"] is None and D["scroll3"]["prediction_P4"] is True
    )
    assert (
        sum(_dropped(c) < c5.P4_BELOW for c in S3) == 8
        and "**held** (8 of 8)" in REPORT
    )
    assert (
        f"falls from {_span([_dropped_before(c) for c in S5])} to {_span([_dropped(c) for c in S5])} on the three "
        f"in-sample Scroll-5 cubes, and from {_span([_dropped_before(c) for c in S3])} to "
        f"{_span([_dropped(c) for c in S3])} on the eight held-out Scroll-3 ones"
        in REPORT
    )
    factors = [NOW[c][COV] / F91[c][COV] for c in ALL]
    small = [
        F97["rows_tol2"][c][COV] / F97["finding_91_rows_tol2"][c][COV]
        for c in F97["rows_tol2"]
    ]
    assert (
        f"it rises {_span(factors, '{:.2f}')}× on every cube, against {_span(small, '{:.2f}')}× on the 256³ cubes"
        in REPORT
    )
    meds = sorted(D[n]["median_coverage_factor"] for n in c5.SETS)
    assert (
        f"The medians are {meds[1]:.2f} and {meds[0]:.2f}." in REPORT
        and "estimated a median coverage factor of about 1.36" in REPORT
    )


def test_the_descriptive_figures():
    traces = [
        D["records"][c]["traced"] / D["finding_96_records"][c]["traced"] for c in ALL
    ]
    assert f"it starts {_span(traces, '{:.2f}')} times as many traces" in REPORT
    for rows, old, tol in ((NOW, F91, 2), (NOW4, F94, 4)):
        r = [rows[c][PEN] / old[c][PEN] for c in ALL]
        assert (
            f"{_span(r, '{:.2f}')}× at tolerance {tol} (median {statistics.median(r):.2f})"
            in REPORT
        )
    assert (
        f"essentially unchanged, {_span([NOW[c]['precision'] for c in ALL])} against "
        f"{_span([F91[c]['precision'] for c in ALL])}" in REPORT
    )
    assert (
        f"{_span([_out(NOW[c]) for c in ALL], '{:.2f}')} of the ground-truth length, against "
        f"{_span([_out(F91[c]) for c in ALL], '{:.2f}')}" in REPORT
    )

    def med(rows, ours, cubes):
        return statistics.median(rows[c][PEN] / ours[c][PEN] for c in cubes)

    assert (
        f"on Scroll 5 its median ratio to our tracer rises from {med(F91, OURS, S5):.2f} to {med(NOW, OURS, S5):.2f}. "
        f"On Scroll 3 it rises from {med(F91, OURS, S3):.2f} to {med(NOW, OURS, S3):.2f}"
        in REPORT
    )
    assert (
        f"at tolerance 4, from {med(F94, OURS4, S5):.2f} to {med(NOW4, OURS4, S5):.2f} on Scroll 5, and from "
        f"{med(F94, OURS4, S3):.2f} to {med(NOW4, OURS4, S3):.2f} on Scroll 3" in REPORT
    )
    # P3's ranking, as the table bolds it
    assert all(NOW4[c][PEN] > OURS4[c][PEN] for c in ALL)
    assert all(NOW[c][PEN] > OURS[c][PEN] for c in S3) and all(
        NOW[c][PEN] < OURS[c][PEN] for c in S5
    )
    held97 = sorted(
        F97["records"][c]["no_heading_share"]
        for c in ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")
    )
    assert (
        f"Scroll 3 keeps a small residual:** {_span([_dropped(c) for c in S3])} of its seed dots, against "
        f"{_span([_dropped(c) for c in S5])} on Scroll 5. That is far below the {held97[0]:.3f} and {held97[1]:.3f}"
        in REPORT
    )
    assert f"yet drops at most {max(_dropped(c) for c in S3):.3f}" in REPORT


def test_all_21_cubes_with_finding_97():
    def leads(rows, ours, cubes):
        return sum(rows[c][PEN] > ours[c][PEN] for c in cubes)

    small = list(F97["rows_tol2"])
    assert len(small) + len(ALL) == 21
    now4 = leads(NOW4, OURS4, ALL) + leads(
        F97["rows_tol4"], F97["our_tracer_tol4"], small
    )
    was4 = leads(F94, OURS4, ALL) + leads(
        F97["finding_94_rows_tol4"], F97["our_tracer_tol4"], small
    )
    now2 = leads(NOW, OURS, ALL) + leads(
        F97["rows_tol2"], F97["our_tracer_tol2"], small
    )
    was2 = leads(F91, OURS, ALL) + leads(
        F97["finding_91_rows_tol2"], F97["our_tracer_tol2"], small
    )
    assert (now4, was4, now2, was2) == (19, 11, 10, 8)
    assert (
        "at tolerance 4 it leads on 19 of the 21 cubes, against 11 of 21 with the cube alone"
        in REPORT
    )
    assert "at tolerance 2 it leads on 10 of 21, against 8." in REPORT
    gained = [
        c for c in small if F97["rows_tol2"][c][PEN] > F97["our_tracer_tol2"][c][PEN]
    ]
    assert sorted(gained) == ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
    s5_512 = statistics.median(NOW[c][PEN] / OURS[c][PEN] for c in S5)
    assert (
        f"at a median {s5_512:.2f} of our tracer on the 512³ cubes and 0.60–0.65 on the 256³ ones"
        in REPORT
    )
    seed = json.loads((ROOT / "reports/neural_tracer_boundary.json").read_text())[
        "rows"
    ]
    assert (
        f"({seed[ALL[0]]['seedable_share']:.3f} against {seed[small[0]]['seedable_share']:.3f})"
        in REPORT
    )
    allf = [NOW[c][COV] / F91[c][COV] for c in ALL]
    assert (
        all(f > 1 for f in allf)
        and f"and {_span(allf, '{:.2f}')}× on the 512³ ones" in REPORT
    )
