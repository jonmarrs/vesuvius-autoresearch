"""reports/neural_tracer_heading_residual.md (finding 99): every figure from its JSONs, and the run checked against
findings 97 and 98's runs and ScrollGT's ground truth."""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_heading_residual as hr  # noqa: E402

D = json.loads((ROOT / "reports/neural_tracer_heading_residual.json").read_text())
P1 = json.loads(
    (ROOT / "reports/neural_tracer_heading_residual_pass1.json").read_text()
)
REPORT = " ".join(
    (ROOT / "reports/neural_tracer_heading_residual.md").read_text().split()
)
C = D["cubes"]
HELD = sorted(hr.HELD_256)
S3 = [c for c in C if c.startswith("s3_")]
IN = [c for c in C if c not in HELD and c not in S3]
TEN = HELD + S3


def dis(c):
    return C[c]["near_gt"]["disagree"]


def span(vals, fmt="{:.2f}"):
    return f"{fmt.format(min(vals))}–{fmt.format(max(vals))}"


def steep(c):
    r = C[c]
    return (
        sum(
            (r["near_gt"][k]["steep_sheet_share"] or 0) * r["counts"][k]
            for k in ("disagree", "ok")
        )
        / r["classified"]
    )


def _rank(v):
    s = sorted(v)
    return [s.index(x) + (s.count(x) - 1) / 2 for x in v]


def test_the_run_is_the_runs_it_explains():
    assert (
        set(C) == set(P1["cubes"]) and len(C) == 21 and len(IN) == 11 and len(S3) == 8
    )
    sg = hr.pl.f91.SG / "data"
    for c, r in C.items():
        assert r["dots"] == r["recorded"]["dots"], (
            c
        )  # villa's tile_dots re-derives the run's dots
        assert r["classified"] == (r["dots"] if c.endswith("_256") else hr.SAMPLE), c
        assert r["counts"] == P1["cubes"][c]["counts"], c  # pass 2 reproduces pass 1
        assert r["villa_check"] == {
            "dots": 50,
            "mismatches": 0,
            "normal_mismatches": 0,
        }, c
        assert P1["cubes"][c]["villa_check"] == {"dots": 50, "mismatches": 0}, c
        assert r["written_seeds"]["failing"] == r["written_seeds"]["unmatched"] == 0, c
        assert (
            r["skeleton_sha256"]
            == hashlib.sha256(
                (sg / f"fibers_{c}" / "skeleton.npz").read_bytes()
            ).hexdigest()
        )
        if c.endswith(
            "_256"
        ):  # every dot classified: the run's drops, of the dots it offered, are among them
            assert r["recorded"]["no_heading"] <= r["counts"]["disagree"], c
    seeds = sum(r["written_seeds"]["checked"] for r in C.values())
    assert f"all {seeds:,} written seeds checked match a dot and pass" in REPORT
    n256 = sum(r["classified"] for c, r in C.items() if c.endswith("_256"))
    big = [r["dots"] for c, r in C.items() if c.endswith("_512")]
    assert f"Every dot of the 256³ cubes is classified ({n256:,})" in REPORT
    assert (
        f"a fixed random sample of {hr.SAMPLE:,} on each 512³ cube (of {min(big):,}–{max(big):,})"
        in REPORT
    )


def test_every_drop_is_the_agreement_test():
    for c, r in C.items():
        assert (
            r["counts"]["edge"]
            == r["counts"]["no_normal"]
            == r["counts"]["ambiguous"]
            == 0
        ), c
        assert r["counts"]["disagree"] > 0, c
    assert "On all 21 cubes, every dropped dot fails the last" in REPORT
    assert (
        hr.AGREE_DEGREES == 35.0
        and "lies more than 35° from the dot's direction" in REPORT
    )


def test_the_answer():
    def s(key, cubes, fmt="{:.0f}"):
        return span([dis(c)[key] for c in cubes], fmt)

    assert (
        f"a median {s('median_presence_to_gt', HELD)}° from the ground-truth tangent on the two held-out"
        in REPORT
    )
    assert f"and {s('median_presence_to_gt', S3)}° on Scroll 3" in REPORT
    held_ct = {round(dis(c)["median_ct_axis_to_gt"]) for c in HELD}
    assert len(held_ct) == 1
    assert (
        f"The CT's axis lies {held_ct.pop()}° and {s('median_ct_axis_to_gt', S3)}° from it"
        in REPORT
    )
    assert (
        f"closer of the two on {s('ct_axis_closer_share', HELD, '{:.2f}')} and "
        f"{s('ct_axis_closer_share', S3, '{:.2f}')} of those dots" in REPORT
    )
    for c, r in C.items():
        for k in ("disagree", "ok"):
            assert r["near_gt"][k]["unclear_sheet_share"] == 0, (c, k)
    assert (
        hr.MIN_EIGENGAP == 0.05
        and "no relative eigengap is below villa's `MIN_EIGENGAP`, 0.05" in REPORT
    )
    assert (
        f"lies a median {s('median_gt_out_of_ct_sheet', TEN)}° out of that sheet"
        in REPORT
    )
    assert (
        f"tilted a median {s('median_sheet_tilt', TEN)}° from vertical at the dropped dots"
        in REPORT
    )
    h = [C[c]["by_family"]["H"]["disagree"] / C[c]["counts"]["disagree"] for c in TEN]
    assert f"{span(h)} of those cubes' dropped dots are H dots" in REPORT
    assert hr.STEEP_TILT == 45.0


