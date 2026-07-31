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
