"""Conservative fiber tracer.

The properties worth pinning are not "does it find fibers" but the ones the
🙋 ask actually cares about: it must not merge distinct fibers, it must stop
rather than guess, it must say why it stopped, and raising the abstention
threshold must trade coverage monotonically rather than behaving erratically.
"""

from __future__ import annotations

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.trace import (
    StopReason,
    TraceParams,
    TraceResult,
    trace_fibers,
)


def _tubes(n=64, centers=((20, 20), (20, 44), (44, 32)), radius=2.0):
    vol = np.zeros((n, n, n), dtype=float)
    zz, yy = np.mgrid[0:n, 0:n]
    for cz, cy in centers:
        vol[((zz - cz) ** 2 + (yy - cy) ** 2) <= radius**2, :] = 1.0
    return vol


def _params(**kw):
    base = {
        "seed_threshold": 0.5,
        "continue_threshold": 0.2,
        "min_length": 10,
        "seed_stride": 3,
    }
    base.update(kw)
    return TraceParams(**base)


def test_traces_one_instance_per_tube():
    """Three separated tubes must give exactly three fibers: no splits, no merges."""
    res = trace_fibers(_tubes(), params=_params())
    assert len(res) == 3, f"expected 3 fibers, got {len(res)}"
    for f in res.fibers:
        assert f.length > 50, f"tube traced only {f.length:.1f} of ~63 voxels"


def test_tangent_follows_the_tube_axis():
    res = trace_fibers(_tubes(), params=_params())
    for f in res.fibers:
        d = f.points[-1] - f.points[0]
        d = d / np.linalg.norm(d)
        assert abs(d[2]) > 0.95, f"walk not along x: {d}"


def test_claiming_suppresses_redundant_seeds():
    """A traced fiber claims its neighbourhood, so we try few seeds, not thousands."""
    res = trace_fibers(_tubes(), params=_params())
    assert res.n_seeds_tried <= 10, (
        f"claiming failed: {res.n_seeds_tried} seeds tried for 3 fibers"
    )


def test_every_fiber_reports_a_stop_reason():
    res = trace_fibers(_tubes(), params=_params())
    assert res.stop_counts, "stop reasons must be reported"
    assert sum(res.stop_counts.values()) == 2 * len(res)
    for f in res.fibers:
        assert isinstance(f.stop_start, StopReason)
        assert isinstance(f.stop_end, StopReason)
    # Tubes span the whole cube, so both ends should run off the edge.
    assert res.stop_counts.get(StopReason.OUT_OF_BOUNDS.value, 0) == 2 * len(res)


def test_does_not_merge_two_nearly_touching_tubes():
    """The failure mode that matters. A merge corrupts the U/V axes downstream."""
    n = 64
    vol = np.zeros((n, n, n), dtype=float)
    zz, yy = np.mgrid[0:n, 0:n]
    # Two parallel tubes 4 voxels apart, closer than a naive tracer tolerates.
    for cy in (30, 34):
        vol[((zz - 32) ** 2 + (yy - cy) ** 2) <= 1.0**2, :] = 1.0
    res = trace_fibers(vol, params=_params(min_length=20))
    # Either it separates them, or it conservatively traces one and stops; what
    # it must not do is produce a single instance spanning both centre lines.
    for f in res.fibers:
        spread = f.points[:, 1].max() - f.points[:, 1].min()
        assert spread < 3.5, f"instance spans both tubes (y spread {spread:.1f})"


def test_empty_volume_returns_nothing_not_an_error():
    res = trace_fibers(np.zeros((32, 32, 32)), params=_params())
    assert len(res) == 0
    assert res.total_length == 0.0
    assert res.to_instances().sum() == 0


def test_constant_volume_does_not_hallucinate_fibers():
    """A featureless volume has no fibers; a tracer that invents them is useless."""
    res = trace_fibers(np.ones((32, 32, 32)), params=_params())
    assert len(res) == 0, f"hallucinated {len(res)} fibers in a constant volume"


def test_pure_noise_yields_far_less_than_structured_signal():
    rng = np.random.default_rng(0)
    noise = rng.random((64, 64, 64))
    res_noise = trace_fibers(noise, params=_params())
    res_tubes = trace_fibers(_tubes(), params=_params())
    assert res_noise.total_length < 0.5 * res_tubes.total_length, (
        f"noise traced {res_noise.total_length:.0f} vs tubes "
        f"{res_tubes.total_length:.0f}: tracer is not discriminating"
    )


def test_determinism():
    a = trace_fibers(_tubes(), params=_params())
    b = trace_fibers(_tubes(), params=_params())
    assert len(a) == len(b)
    for fa, fb in zip(a.fibers, b.fibers, strict=False):
        np.testing.assert_allclose(fa.points, fb.points)
        assert fa.confidence == fb.confidence


