"""scripts/neural_tracer_placement.py: where thin predicted centrelines sit relative to the hand-traced GT."""

import itertools
import json
import math
import statistics
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_placement as pl  # noqa: E402


def _fiber(*nodes):
    c = np.asarray(nodes, float)
    return types.SimpleNamespace(
        coords=c, edges=np.array([[i, i + 1] for i in range(len(c) - 1)])
    )


def test_gt_samples_carry_their_edge_length_and_distance_from_the_nearer_node():
    P, length, node = pl.gt_samples([_fiber((5, 5, 1), (5, 5, 9))], size=16)
    assert len(P) == 33 and np.allclose(P[:, 2], np.linspace(1, 9, 33))
    assert np.all(length == 8)
    assert (
        node[0] == node[-1] == 0 and node[16] == 4
    )  # the midpoint is 4 voxels from both nodes


def test_gt_samples_outside_the_cube_are_dropped():
    P, _, _ = pl.gt_samples([_fiber((5, 5, -4), (5, 5, 4))], size=16)
    assert P[:, 2].min() >= 0


def test_a_shift_reads_as_the_median_displacement():
    gt = pl.gt_samples([_fiber((5, 5, 0), (5, 5, 15))], size=16)
    pred = np.column_stack([np.full(41, 5.0), np.full(41, 6.5), np.linspace(2, 12, 41)])
    r = pl.placement(pred, *gt)
    assert np.allclose(r["median_disp_zyx"], (0, -1.5, 0)) and r["le2"] == 1.0
    far = pred + (
        0,
        1.5,
        0,
    )  # 3 voxels off: inside the 6-voxel radius, outside the tolerance
    assert pl.placement(far, *gt)["le2"] == 0.0


def test_samples_beyond_the_radius_are_not_counted():
    gt = pl.gt_samples([_fiber((5, 5, 0), (5, 5, 15))], size=16)
    near = np.column_stack([np.full(10, 5.0), np.full(10, 6.0), np.linspace(2, 12, 10)])
    away = near + (0, 7, 0)
    r = pl.placement(np.vstack([near, away]), *gt)
    assert r["n_matched"] == 10 and r["matched_share"] == 0.5 and r["le2"] == 1.0


def test_near_node_and_mid_edge_are_split_by_distance_from_the_nodes():
    gt = pl.gt_samples([_fiber((5, 5, 0), (5, 5, 10))], size=16)
    at_node = np.column_stack(
        [np.full(5, 5.0), np.full(5, 6.0), np.linspace(0, 1, 5)]
    )  # 1 voxel off
    mid = np.column_stack(
        [np.full(9, 5.0), np.full(9, 8.0), np.linspace(4, 6, 9)]
    )  # 3 voxels off
    r = pl.placement(np.vstack([at_node, mid]), *gt)
    assert r["near_node_le2"] == 1.0 and r["mid_edge_le2"] == 0.0
    assert r["n_near_node"] == 5 and r["n_mid_edge"] == 9


E = json.loads((ROOT / "reports/neural_tracer_entrant.json").read_text())
PL = json.loads((ROOT / "reports/neural_tracer_placement.json").read_text())
REPORT = " ".join((ROOT / "reports/neural_tracer_entrant.md").read_text().split())
SECTION = REPORT.split(
    "## Exploratory, after finding 92: what the Scroll-3 lead is made of"
)[1]
S3 = E["s3_cubes"]
S5_512 = [c for c in pl.f91.IN_SAMPLE if c.endswith("_512")]
PEN = "erl_merge_penalized"


def _row(c, ent, tol4=False):
    if tol4:
        return E["descriptive_tolerance_4"][c]["tracer" if ent == "neural" else ent]
    return E["neural_rows"][c] if ent == "neural" else E["comparators"][c][ent]


def _med(cubes, ent, key=PEN, tol4=False):
    return statistics.median(_row(c, ent, tol4)[key] for c in cubes)


def _ratio(ent, key=PEN, tol4=False):
    return _med(S3, ent, key, tol4) / _med(S5_512, ent, key, tol4)


def _exact_two_sided(a, b):
    """Mann-Whitney U by full enumeration of which values fall in b's group."""
    pooled, n = a + b, len(b)
    mean = len(a) * n / 2

    def u(bb, aa):
        return sum((x < y) + 0.5 * (x == y) for x in bb for y in aa)

    obs = abs(u(b, a) - mean)
    us = [
        abs(
            u(
                [pooled[i] for i in idx],
                [pooled[i] for i in range(len(pooled)) if i not in idx],
            )
            - mean
        )
        for idx in itertools.combinations(range(len(pooled)), n)
    ]
    return sum(x >= obs - 1e-12 for x in us) / len(us)


def test_the_json_covers_every_cube_with_both_thin_entrants():
    assert (
        sorted(PL["cubes"]) == sorted(pl.f91.ALL) and len(S5_512) == 3 and len(S3) == 8
    )
    assert PL["tolerance"] == 2.0 and PL["radius"] == 6.0
    assert all(
        set(v) == {"gt_median_edge", "neural", "generator"}
        for v in PL["cubes"].values()
    )


