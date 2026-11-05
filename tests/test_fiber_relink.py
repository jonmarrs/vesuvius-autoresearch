"""Fragment re-linking.

Fragmentation, not detection, is what limits this tracer: coverage reached
0.69-0.88 of ground-truth length but each fiber came back as 10-26 instances.
Re-linking joins collinear fragments.

The governing asymmetry: a wrong link is a MERGE and corrupts the parameterization
fibers are wanted for, while the split it would fix merely fails to help. So the
tests that matter most are the ones asserting it *refuses* to link.
"""

from __future__ import annotations

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.trace import (
    RelinkParams,
    StopReason,
    TracedFiber,
    TraceResult,
    relink_fragments,
)


def _frag(pts, mean=0.9, mn=0.8):
    return TracedFiber(
        points=np.asarray(pts, dtype=float),
        mean_response=mean,
        min_response=mn,
        stop_start=StopReason.LOW_RESPONSE,
        stop_end=StopReason.LOW_RESPONSE,
    )


def _line(z, y, x0, x1, step=1.0):
    xs = np.arange(x0, x1 + 1e-9, step)
    return np.stack([np.full(len(xs), z), np.full(len(xs), y), xs], axis=1)


def _result(frags, shape=(32, 32, 64)):
    return TraceResult(fibers=list(frags), shape=shape)


def test_joins_two_collinear_fragments_across_a_gap():
    r = _result([_frag(_line(16, 16, 0, 20)), _frag(_line(16, 16, 25, 45))])
    out = relink_fragments(r, RelinkParams(max_gap=6.0))
    assert len(out) == 1, f"expected one joined fiber, got {len(out)}"
    assert out.fibers[0].length > 40


def test_preserves_point_order_along_the_joined_fiber():
    r = _result([_frag(_line(16, 16, 0, 20)), _frag(_line(16, 16, 25, 45))])
    out = relink_fragments(r, RelinkParams(max_gap=6.0))
    xs = out.fibers[0].points[:, 2]
    assert np.all(np.diff(xs) > 0) or np.all(np.diff(xs) < 0), (
        f"points not monotone along the fiber: {xs[:8]} ... {xs[-8:]}"
    )


def test_refuses_a_gap_that_is_too_long():
    r = _result([_frag(_line(16, 16, 0, 20)), _frag(_line(16, 16, 40, 60))])
    out = relink_fragments(r, RelinkParams(max_gap=6.0))
    assert len(out) == 2, "bridged a gap it should have refused"


def test_refuses_perpendicular_fragments():
    """A T-junction must not be linked: that is the classic false merge."""
    horiz = _line(16, 16, 0, 20)
    vert = np.stack(
        [np.full(21, 16.0), np.arange(24.0, 45.0), np.full(21, 22.0)], axis=1
    )
    out = relink_fragments(
        _result([_frag(horiz), _frag(vert)]), RelinkParams(max_gap=8.0)
    )
    assert len(out) == 2, "linked two perpendicular fragments"


def test_refuses_parallel_side_by_side_fragments():
    """Two fibers running alongside each other must stay separate."""
    r = _result([_frag(_line(16, 14, 0, 20)), _frag(_line(16, 18, 22, 42))])
    out = relink_fragments(r, RelinkParams(max_gap=6.0, max_link_angle_deg=20.0))
    assert len(out) == 2, "joined two parallel neighbours"


def test_refuses_antiparallel_overlap():
    """Fragments whose tangents point the same way are not end-to-end."""
    a = _line(16, 16, 0, 20)
    b = _line(16, 16, 22, 42)[::-1]  # same geometry, reversed traversal
    out = relink_fragments(_result([_frag(a), _frag(b)]), RelinkParams(max_gap=6.0))
    # Reversal is legitimate (direction is arbitrary), so this SHOULD link.
    assert len(out) == 1


def test_chains_three_fragments():
    r = _result(
        [
            _frag(_line(16, 16, 0, 12)),
            _frag(_line(16, 16, 16, 28)),
            _frag(_line(16, 16, 32, 44)),
        ]
    )
    out = relink_fragments(r, RelinkParams(max_gap=6.0))
    assert len(out) == 1, f"expected a single chain, got {len(out)}"
    assert out.fibers[0].length > 38