def test_per_cube_and_pooled():
    xs, ys = [steep(c) for c in C], [C[c]["dropped_share"] for c in C]
    r, rho = (
        statistics.correlation(xs, ys),
        statistics.correlation(_rank(xs), _rank(ys)),
    )
    assert f"Pearson r {r:.2f} over the 21 cubes, Spearman {rho:.2f}" in REPORT
    held = sorted(steep(c) for c in HELD)
    assert (
        f"That share is {held[0]:.2f} and {held[1]:.2f} on the two held-out Scroll-5 cubes"
        in REPORT
    )
    assert (
        f"{span([steep(c) for c in S3])} on Scroll 3, and at most {max(steep(c) for c in IN):.2f} in sample"
        in REPORT
    )
    in_steep, out_steep, in_rest, out_rest = 0.0, 0.0, 0.0, 0.0
    for c, row in C.items():
        for k in ("disagree", "ok"):
            n, sh = row["counts"][k], row["near_gt"][k]["steep_sheet_share"] or 0
            if k == "disagree":
                in_steep, in_rest = in_steep + n * sh, in_rest + n * (1 - sh)
            else:
                out_steep, out_rest = out_steep + n * sh, out_rest + n * (1 - sh)
    pooled = (in_steep / (in_steep + out_steep), in_rest / (in_rest + out_rest))
    assert (
        f"it drops {pooled[0]:.3f} of the dots in such sheets and {pooled[1]:.3f} of the rest"
        in REPORT
    )
    lo = min(S3, key=steep)
    assert (
        lo == "s3_02994_02494_01994_512"
        and max(S3, key=lambda c: C[c]["dropped_share"]) == "s3_00994_02494_01494_512"
    )
    assert (
        f"it drops {C[lo]['dropped_share']:.3f} of the dots on the cube with the fewest steep ones and "
        f"{C['s3_00994_02494_01494_512']['dropped_share']:.3f} on one with many"
        in REPORT
    )
    assert (
        "nearly all the in-sample dots' are" in REPORT
        and max(steep(c) for c in IN) < 0.05
    )


def test_the_table_is_the_json():
    for c in C:
        r, a, o = C[c], dis(c), C[c]["near_gt"]["ok"]
        split = "in sample" if c in IN else "held out"
        rec = r["recorded"]["no_heading"] / r["recorded"]["dots"]
        row = (
            f"| {c} | {split} | {rec:.3f} | {r['dropped_share']:.3f} ({r['counts']['disagree']}) | {steep(c):.3f} | "
            f"{a['median_presence_to_gt']:.0f}° | {a['median_ct_axis_to_gt']:.0f}° | {a['median_sheet_tilt']:.0f}° | "
            f"{o['median_sheet_tilt']:.0f}° | {a['median_gt_out_of_ct_sheet']:.0f}° |"
        )
        assert row in REPORT, c
    n = [C[c]["counts"]["disagree"] for c in IN]
    assert f"few dots are dropped ({min(n)}–{max(n)})" in REPORT


def test_the_figures_it_starts_from():
    f97 = json.loads((ROOT / "reports/neural_tracer_ct_context.json").read_text())[
        "records"
    ]
    f98 = json.loads((ROOT / "reports/neural_tracer_ct_context_512.json").read_text())[
        "records"
    ]
    rec = {**f97, **f98}
    for (
        c,
        r,
    ) in C.items():  # the runs this classifies are the ones findings 97 and 98 recorded
        assert (
            abs(
                rec[c]["no_heading_share"]
                - r["recorded"]["no_heading"] / r["recorded"]["dots"]
            )
            < 1e-12
        ), c
    ins = [rec[c]["no_heading_share"] for c in IN]
    assert f"fell to {span(ins, '{:.3f}')}" in REPORT
    held = sorted(rec[c]["no_heading_share"] for c in HELD)
    assert (
        f"It stayed at {held[0]:.3f} and {held[1]:.3f} on the two held-out Scroll-5 256³ cubes"
        in REPORT
    )
    assert (
        f"and at {span([rec[c]['no_heading_share'] for c in S3], '{:.3f}')} on Scroll 3"
        in REPORT
    )


def test_the_expectations():
    e1 = all(
        C[c]["counts"]["disagree"] == C[c]["classified"] - C[c]["counts"]["ok"]
        for c in HELD
    ) and not any(C[c]["counts"]["edge"] for c in HELD)
    other_way = all(
        dis(c)["ct_axis_closer_share"] < 0.5 for c in HELD
    )  # E2 said the CT's axis is the closer
    over = sorted(
        C[c]["dropped_share"]
        for c in C
        if c not in HELD and C[c]["dropped_share"] >= 0.10
    )
    assert e1 and other_way and len(over) == 2
    assert (
        "| E1: on the two held-out 256³ cubes most of the dropped dots are `disagree`, and none `edge` | **held**"
        in REPORT
    )
    assert "**failed**, the other way round" in REPORT
    assert f"**failed** on two Scroll-3 cubes ({over[0]:.3f}, {over[1]:.3f})" in REPORT
    # the expectations in the script are the ones the report quotes
    doc = " ".join(
        (ROOT / "scripts/neural_tracer_heading_residual.py").read_text().split()
    )
    assert (
        "E1 (moderate) on the two held-out 256³ cubes most of the dropped dots are `disagree`, and none is `edge`"
        in doc
    )
    assert (
        "E3 (moderate) on every other cube fewer than 0.10 of all dots are dropped"
        in doc
    )
