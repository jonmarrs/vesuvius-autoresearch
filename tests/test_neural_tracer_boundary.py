"""Finding 96 (exploratory): scripts/neural_tracer_boundary.py's arithmetic, and every figure in
reports/neural_tracer_boundary.md bound to the JSON it wrote."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import neural_tracer_boundary as nb  # noqa: E402

JSON = _REPO / "reports/neural_tracer_boundary.json"
REPORT = _REPO / "reports/neural_tracer_boundary.md"


def _flat() -> str:
    return " ".join(REPORT.read_text().split())


@pytest.mark.parametrize("n", [256, 512])
def test_the_seedable_grid_is_villas_window_condition(n):
    """villa: start = floor(scale * g) - radius >= 0 and start + 2 * radius + 1 <= n."""
    ok = [g for g in range(n // 2) if 2 * g - 38 >= 0 and 2 * g - 38 + 77 <= n]
    assert nb.seedable_grid(n) == (ok[0], ok[-1])
    assert nb.seedable_share(n) == pytest.approx((len(ok) / (n // 2)) ** 3)


def test_the_core_bounds():
    assert nb.seedable_grid(256) == (19, 108) and nb.seedable_grid(512) == (19, 236)
    assert (
        round(nb.seedable_share(256), 3) == 0.348
        and round(nb.seedable_share(512), 3) == 0.618
    )


@pytest.mark.skipif(
    not (nb.VILLA / nb.CT_STRUCTURE).exists(), reason="villa checkout absent"
)
def test_the_radius_is_villas():
    assert nb.villa_radius() == nb.RADIUS == 38


def _fiber(points):
    c = np.asarray(points, float)
    return SimpleNamespace(
        coords=c, edges=np.array([[i, i + 1] for i in range(len(c) - 1)])
    )


def test_reachable_share_counts_whole_fibers_that_touch_the_core():
    n = 100  # core: floor(coordinate) in [38, 61]
    inner = _fiber([[50, 50, 0], [50, 50, 10]])  # the core in z, y; not in x
    through = _fiber(
        [[50, 50, 30], [50, 50, 50], [50, 50, 70]]
    )  # crosses the core: reachable, all 40
    edge = _fiber([[1, 1, 1], [1, 1, 21]])
    assert nb.reachable_share([through], n) == 1.0
    assert nb.reachable_share([inner, edge], n) == 0.0
    assert nb.reachable_share([through, edge], n) == pytest.approx(40 / 60)
    outside = _fiber(
        [[50, 50, 90], [50, 50, 120]]
    )  # its one edge leaves the cube: no length
    assert nb.reachable_share([through, outside], n) == 1.0


def test_face_share_of_a_uniform_labelling_is_the_volume_share():
    lab = np.ones((100, 100, 100), np.int32)
    got, vol = nb.face_share(lab, 10)
    assert got == pytest.approx(vol) and vol == pytest.approx(1 - 0.8**3)


pytestmark_json = pytest.mark.skipif(
    not JSON.exists(), reason="finding 96 artifact absent"
)


def _d() -> dict:
    return json.loads(JSON.read_text())


def _r3(v) -> str:
    return ", ".join(f"{x:.3f}" for x in v)


@pytestmark_json
def test_the_rule_holds_on_every_cube():
    d = _d()
    assert (
        len(d["rows"]) == 21
        and d["exploratory"] is True
        and d["radius_ct_voxels"] == 38
    )
    assert {r["min_seed_face_distance_grid"] for r in d["rows"].values()} == {19.0}
    assert sum(r["size"] == 256 for r in d["rows"].values()) == 10
    assert (
        "| closest traced seed to a face | 19.00 grid voxels (38 CT) on every cube | 19.00 on every cube |"
        in _flat()
    )


@pytestmark_json
def test_the_size_table_is_the_json():
    by, flat = _d()["by_size"], _flat()
    labels = {
        "seedable_share": "share of the cube where a seed's window fits",
        "no_heading_share": "share of seed dots dropped as `no_heading`",
        "reachable_share": "share of ground-truth length on fibers with a node where a seed's window fits",
        "neural_coverage": "neural tracer's coverage (finding 91, tolerance 2)",
        "neural_pred_over_gt": "neural tracer's predicted over ground-truth length",
        "tracer_coverage": "our tracer's coverage (ScrollGT's rows, findings 80 and 83)",
    }
    for key, label in labels.items():
        a, b, sep = by[key]["256"], by[key]["512"], by[key]["separate"]
        cells = (
            [f"{a[0]:.3f}", f"{b[0]:.3f}"]
            if key == "seedable_share"
            else [_r3(a), _r3(b)]
        )
        assert (
            f"| {label} | {cells[0]} | {cells[1]} | {'yes' if sep else 'no'} |" in flat
        ), key
    assert not by["tracer_coverage"]["separate"]
    assert all(by[k]["separate"] for k in labels if k != "tracer_coverage")


@pytestmark_json
def test_the_scroll_5_table_is_the_json():
    rows, flat = _d()["rows"], _flat()
    labels = {
        "no_heading_share": "dropped as `no_heading`",
        "reachable_share": "ground-truth length on fibers a seed can reach",
        "neural_coverage": "neural tracer's coverage",
        "neural_pred_over_gt": "neural tracer's predicted over ground-truth length",
        "tracer_coverage": "our tracer's coverage",
    }
    groups = {
        n: [r for c, r in rows.items() if c.startswith("s5_") and r["size"] == n and r["split"] != "held_out"]
        for n in (256, 512)
    }  # fmt: skip
    assert len(groups[256]) == len(groups[512]) == 3
    for key, label in labels.items():
        cell = [
            f"{min(r[key] for r in g):.3f}–{max(r[key] for r in g):.3f}"
            for g in groups.values()
        ]
        assert f"| {label} | {cell[0]} | {cell[1]} |" in flat, key


@pytestmark_json
def test_the_prose_figures_are_the_json():
    d, flat = _d(), _flat()
    by, rows = d["by_size"], d["rows"]
    reach = by["reachable_share"]
    assert (
        f"(median {reach['256'][1]:.3f} reachable)" in flat
        and f"(median {reach['512'][1]:.3f})" in flat
    )
    cov = by["neural_coverage"]
    assert (
        f"(median {cov['256'][1]:.3f} against {reach['256'][1]:.3f} on 256³ cubes, "
        f"{cov['512'][1]:.3f} against {reach['512'][1]:.3f} on 512³)" in flat
    )
    lab, vol = d["tracer_face_share"]["labelled"], d["tracer_face_share"]["volume"]
    assert d["tracer_face_share"]["cube"] == "s5_07997_02997_05497_256"
    assert f"{100 * lab:.1f}% of its labelled voxels on `s5_07997_02997_05497_256` lie within 38 voxels of a face, against {100 * vol:.1f}%" in flat  # fmt: skip
    lo, hi = d["seedable_grid"]["256"], d["seedable_grid"]["512"]
    assert (
        f"coordinates {lo[0]}–{lo[1]} of a 256³ cube's 128, and {hi[0]}–{hi[1]} of a 512³ cube's 256"
        in flat
    )
    trailing = [c for c in rows if not c.startswith("s3_")]
    assert len(trailing) == 13 and sum(rows[c]["size"] == 256 for c in trailing) == 10
    assert (
        "Ten of the 13 cubes on which ScrollGT says it trails our tracer are 256³."
        in flat
    )
    pred = by["neural_pred_over_gt"]
    assert (
        0.4 < pred["256"][1] / pred["512"][1] < 0.6
    )  # "about half the centreline per unit of ground truth"
    assert statistics.median([pred["256"][1], pred["512"][1]]) > 0
