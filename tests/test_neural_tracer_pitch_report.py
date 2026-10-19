"""reports/neural_tracer_pitch.md quotes reports/neural_tracer_pitch.json, and the JSON applies the registered rule."""

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_pitch_analysis as pa  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_pitch.json").read_text())
REPORT = " ".join((ROOT / "reports/neural_tracer_pitch.md").read_text().split())
NATIVE = json.loads((ROOT / "reports/neural_tracer_entrant.json").read_text())[
    "neural_rows"
]
P, C = "erl_merge_penalized", "coverage"
ROWS, NAT, COMP, G = D["pitch_rows"], D["native_rows"], D["comparators"], D["groups"]
CUBES = sorted(ROWS)


def med(xs) -> float:
    return statistics.median(list(xs))


def test_the_run_is_complete_and_registered():
    assert (
        D["status"] == "OK" and D["failed_runs"] == [] and D["identity_problems"] == {}
    )
    assert len(CUBES) == 21 and all(ROWS[c] for c in CUBES)
    assert D["to_um"] == 9.6 and D["settings"] == pa.SETTINGS
    assert (
        "5c052f7c" in D["sources"]["registration"]
        and "12:55:34-13:24:04" in D["sources"]["traced"]
    )
    # The native rows it compares with are finding 91's, field for field.
    for c in CUBES:
        assert NAT[c] == {k: v for k, v in NATIVE[c].items() if k != "stop_reasons"}


def test_the_verdict_is_the_registered_rule_applied_to_these_rows():
    rows = {c: ROWS[c] for c in CUBES}
    assert {k: D[k] for k in pa.verdict(rows, NAT, COMP)} == pa.verdict(rows, NAT, COMP)
    assert D["predictions"] == {
        "P1_in_sample_trails_tracer_on_9_of_11": True,
        "P2_s3_leads_tracer_on_6_of_8": False,
        "P3_median_pen_ratio_within_0.85_1.15": False,
    }
    assert D["in_sample_trailing_tracer"] == [11, 11] and D["s3_leading_tracer"] == [
        0,
        8,
    ]
    assert (
        D["flips_against_tracer"] == 8 and D["published_row_moves_materially"] is True
    )
    assert (
        D["in_sample_reading"] == "pitch is not the main cause of the in-sample deficit"
    )
    assert "| **held:** 11 of 11 |" in REPORT and "| **failed:** 0 of 8 |" in REPORT
    assert f"| **failed:** {D['median_pen_ratio_pitch_over_native']:.2f} |" in REPORT
    assert (
        f"falls to a median {D['median_pen_ratio_pitch_over_native']:.2f} of the native run's"
        in REPORT
    )


def test_the_group_table():
    groups = [
        ("in sample, 256³", [c for c in G["in_sample"] if c.endswith("_256")]),
        ("in sample, 512³", [c for c in G["in_sample"] if c.endswith("_512")]),
        ("Scroll 3, 512³", G["s3"]),
        ("held-out Scroll 5, 256³", G["s5_held_out"]),
    ]
    for name, cubes in groups:
        cells = [
            str(len(cubes)),
            f"{med(ROWS[c][P] for c in cubes):.2f}",
            f"{med(NAT[c][P] for c in cubes):.2f}",
            f"{med(COMP[c]['tracer'][P] for c in cubes):.2f}",
            f"{med(COMP[c]['cc'][P] for c in cubes):.2f}",
            f"{med(ROWS[c][P] / NAT[c][P] for c in cubes):.2f}",
            f"{med(ROWS[c][C] for c in cubes):.3f}",
            f"{med(NAT[c][C] for c in cubes):.3f}",
        ]
        assert f"| {name} | " + " | ".join(cells) + " |" in REPORT, name


def test_lower_on_every_cube_with_fewer_fibers_not_worse_ones():
    pen = [ROWS[c][P] / NAT[c][P] for c in CUBES]
    cov = [ROWS[c][C] / NAT[c][C] for c in CUBES]
    assert max(pen) < 1 and max(cov) < 1
    assert (
        f"ERLpen is lower on all 21 (ratio {min(pen):.2f}–{max(pen):.2f}, median {med(pen):.2f}), and so is coverage "
        f"(ratio {min(cov):.2f}–{max(cov):.2f}, median {med(cov):.2f})" in REPORT
    )
    inst = med(ROWS[c]["n_pred_instances"] / NAT[c]["n_pred_instances"] for c in CUBES)
    prec = (
        med(ROWS[c]["precision"] for c in CUBES),
        med(NAT[c]["precision"] for c in CUBES),
    )
    assert f"The median cube has {inst:.2f} times as many instances" in REPORT
    assert (
        f"median precision is unchanged ({prec[0]:.3f} against {prec[1]:.3f})" in REPORT
    )


def test_scroll3_loses_the_most():
    s3 = G["s3"]
    to_tracer = [ROWS[c][P] / COMP[c]["tracer"][P] for c in s3]
    over_cc = sum(ROWS[c][P] > COMP[c]["cc"][P] for c in s3)
    by_group = {
        g: med(ROWS[c][P] / NAT[c][P] for c in cubes)
        for g, cubes in (("s3", s3), ("in", G["in_sample"]), ("s5", G["s5_held_out"]))
    }
    assert by_group["s3"] == min(by_group.values())
    assert (
        f"it scores {min(to_tracer):.2f}–{max(to_tracer):.2f} of our tracer's ERLpen, and leads connected components "
        f"on {over_cc} of 8 cubes" in REPORT
    )


def test_the_recommended_annotation_quotes_the_result():
    assert (
        f"it scores lower on all 21 cubes (median {D['median_pen_ratio_pitch_over_native']:.2f} of these rows) and "
        "leads our tracer on none of the Scroll-3 cubes" in REPORT
    )
    # "each is 21% longer in physical units"
    assert (
        round(100 * (pa.R - 1)) == 21
        and "each is 21% longer in physical units" in REPORT
    )
    assert (
        pa.grid_size("s1_00497_01497_03997_256"),
        pa.grid_size("s3_00994_00494_01994_512"),
    ) == (106, 211)
    assert "(106 or 211 across, against 128 or 256)" in REPORT


def test_finding_91s_scale_limit_points_here():
    f91 = " ".join((ROOT / "reports/neural_tracer_entrant.md").read_text().split())
    assert (
        f"(Measured 2026-10-19, finding 92, `neural_tracer_pitch.md`: resampled to its 9.6 µm training pitch it scores "
        f"lower on all 21 cubes, median {D['median_pen_ratio_pitch_over_native']:.2f} of these rows, and leads our "
        "tracer on none of the Scroll-3 cubes.)" in f91
    )