def test_confidence_filter_is_monotonic_and_non_mutating():
    """The abstention sweep underpins the coverage/correctness curve."""
    res = trace_fibers(_tubes(), params=_params())
    n0 = len(res)
    prev = n0
    for t in [0.0, 0.25, 0.5, 0.75, 1.01]:
        sub = res.filter_confidence(t)
        assert len(sub) <= prev, "filter is not monotonic in threshold"
        prev = len(sub)
        assert len(res) == n0, "filter_confidence mutated the original result"
    assert len(res.filter_confidence(1.01)) == 0


def test_smooth_bend_is_followed_but_a_gap_is_not_bridged():
    """`max_angle_deg` is a PER-STEP limit, so smooth curves are followed by
    design -- real papyrus fibers curve, and refusing to follow them would be
    the wrong behaviour. The property that matters is not bridging across a gap
    into a different structure.
    """
    n = 48
    # Two perpendicular segments that never touch: 6 voxels of background between.
    vol = np.zeros((n, n, n), dtype=float)
    vol[24, 24, 4:20] = 1.0  # along x
    vol[24, 26:42, 26] = 1.0  # along y, offset and disjoint
    res = trace_fibers(
        vol, params=_params(min_length=5, max_angle_deg=20.0, seed_stride=1)
    )
    for f in res.fibers:
        yspread = np.ptp(f.points[:, 1])
        xspread = np.ptp(f.points[:, 2])
        assert not (xspread > 8 and yspread > 8), (
            f"bridged the gap between two structures (x {xspread:.1f}, y {yspread:.1f})"
        )


def test_step_angle_limit_is_enforced():
    """No single step may exceed max_angle_deg, whatever the geometry."""
    res = trace_fibers(_tubes(), params=_params(max_angle_deg=30.0))
    for f in res.fibers:
        if len(f.points) < 3:
            continue
        d = np.diff(f.points, axis=0)
        nrm = np.linalg.norm(d, axis=1, keepdims=True)
        d = d / np.maximum(nrm, 1e-12)
        cos = np.sum(d[:-1] * d[1:], axis=1)
        worst = np.degrees(np.arccos(np.clip(cos.min(), -1, 1)))
        assert worst <= 30.0 + 1e-6, f"step turned {worst:.2f} deg, limit 30"


def test_to_instances_labels_are_distinct_per_fiber():
    res = trace_fibers(_tubes(), params=_params())
    inst = res.to_instances(radius=1.0)
    labels = set(np.unique(inst)) - {0}
    assert len(labels) == len(res)
    assert labels == set(range(1, len(res) + 1))


def test_semantic_mask_needs_a_centreline_field_for_seeding():
    """A flat mask carries no centre-line information; seeding on it over-splits.

    Documented behaviour, not a wart: a saturated semantic mask is uniform inside
    a fiber, so seeds scatter across the cross-section and each spawns its own
    walk. Centre-line geometry must come from the Hessian. Passing `volume` makes
    the tracer build a vesselness seed field automatically.
    """
    from vesuvius_autoresearch.fibers.detection import fiber_direction, hessian

    vol = _tubes()
    J, _ = hessian(vol.copy(), gauss_sigma=1, sigma=2)
    dirs, valid = fiber_direction(J)
    mask = (vol > 0.5).astype(float)  # a perfect but FLAT "semantic segmentation"

    flat = trace_fibers(
        response=mask,
        directions=np.asarray(dirs),
        valid=np.asarray(valid),
        params=_params(),
    )
    assert len(flat) > 3, (
        "expected over-splitting when seeding on a flat mask; if this now "
        "returns 3, the seeding strategy changed and the docs need updating"
    )

    # The intended composition: mask gates continuation, volume supplies geometry.
    composed = trace_fibers(
        vol,
        response=mask,
        directions=np.asarray(dirs),
        valid=np.asarray(valid),
        params=_params(),
    )
    assert len(composed) == 3, f"composed path gave {len(composed)} fibers, want 3"


def test_accepts_precomputed_response_and_directions():
    """All-precomputed path must run without a volume."""
    from vesuvius_autoresearch.fibers.detection import (
        detect_vesselness,
        fiber_direction,
        hessian,
    )

    vol = _tubes()
    J, _ = hessian(vol.copy(), gauss_sigma=1, sigma=2)
    dirs, valid = fiber_direction(J)
    ves = np.asarray(detect_vesselness(vol.copy(), gauss_sigma=1, sigma=2), dtype=float)
    ves = ves / ves.max()
    res = trace_fibers(
        response=ves,
        seed_response=ves,
        directions=np.asarray(dirs),
        valid=np.asarray(valid),
        params=_params(),
    )
    assert len(res) == 3


def test_missing_inputs_raise():
    with pytest.raises(ValueError):
        trace_fibers()


def test_traceresult_shape_matches_input():
    res = trace_fibers(_tubes(n=48), params=_params())
    assert res.shape == (48, 48, 48)
    assert res.to_instances().shape == (48, 48, 48)
