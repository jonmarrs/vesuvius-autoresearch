"""Baseline lock: the tracer's current behaviour, so an improvement is provable.

These tests do not assert the tracer is good. They assert it behaves exactly as
it did when the published baseline was measured, so that a later change can be
attributed to the change rather than to drift.
"""

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.trace import TraceParams, trace_fibers

BASE = {
    "seed_threshold": 0.5,
    "continue_threshold": 0.25,
    "min_length": 3.0,
    "max_angle_deg": 25.0,
    "claim_radius": 2.5,
}


def _straight_tube(shape=(40, 40, 40), axis=0, centre=(20, 20), radius=2.0):
    """A single straight fiber along `axis`, with a clean orientation field.

    Returns (response, seed_response, dirs, valid). The two fields differ on
    purpose and the distinction is load-bearing: `response` is the flat
    continuation gate a semantic model produces, while `seed_response` is
    ridge-peaked like Hessian vesselness. Passing the flat field for seeding
    scatters seeds across the cross-section and yields several parallel
    instances per fiber -- `trace_fibers`' own docstring records measuring 15
    instances instead of 3 that way. `claim_radius` is 2.5 (> the tube radius)
    so one accepted seed claims the whole cross-section.
    """
    response = np.zeros(shape, dtype=float)
    seed = np.zeros(shape, dtype=float)
    dirs = np.zeros(shape + (3,), dtype=float)
    valid = np.zeros(shape, dtype=bool)
    coords = list(np.indices(shape))
    perp = [i for i in range(3) if i != axis]
    d2 = (coords[perp[0]] - centre[0]) ** 2.0 + (coords[perp[1]] - centre[1]) ** 2.0
    inside = d2 <= radius * radius
    response[inside] = 1.0
    seed[inside] = np.exp(-d2[inside] / (2.0 * (radius / 2.0) ** 2))
    dirs[inside, axis] = 1.0
    valid[inside] = True
    return response, seed, dirs, valid


def test_defaults_preserve_published_behaviour():
    """The new parameters must all default to a no-op."""
    p = TraceParams()
    assert p.tangent_window == 1, "default must reproduce the published baseline"
    assert p.max_skip_steps == 0, "default must reproduce the published baseline"
    assert p.seed_nms_radius == 0.0, "default must reproduce the published baseline"


def test_straight_fiber_traces_end_to_end():
    response, seed, dirs, valid = _straight_tube()
    res = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(**BASE),
    )
    assert len(res) == 1, f"expected one fiber, got {len(res)}: {res.stop_counts}"
    assert res.fibers[0].length > 25.0
    assert res.stop_counts.get("high_curvature", 0) == 0


def test_single_corrupted_voxel_splits_the_fiber_today():
    """The defect being fixed, pinned as current behaviour.

    One voxel with a wildly wrong orientation splits the fiber in two, because
    the walk terminates on the first curvature rejection.
    """
    response, seed, dirs, valid = _straight_tube()
    dirs[20, 20, 20] = np.array([0.0, 1.0, 0.0])  # perpendicular to the fiber

    res = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(**BASE),
    )
    assert res.stop_counts.get("high_curvature", 0) >= 1, (
        "the corrupted voxel should currently stop a walk; if it does not, this "
        "test no longer pins the defect and must be rewritten before proceeding"
    )
    assert len(res) == 2, f"expected the fiber to be split in two, got {len(res)}"


def test_coasting_survives_a_single_corrupted_voxel():
    """Fix A, mechanism 2: one bad voxel must no longer split the fiber.

    Smoothing alone cannot do this. At the corrupted voxel the incoming
    direction is perpendicular, so dot(d, ref) fails the threshold whether the
    reference is smoothed or not. The coast budget is what carries this case.
    """
    response, seed, dirs, valid = _straight_tube()
    dirs[20, 20, 20] = np.array([0.0, 1.0, 0.0])

    res = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(tangent_window=3, max_skip_steps=2, **BASE),
    )
    assert len(res) == 1, f"expected one unbroken fiber, got {len(res)}"
    assert res.fibers[0].length > 25.0
    assert res.stop_counts.get("high_curvature", 0) == 0


def test_smoothing_alone_does_not_rescue_an_outlier():
    """Pins the limit of mechanism 1, so the two are not confused later."""
    response, seed, dirs, valid = _straight_tube()
    dirs[20, 20, 20] = np.array([0.0, 1.0, 0.0])

    res = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(tangent_window=3, max_skip_steps=0, **BASE),
    )
    assert res.stop_counts.get("high_curvature", 0) >= 1, (
        "smoothing the reference cannot reject a bad sample; if this now passes, "
        "the coast budget is leaking into the smoothing-only path"
    )


