"""scripts/neural_tracer_gt_offset.py: one entrant's shift applied to the other's centreline, and where the CT alone
puts the fibers' centres along that shift."""

import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_gt_offset as go  # noqa: E402


def _line(z, y, x0, x1, n=41):
    return np.column_stack(
        [np.full(n, float(z)), np.full(n, float(y)), np.linspace(x0, x1, n)]
    )


def test_the_other_entrants_shift_moves_a_centreline_onto_the_gt():
    gt = _line(10, 10, 2, 28)
    pred = gt + (0.0, -2.5, 0.0)  # 2.5 voxels off: inside 6, outside 2
    shift = np.array([0.0, 2.5, 0.0])  # displacement = GT - prediction
    r = go.cross_shift(gt, pred, shift)
    assert r == {"le2": 0.0, "le2_shifted": 1.0, "le2_opposite": 0.0}


def test_within_2_voxels_includes_2_as_the_placement_measure_does():
    gt = _line(10, 10, 2, 28)
    near = np.vstack([gt[:20] + (0.0, 1.75, 0.0), gt[20:] + (0.0, 2.0, 0.0)])
    assert go.cross_shift(gt, near, np.zeros(3))["le2"] == 1.0


def test_the_ct_peak_is_read_along_the_shift():
    """A bright line at y = 11, the GT at y = 10, the tracers at y = 12 (shift (0, -2, 0)): the CT peaks half way."""
    vol = np.zeros((24, 24, 32), np.float32)
    vol[10, 11, :] = 100.0
    gt = _line(10, 10, 4, 28)
    t_star, gain, profile = go.ct_peak(vol, gt, np.array([0.0, -2.0, 0.0]))
    assert t_star == 0.5 and gain > 0 and len(profile) == len(go.T)
    assert profile[list(go.T).index(0.5)] == max(profile)


def test_a_centred_gt_peaks_at_zero():
    vol = np.zeros((24, 24, 32), np.float32)
    vol[10, 10, :] = 100.0
    t_star, gain, _ = go.ct_peak(vol, _line(10, 10, 4, 28), np.array([0.0, 1.0, 0.0]))
    assert t_star == 0.0 and gain == 0.0


def test_the_mean_shift_averages_both_entrants():
    cube = {
        "neural": {"median_disp_perp_zyx": [1.0, 0.0, 2.0]},
        "generator": {"median_disp_perp_zyx": [0.0, 1.0, 1.0]},
    }
    assert np.allclose(go.mean_shift(cube), (0.5, 0.5, 1.5))


def test_the_mean_shift_refuses_an_axis_an_entrant_has_no_samples_across():
    cube = {
        "neural": {"median_disp_perp_zyx": [1.0, None, 2.0]},
        "generator": {"median_disp_perp_zyx": [0.0, 1.0, 1.0]},
    }
    with pytest.raises(ValueError, match="neural has no samples across an axis"):
        go.mean_shift(cube)


GO = json.loads((ROOT / "reports/neural_tracer_gt_offset.json").read_text())
PLJ = json.loads((ROOT / "reports/neural_tracer_placement.json").read_text())["cubes"]
REPORT = " ".join((ROOT / "reports/neural_tracer_entrant.md").read_text().split())
C, G = GO["cubes"], GO["groups"]
NORM = {c: float(np.linalg.norm(v["shift"])) for c, v in C.items()}
BIG = [c for c in G["in_sample"] if NORM[c] >= 1]


def _r(vals, fmt=".2f"):
    return f"{min(vals):{fmt}}–{max(vals):{fmt}}"


def test_the_json_is_this_scripts_on_every_cube():
    assert (
        sorted(C) == sorted(go.pl.f91.ALL)
        and GO["t"] == go.T.tolist()
        and GO["sigma"] == go.SIGMA
    )
    for c, v in C.items():
        assert np.allclose(v["shift"], go.mean_shift(PLJ[c]))
        for ent, other in (("neural", "generator"), ("generator", "neural")):
            assert v[ent]["shift_from_other"] == PLJ[c][other]["median_disp_perp_zyx"]
        assert (
            v["neural"]["le2"] == PLJ[c]["neural"]["le2"]
        )  # the same matching as the placement measure


def test_five_in_sample_cubes_and_no_scroll3_cube_pass_a_voxel():
    assert len(BIG) == 5 and "On 5 of the 11 in-sample cubes" in REPORT
    assert f"Their mean is {_r([NORM[c] for c in BIG])} voxels long there" in REPORT
    s3 = max(NORM[c] for c in G["s3"])
    rest = max(NORM[c] for c in G["in_sample"] if c not in BIG)
    assert (
        f"On every Scroll-3 cube it is at most {s3:.2f}, and on the other in-sample cubes at most {rest:.2f}"
        in REPORT
    )
    for c in BIG:
        a, b = (
            PLJ[c]["neural"]["median_disp_perp_zyx"],
            PLJ[c]["generator"]["median_disp_perp_zyx"],
        )
        assert all(
            np.sign(x) == np.sign(y)
            for x, y in zip(a, b, strict=True)
            if max(abs(x), abs(y)) >= 0.5
        )


def test_the_cross_entrant_shift_and_its_opposite():
    def d(ent, cubes, key="le2_shifted"):
        return [C[c][ent][key] - C[c][ent]["le2"] for c in cubes]

    drop = [C[c]["neural"]["le2"] - C[c]["neural"]["le2_opposite"] for c in BIG]
    assert (
        f"share within 2 voxels by {_r(d('neural', BIG))} on those 5 cubes, against {_r(d('neural', G['s3']), '.3f')} "
        f"on Scroll 3. The opposite shift lowers it by {_r(drop)}. The generator, moved by this tracer's shift, gains "
        f"{_r(d('generator', BIG))} there" in REPORT
    )
    fixed = [C[c]["neural"]["le2_shifted"] for c in BIG]
    s3 = [C[c]["neural"]["le2"] for c in G["s3"]]
    assert max(fixed) < min(s3)
    assert (
        f"this tracer's shares on those cubes ({_r(fixed)}) still trail Scroll 3's ({_r(s3)})"
        in REPORT
    )


def test_the_ct_alone():
    t = [C[c]["ct"]["t_star"] for c in BIG]
    off = [C[c]["ct"]["t_star"] * NORM[c] for c in BIG]
    gain = [C[c]["ct"]["gain"] for c in BIG]
    assert all(0 < x < 1 for x in t)
    assert (
        f"is brightest {min(t):.1f}–{max(t):.2f} of the way from the GT towards the entrants' centre on all 5"
        in REPORT
    )
    assert f"It puts the fibers' centres {_r(off)} voxels off the GT" in REPORT
    assert f"the gain in brightness is small ({_r(gain)} grey levels)" in REPORT


def test_gt_points_are_the_placement_samples():
    f = types.SimpleNamespace(
        coords=np.array([[5.0, 5.0, 1.0], [5.0, 5.0, 9.0]]), edges=np.array([[0, 1]])
    )
    assert np.array_equal(go.gt_points([f], 16), go.pl.gt_samples([f], 16)[0])
