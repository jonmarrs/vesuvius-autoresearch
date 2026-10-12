"""Every number in the #1934 reply draft must match finding 84's or 85's artifact (same discipline as the filing tests)."""

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_DRAFT = _REPO / "docs/VILLA_DRAFT_1934_afv_generator.md"
_F85 = _REPO / "reports/afv_generator_entrant.json"
_F84 = _REPO / "reports/fiber_miss_diagnostic.json"
_NEW_S5 = ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")

pytestmark = pytest.mark.skipif(
    not (_DRAFT.exists() and _F85.exists() and _F84.exists()),
    reason="draft or source artifact absent",
)


def _text() -> str:
    return " ".join(_DRAFT.read_text().split())


def test_run_identity_matches_the_measured_run():
    d, txt = json.loads(_F85.read_text()), _text()
    s = d["settings"]
    assert (
        d["status"] == "OK" and not d["failed_runs"] and len(d["generator_rows"]) == 21
    )
    assert (
        d["revision"].startswith("e189af75")
        and "`Qualzz20/afv_fiber_9um` at `e189af75`" in txt
    )
    assert (
        f"threshold {s['threshold_percent']:.0f}%, {s['block_size']} blocks, "
        f"{s['min_length_voxels']:.0f}-voxel minimum length, black distance {s['black_distance_voxels']:.0f}, "
        f"{s['max_join_angle_degrees']:.0f}° joins, no `--extend`" in txt
    )
    assert not s["extend"] and not s["mirror"]
    n = {
        p: sum(k.startswith(p) for k in d["generator_rows"])
        for p in ("s1_", "s3_", "s5_")
    }
    assert (
        f"{n['s1_']} from Scroll 1, {n['s3_']} from Scroll 3 and {n['s5_']} from Scroll 5"
        in txt
    )


def test_coverage_numbers_match_finding_85():
    rows, txt = json.loads(_F85.read_text())["generator_rows"], _text()
    other = [r["coverage"] for k, r in rows.items() if k not in _NEW_S5]
    assert f"{min(other):.2f}–{max(other):.2f} on {len(other)} cubes" in txt
    a, b = (rows[k] for k in _NEW_S5)
    assert (
        f"**{a['coverage']:.2f} and {b['coverage']:.2f} on two Scroll 5 cubes from Dataset004**"
        in txt
    )
    assert (
        f"{a['n_fibers_in_afv']} and {b['n_fibers_in_afv']} fibers, against {a['n_gt_fibers']} and "
        f"{b['n_gt_fibers']} hand-traced" in txt
    )


def test_base_model_hard_miss_matches_finding_84():
    cubes, txt = json.loads(_F84.read_text())["cubes"], _text()
    hard = [100 * (1 - cubes[k]["sweep"]["coverage"]["0.05"]) for k in _NEW_S5]
    assert f"within 2 voxels of {hard[0]:.0f}% and {hard[1]:.0f}% of the fiber" in txt
    # finding 82: fiber_hz_vt's training fingerprint holds every non-held-out ScrollGT cube
    n_in = sum(c["split"] != "held_out" for c in cubes.values())
    assert f"`fiber_hz_vt` trained on {n_in} of these cubes" in txt
