"""scripts/fiber_miss_diagnostic.py on synthetic volumes: its coverage is ScrollGT's, its shift search finds a planted
offset, and its verdict refuses partial samples and failed gates."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parent.parent
_SG = _REPO.parent / "scrollgt" / "src"
needs_scrollgt = pytest.mark.skipif(
    not _SG.exists(), reason="scrollgt checkout not beside this repo"
)


@pytest.fixture(scope="module")
def mod():
    sys.path.insert(0, str(_SG))
    spec = importlib.util.spec_from_file_location(
        "fiber_miss_diagnostic", _REPO / "scripts/fiber_miss_diagnostic.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _skeleton(polylines):
    from scrollgt.fibers.skeleton_io import Fiber, Skeleton

    fibers = []
    for i, pts in enumerate(polylines):
        pts = np.asarray(pts, dtype=float)
        n = len(pts)
        fibers.append(Fiber(id=i + 1, name=f"f{i}", node_ids=np.arange(n), coords=pts,
                            edges=np.stack([np.arange(n - 1), np.arange(1, n)], axis=1)))  # fmt: skip
    return Skeleton(fibers=fibers, scale_um=(7.91, 7.91, 7.91), origin_zyx=(0, 0, 0))


def _scene(shift=(0, 0, 0)):
    """Two straight tubes in a 48^3 volume; the skeleton runs along their axes, displaced by `shift`."""
    shape = (48, 48, 48)
    prob = np.zeros(shape, dtype=np.float32)
    prob[10:38, 12:15, 20:23] = 0.9  # fiber along z
    prob[30:33, 6:40, 30:33] = 0.9  # fiber along y
    prob[20:23, 30:33, 5:15] = 0.3  # a faint fiber only a lower threshold sees
    lines = [
        [(10, 13, 21), (37, 13, 21)],
        [(31, 6, 31), (31, 39, 31)],
        [(21, 31, 5), (21, 31, 14)],
    ]
    lines = [[tuple(np.add(p, shift)) for p in ln] for ln in lines]
    return prob, _skeleton(lines)


@needs_scrollgt
def test_zero_shift_coverage_is_scrollgts(mod):
    from scrollgt.fibers.eval_trace import floor_connected_components, score_tracing

    prob, skel = _scene()
    mask = prob >= 0.5
    want = score_tracing(skel, floor_connected_components(mask), tolerance=2.0).coverage
    idx, dl = mod.samples(skel)
    s = mod.shift_search(mask, idx, dl, max_shift=2)
    assert s["zero"] == pytest.approx(want, abs=1e-12)
    assert mod.threshold_sweep(prob, idx, dl)["coverage"]["0.5"] == pytest.approx(
        want, abs=1e-12
    )
    assert (
        0.8 < want < 0.9
    )  # the faint fiber (9 of 69 voxels of length) is missed at 0.5


@needs_scrollgt
def test_partial_edge_coverage_matches_scrollgt_too(mod):
    """A skeleton that leaves the volume and grazes the mask edge: the in-bounds and tolerance logic must still agree."""
    from scrollgt.fibers.eval_trace import floor_connected_components, score_tracing

    prob, _ = _scene()
    skel = _skeleton(
        [[(-5, 16.4, 21.5), (30, 16.4, 21.5)], [(31, -3, 34.6), (31, 52, 34.6)]]
    )
    mask = prob >= 0.5
    want = score_tracing(skel, floor_connected_components(mask), tolerance=2.0).coverage
    idx, dl = mod.samples(skel)
    assert mod.shift_search(mask, idx, dl, max_shift=1)["zero"] == pytest.approx(
        want, abs=1e-12
    )
    assert mod.threshold_sweep(prob, idx, dl)["coverage"]["0.5"] == pytest.approx(
        want, abs=1e-12
    )


@needs_scrollgt
def test_threshold_sweep_sees_the_faint_fiber(mod):
    prob, skel = _scene()
    idx, dl = mod.samples(skel)
    w = mod.threshold_sweep(prob, idx, dl)
    assert w["coverage"]["0.3"] == pytest.approx(1.0)
    assert w["soft_miss_fraction"] == pytest.approx(1.0)
    hard = prob.copy()
    hard[hard == np.float32(0.3)] = 0.0
    assert mod.threshold_sweep(hard, idx, dl)["soft_miss_fraction"] == pytest.approx(
        0.0
    )


@needs_scrollgt
def test_shift_search_recovers_a_planted_offset(mod):
    prob, skel = _scene(shift=(0, 3, -4))
    mask = prob >= 0.5
    idx, dl = mod.samples(skel)
    s = mod.shift_search(mask, idx, dl, max_shift=4)
    assert s["gain"] > 0.3
    # Within the 2-voxel tolerance every shift near the planted one ties; ties go to the smallest shift, so the
    # search reports the near edge of the plateau. It must still point back toward the true frame on both axes.
    assert s["best_shift"][0] == 0 and s["best_shift"][1] < 0 and s["best_shift"][2] > 0
    prob0, skel0 = _scene()
    idx0, dl0 = mod.samples(skel0)
    assert mod.shift_search(prob0 >= 0.5, idx0, dl0, max_shift=4)["best_shift"] == [
        0,
        0,
        0,
    ]


def _row(split, gain=0.0, c01=None, soft=0.2, cov=0.6, g1=True):
    if c01 is None:
        c01 = cov + soft * (1 - cov)
    else:
        soft = (c01 - cov) / (1 - cov)
    return {"split": split, "g1_prob_threshold_equals_shipped_mask": g1, "published_cc_coverage": cov,
            "g2_zero_shift_coverage": cov, "g2_ballmax_coverage_at_0.5": cov,
            "shift": {"gain": gain, "best": cov + gain}, "sweep": {"coverage": {"0.1": c01}, "soft_miss_fraction": soft}}  # fmt: skip


def _full(mod, **new):
    res = {c: _row(mod.EXPECTED_SPLITS[c], soft=0.3) for c in mod.CUBES}
    res.update({c: _row("held_out", **new) for c in mod.NEW_S5})
    return res


def test_verdict_refuses_a_partial_sample(mod):
    res = _full(mod)
    del res[mod.NEW_S5[0]]
    with pytest.raises(ValueError, match="partial"):
        mod.verdict(res)


def test_a_failed_gate_emits_no_conclusion(mod):
    res = _full(mod)
    res[mod.IN_S5[0]] = _row("cross_scroll", g1=False)
    v = mod.verdict(res)
    assert v["status"] == "INSTRUMENT_FAILED" and "conclusion" not in v
    res = _full(mod)
    res[mod.IN_S5[1]]["g2_zero_shift_coverage"] += 0.001
    assert mod.verdict(res)["status"] == "INSTRUMENT_FAILED"
    res = _full(mod)
    res[mod.IN_S5[2]] = _row("cross_scroll", gain=0.06)
    v = mod.verdict(res)
    assert v["status"] == "CONTROL_FAILED" and "conclusion" not in v


@pytest.mark.parametrize(
    "new, conclusion",
    [
        ({"gain": 0.3, "cov": 0.6}, "FRAME_OFFSET_EXPLAINS"),
        ({"gain": 0.1, "cov": 0.6}, "FRAME_OFFSET_PARTIAL"),
        ({"c01": 0.85}, "THRESHOLD_RESCUES"),
        ({"soft": 0.5}, "SOFTER_BUT_NOT_RESCUED"),
        ({}, "HARD_MISS"),
    ],
)
def test_verdict_branches(mod, new, conclusion):
    assert mod.verdict(_full(mod, **new))["conclusion"] == conclusion
