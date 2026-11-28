"""Finding 140's runner: which blocks meet, the registered verdict lines, and the summary's arithmetic."""

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "afv_generator_seam_repair", ROOT / "scripts/afv_generator_seam_repair.py"
)
assert _spec and _spec.loader
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)
REG = " ".join(
    (ROOT / "docs/preregistration/2026-11-27_afv_generator_seam_repair.md")
    .read_text()
    .split()
)


def test_blocks_meet_only_their_neighbours():
    # A 2 x 1 x 2 grid of 256-blocks with the CLI's 32-voxel margin, x fastest.
    boxes = []
    for z in (0, 256):
        for x in (0, 256):
            lo = np.maximum(np.array([x, 0, z]) - 32, 0)
            boxes.append(
                (
                    lo,
                    np.minimum(np.array([x, 256, z]) + 256 + 32, 512),
                    None,
                    None,
                    None,
                    None,
                )
            )
    assert sr.meeting(boxes) == [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]]
    far = [
        (np.array([0, 0, 0]), np.array([100, 100, 100])),
        (np.array([200, 0, 0]), np.array([300, 100, 100])),
    ]
    assert sr.meeting([(*b, None, None, None, None) for b in far]) == [[], []]


def _row(erl4, erl2=1.0, merges=10, cov=0.5, dup=0.1, lost=5):
    return {
        "tol4": {"erl_merge_penalized": erl4, "coverage": cov, "merges": merges},
        "tol2": {"erl_merge_penalized": erl2, "coverage": cov, "merges": merges},
        "duplicated_share": dup,
        "crossings": {"whole": 1, "broken": 1, "lost": lost},
    }


def _results(gains, lost_repaired=20):
    out = {}
    for i, g in enumerate(gains):
        out[f"c{i}"] = {
            "rows": {
                "main": _row(10.0),
                "trim": _row(11.0, cov=0.45),
                "repaired": _row(
                    10.0 * (1 + g), cov=0.48, lost=lost_repaired // len(gains)
                ),
            }
        }
    return out


def test_the_verdict_lines_are_the_registrations():
    assert (sr.UP_LINE, sr.KEEP_MEDIAN, sr.LOSE_MEDIAN, sr.LOST_LINE) == (
        7,
        0.06,
        0.03,
        190,
    )
    assert (
        "ERL at tolerance 4 up over main on at least 7 of 8, median gain at least +6%, and lost crossings at most 190"
        in REG
    )
    assert "median gain under +3%, or up on 5 or fewer" in REG
    keeps = sr.summary(_results([0.1] * 7 + [-0.01]))
    assert (
        keeps["up_tol4"] == 7
        and keeps["median_gain_tol4"] == 0.1
        and sr.verdict(keeps) == "REPAIR_KEEPS_THE_GAIN"
    )
    too_many_lost = sr.summary(_results([0.1] * 8, lost_repaired=8 * 25))
    assert (
        too_many_lost["lost_crossings"]["repaired"] == 200
        and sr.verdict(too_many_lost) == "REPAIR_PARTLY"
    )
    assert sr.verdict(sr.summary(_results([0.02] * 8))) == "REPAIR_LOSES_THE_GAIN"
    assert (
        sr.verdict(sr.summary(_results([0.1] * 5 + [-0.1] * 3)))
        == "REPAIR_LOSES_THE_GAIN"
    )


def test_the_zone_addendum_gates_on_finding_107s_own_trim():
    import afv_generator_default_zone as dz

    assert (
        "Addendum 1 (2026-11-27, after the eighteen cubes, before the 1024³ zone runs)"
        in REG
    )
    assert "must equal finding 107's recorded rows" in REG
    # finding 107's zone trim is the zone form finding 109 and this finding's Scrolls 1 and 5 used
    assert dz.PATCHED_STITCH_SHA256.startswith("362b78b12b2abf1b")
    assert (dz.ZONE, dz.BLOCK, dz.MARGIN) == (1024, 512, 32)


def test_the_summary_compares_each_arm_with_main():
    s = sr.summary(_results([0.1] * 8))
    assert s["lost_crossings"] == {"main": 40, "trim": 40, "repaired": 16}
    assert s["coverage_tol4_median_change"] == {"trim": -0.1, "repaired": -0.04}
    assert s["merges_tol2"] == {"main": 80, "trim": 80, "repaired": 80}