def test_the_table_quotes_the_512_cube_medians_and_ratios():
    names = {
        "neural": "this tracer",
        "generator": "#1934's generator",
        "tracer": "our tracer",
        "cc": "connected components",
    }
    for ent, name in names.items():
        tol4 = (
            f"{_ratio(ent, tol4=True):.2f}"
            if ent in ("neural", "generator")
            else "not scored"
        )
        row = f"| {name} | {_med(S3, ent):.2f} | {_med(S5_512, ent):.2f} | {_ratio(ent):.2f} | {tol4} |"
        assert row in SECTION, row


def test_only_the_thin_entrants_gain_and_every_scroll3_cube_is_above():
    a, b = (
        [_row(c, "neural")[PEN] for c in S3],
        [_row(c, "neural")[PEN] for c in S5_512],
    )
    assert (
        min(a) > max(b)
        and "every Scroll-3 cube scores above every in-sample 512³ one" in SECTION
    )
    p = _exact_two_sided(a, b)
    assert (
        math.isclose(p, 2 / math.comb(11, 3))
        and f"p {p:.3f}, the smallest 8 cubes against 3 allow" in SECTION
    )
    cov = (_med(S3, "cc", "coverage"), _med(S5_512, "cc", "coverage"))
    assert (
        f"connected components' coverage is {cov[0]:.3f} against {cov[1]:.3f}"
        in SECTION
    )


def test_at_tolerance_4_most_of_the_gain_goes():
    assert (
        f"falls from {_ratio('neural'):.2f} to {_ratio('neural', tol4=True):.2f} (coverage "
        f"{_ratio('neural', 'coverage'):.2f} to {_ratio('neural', 'coverage', True):.2f}, precision "
        f"{_ratio('neural', 'precision'):.2f} to {_ratio('neural', 'precision', True):.2f}), and the generator's from "
        f"{_ratio('generator'):.2f} to {_ratio('generator', tol4=True):.2f}" in SECTION
    )


def _range(cubes, ent, key="le2"):
    v = [PL["cubes"][c][ent][key] for c in cubes]
    return min(v), max(v)


def test_the_measured_shares_separate_scroll3_from_the_in_sample_cubes():
    ins = pl.f91.IN_SAMPLE
    for ent, phrase in (
        ("neural", "for this tracer"),
        ("generator", "for the generator"),
    ):
        s3, i = _range(S3, ent), _range(ins, ent)
        assert s3[0] > i[1]
        text = f"{s3[0]:.2f}–{s3[1]:.2f}" + (
            " on Scroll 3 against " if ent == "neural" else " against "
        )
        text += (
            f"{i[0]:.2f}–{i[1]:.2f}"
            + (" on the 11 in-sample cubes " if ent == "neural" else " ")
            + phrase
        )
        assert text in SECTION, text
    assert "For both, every Scroll-3 cube is above every in-sample one." in SECTION


def test_no_shift_and_not_the_node_spacing():
    worst = max(
        abs(v)
        for c in PL["cubes"].values()
        for e in ("neural", "generator")
        for v in c[e]["median_disp_zyx"]
    )
    assert worst < 1 and f"at most {worst:.2f} voxels along any axis" in SECTION
    edge = (
        statistics.median(PL["cubes"][c]["gt_median_edge"] for c in S3),
        statistics.median(PL["cubes"][c]["gt_median_edge"] for c in pl.f91.IN_SAMPLE),
    )
    assert f"a median edge of {edge[0]:.1f} voxels against {edge[1]:.1f}" in SECTION
    gap = statistics.median(
        v["neural"]["near_node_le2"] - v["neural"]["mid_edge_le2"]
        for v in PL["cubes"].values()
    )
    assert f"a median of only {gap:.2f} more often" in SECTION
    nn, ni = (
        _range(S3, "neural", "near_node_le2"),
        _range(pl.f91.IN_SAMPLE, "neural", "near_node_le2"),
    )
    assert (
        nn[0] > ni[1]
        and f"{ni[0]:.2f}–{ni[1]:.2f} against {nn[0]:.2f}–{nn[1]:.2f} for this tracer"
        in SECTION
    )
    c = PL["cubes"]["s1_08997_02997_02497_256"]
    assert (
        c["gt_median_edge"] <= min(PL["cubes"][s]["gt_median_edge"] for s in S3) + 1e-9
    )
    assert (
        f"Scroll 3's node spacing ({c['gt_median_edge']:.1f} voxels) with an in-sample share ({c['neural']['le2']:.2f})"
        in SECTION
    )


def test_the_held_out_cubes_do_not_separate_the_candidates():
    g = [f"{PL['cubes'][c]['generator']['le2']:.2f}" for c in pl.f91.S5_HELDOUT]
    n = [f"{PL['cubes'][c]['neural']['le2']:.2f}" for c in pl.f91.S5_HELDOUT]
    assert (
        f"as on Scroll 3 ({g[0]} and {g[1]})" in SECTION
        and f"as on the in-sample cubes ({n[0]} and {n[1]})" in SECTION
    )