def test_coasting_still_stops_at_a_genuine_bend():
    """Fix A must not silently disable the curvature test.

    A sustained 90-degree turn is a real direction change, not noise, and must
    still terminate the walk once the coast budget is exhausted.
    """
    shape = (40, 40, 40)
    response = np.zeros(shape, dtype=float)
    seed = np.zeros(shape, dtype=float)
    dirs = np.zeros(shape + (3,), dtype=float)
    valid = np.zeros(shape, dtype=bool)

    # an L: along z for the first half, along y for the second
    for z in range(5, 21):
        response[z, 19:22, 19:22] = 1.0
        seed[z, 20, 20] = 1.0
        dirs[z, 19:22, 19:22] = np.array([1.0, 0.0, 0.0])
        valid[z, 19:22, 19:22] = True
    for y in range(20, 36):
        response[19:22, y, 19:22] = 1.0
        dirs[19:22, y, 19:22] = np.array([0.0, 1.0, 0.0])
        valid[19:22, y, 19:22] = True

    res = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(tangent_window=3, max_skip_steps=2, **BASE),
    )
    # This assertion is valid for skip budgets up to about 4 at this geometry: at
    # max_skip_steps >= 5 the walk coasts far enough to reach the bend's far side
    # before the budget is exhausted, and the stop label flips to "low_response"
    # even though the walk still never actually turns the corner. Not budget-invariant.
    assert res.stop_counts.get("high_curvature", 0) >= 1, (
        "a sustained 90-degree bend must still stop a walk"
    )


def test_window_one_and_no_skip_is_exactly_the_old_behaviour():
    response, seed, dirs, valid = _straight_tube()
    dirs[20, 20, 20] = np.array([0.0, 1.0, 0.0])

    old = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(tangent_window=1, max_skip_steps=0, **BASE),
    )
    assert old.stop_counts.get("high_curvature", 0) >= 1
    assert len(old) == 2


def test_nms_keeps_one_seed_per_cross_section():
    """A single fat fiber must not yield several parallel instances.

    claim_radius is deliberately small here (0.5, well under the tube radius) so
    the existing claimed-territory check cannot mask the effect. Without
    suppression several offset seeds each walk the full length; with it, one.
    """
    response, seed, dirs, valid = _straight_tube(radius=3.0)
    p = {
        "seed_threshold": 0.5,
        "continue_threshold": 0.25,
        "min_length": 5.0,
        "max_angle_deg": 25.0,
        "seed_stride": 1,
        "claim_radius": 0.5,
    }

    without = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(seed_nms_radius=0.0, **p),
    )
    with_nms = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(seed_nms_radius=2.0, **p),
    )

    assert len(with_nms) == 1, f"expected one instance, got {len(with_nms)}"
    assert len(with_nms) < len(without), (
        f"NMS must reduce the instance count here; got {len(without)} -> "
        f"{len(with_nms)}. If they are equal, claimed-territory skipping is "
        f"already handling this case and the test proves nothing."
    )


def test_nms_does_not_merge_two_nearby_parallel_fibers():
    """Suppression must not swallow a genuinely separate neighbour."""
    shape = (40, 40, 40)
    response = np.zeros(shape, dtype=float)
    seed = np.zeros(shape, dtype=float)
    dirs = np.zeros(shape + (3,), dtype=float)
    valid = np.zeros(shape, dtype=bool)
    for cx in (17, 23):  # two fibers 6 voxels apart
        response[:, 20, cx] = 1.0
        seed[:, 20, cx] = 1.0
        dirs[:, 20, cx] = np.array([1.0, 0.0, 0.0])
        valid[:, 20, cx] = True

    res = trace_fibers(
        response=response,
        seed_response=seed,
        directions=dirs,
        valid=valid,
        params=TraceParams(
            seed_threshold=0.5,
            continue_threshold=0.25,
            min_length=5.0,
            max_angle_deg=25.0,
            seed_stride=1,
            claim_radius=0.5,
            seed_nms_radius=2.0,
        ),
    )
    assert len(res) == 2, f"expected two fibers, got {len(res)}"


def test_nms_suppresses_perpendicular_only():
    """A candidate far along the tangent must still be accepted.

    Suppressing along the tangent would stop a long fiber being re-seeded past
    a gap, costing coverage.
    """
    from vesuvius_autoresearch.fibers.trace import _suppress_perpendicular

    accepted = np.array([20.0, 20.0, 20.0])
    tangent = np.array([1.0, 0.0, 0.0])

    near_perp = np.array([20.0, 21.0, 20.0])  # 1 voxel perpendicular
    far_along = np.array([35.0, 20.0, 20.0])  # 15 voxels along the tangent

    assert _suppress_perpendicular(near_perp, accepted, tangent, 2.0) is True
    assert _suppress_perpendicular(far_along, accepted, tangent, 2.0) is False