def test_each_endpoint_used_at_most_once():
    """Three fragments meeting at one point must not all fuse through it."""
    centre = np.array([16.0, 16.0, 20.0])
    arms = []
    for d in [(0, 0, -1), (0, -1, 0), (0, 1, 0)]:
        d = np.array(d, dtype=float)
        arms.append(_frag(centre + d * np.arange(3, 18)[:, None]))
    out = relink_fragments(_result(arms), RelinkParams(max_gap=8.0))
    # At most one pair may join; a three-way fusion is a merge.
    assert len(out) >= 2, f"three-way fusion at a junction: {len(out)}"


def test_no_cycles():
    """A closed loop of fragments must not be linked into a cycle."""
    pts = []
    for k in range(4):
        ang = np.linspace(k * np.pi / 2, (k + 1) * np.pi / 2, 12)[:-1]
        pts.append(
            np.stack(
                [np.full(len(ang), 16.0), 16 + 10 * np.sin(ang), 20 + 10 * np.cos(ang)],
                axis=1,
            )
        )
    out = relink_fragments(_result([_frag(p) for p in pts]), RelinkParams(max_gap=6.0))
    total_pts = sum(len(f.points) for f in out.fibers)
    assert total_pts == sum(len(p) for p in pts), "points lost or duplicated"
    assert len(out) >= 1


def test_is_non_mutating():
    frags = [_frag(_line(16, 16, 0, 20)), _frag(_line(16, 16, 25, 45))]
    r = _result(frags)
    before = len(r.fibers)
    out = relink_fragments(r, RelinkParams(max_gap=6.0))
    assert len(r.fibers) == before, "input result was mutated"
    assert sum(len(f.points) for f in out.fibers) >= sum(len(f.points) for f in frags)


def test_bridged_gap_is_filled_with_geometry():
    """A link must make the instance continuous, not just share an id.

    Regression test for a measured no-op: without gap filling, re-linking cut the
    instance count 200 -> 167 while ERL moved 23.14 -> 23.17, because the gap
    stayed background in the rasterization and the ground-truth run was still
    broken.
    """
    r = _result([_frag(_line(16, 16, 0, 20)), _frag(_line(16, 16, 26, 46))])
    out = relink_fragments(r, RelinkParams(max_gap=8.0, gap_fill_step=0.7))
    assert len(out) == 1
    xs = np.sort(out.fibers[0].points[:, 2])
    biggest_gap = float(np.max(np.diff(xs)))
    assert biggest_gap <= 1.0, f"gap left unfilled, largest step {biggest_gap:.2f}"

    inst = out.to_instances(radius=1.0)
    lane = inst[16, 16, :]
    covered = np.flatnonzero(lane > 0)
    assert covered.size > 0
    assert int(np.max(np.diff(covered))) == 1, "rasterized instance is discontinuous"


def test_single_and_empty_inputs():
    assert len(relink_fragments(_result([]))) == 0
    one = _result([_frag(_line(16, 16, 0, 20))])
    assert len(relink_fragments(one)) == 1


def test_confidence_uses_worst_fragment():
    """A chain is only as trustworthy as its weakest link."""
    r = _result(
        [
            _frag(_line(16, 16, 0, 20), mean=0.9, mn=0.9),
            _frag(_line(16, 16, 25, 45), mean=0.5, mn=0.2),
        ]
    )
    out = relink_fragments(r, RelinkParams(max_gap=6.0))
    assert len(out) == 1
    assert out.fibers[0].min_response == 0.2


@pytest.mark.parametrize("reverse_first", [False, True])
@pytest.mark.parametrize("reverse_last", [False, True])
def test_stop_reasons_follow_the_output_endpoints(reverse_first, reverse_last):
    first = _frag(_line(16, 16, 0, 20))
    last = _frag(_line(16, 16, 25, 45))
    first.stop_start, first.stop_end = (
        StopReason.OUT_OF_BOUNDS,
        StopReason.HIGH_CURVATURE,
    )
    last.stop_start, last.stop_end = StopReason.LOW_RESPONSE, StopReason.MAX_LENGTH
    for fragment, reverse in [(first, reverse_first), (last, reverse_last)]:
        if reverse:
            fragment.points = fragment.points[::-1].copy()
            fragment.stop_start, fragment.stop_end = (
                fragment.stop_end,
                fragment.stop_start,
            )
    original = _result([first, last])
    original.stop_counts = {
        "out_of_bounds": 1,
        "high_curvature": 1,
        "low_response": 1,
        "max_length": 1,
    }
    out = relink_fragments(original)
    assert len(out) == 1
    fiber = out.fibers[0]
    reasons = {0.0: StopReason.OUT_OF_BOUNDS, 45.0: StopReason.MAX_LENGTH}
    assert fiber.stop_start == reasons[fiber.points[0, 2]]
    assert fiber.stop_end == reasons[fiber.points[-1, 2]]
    assert out.stop_counts == original.stop_counts
    assert out.stop_counts is not original.stop_counts


@pytest.mark.parametrize("seed", range(5))
def test_spatial_search_matches_exhaustive_pairs(monkeypatch, seed):
    from scipy import spatial

    rng = np.random.default_rng(seed)
    fragments = []
    for _ in range(40):
        start = rng.uniform(0, 30, 3)
        direction = rng.normal(size=3)
        direction /= np.linalg.norm(direction)
        points = start + np.arange(8)[:, None] * direction
        fragments.append(_frag(points))
    # Include equal-cost alternatives, exact-gap boundary, and a reversed chain.
    fragments.extend(
        [
            _frag(_line(16, 16, 0, 10)),
            _frag(_line(16, 16, 16, 26)),
            _frag(_line(16, 16, 16, 26)),
            _frag(_line(16, 16, 32, 42)[::-1]),
        ]
    )
    result = _result(fragments)
    params = RelinkParams(max_gap=6, max_link_angle_deg=45, max_tangent_angle_deg=60)
    indexed = relink_fragments(result, params)

    class ExhaustivePairs:
        def __init__(self, points):
            self.count = len(points)

        def query_ball_point(self, *args, **kwargs):
            # Disable only the broad phase: every original endpoint pair is tested.
            return range(self.count)

    monkeypatch.setattr(spatial, "cKDTree", ExhaustivePairs)
    exhaustive = relink_fragments(result, params)
    assert len(indexed) == len(exhaustive)
    for actual, expected in zip(indexed.fibers, exhaustive.fibers, strict=True):
        np.testing.assert_array_equal(actual.points, expected.points)
        assert actual.mean_response == expected.mean_response
        assert actual.min_response == expected.min_response
        assert actual.stop_start == expected.stop_start
        assert actual.stop_end == expected.stop_end
    np.testing.assert_array_equal(indexed.to_instances(), exhaustive.to_instances())


@pytest.mark.parametrize(
    "name,value",
    [
        ("max_gap", np.nan),
        ("max_gap", np.inf),
        ("max_gap", -1),
        ("max_link_angle_deg", np.nan),
        ("max_link_angle_deg", 181),
        ("max_tangent_angle_deg", -1),
        ("angle_weight", np.inf),
        ("gap_weight", -1),
        ("gap_fill_step", 0),
        ("gap_fill_step", np.nan),
        ("endpoint_window", 0),
        ("endpoint_window", 1.5),
        ("endpoint_window", True),
    ],
)
def test_invalid_relink_parameters_fail_even_on_empty_inputs(name, value):
    params = RelinkParams(**{name: value})
    with pytest.raises(ValueError, match=name):
        relink_fragments(_result([]), params)


@pytest.mark.parametrize(
    "points",
    [
        np.empty((0, 3)),
        np.ones((1, 3)),
        np.ones((2, 2)),
        np.ones(3),
        np.array([[0, 0, np.nan]]),
        np.array([[0, 0, np.inf]]),
    ],
)
def test_invalid_fragment_geometry_is_rejected(points):
    with pytest.raises(ValueError, match="fragment points"):
        relink_fragments(_result([_frag(points)]))
