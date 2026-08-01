"""Ground-truth tangent extraction and sign-ambiguous angular error."""

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.field_quality import (
    NodeKind,
    count_node_kinds,
    gt_tangents,
    gt_tangents_bisector,
    tangent_estimator_disagreement,
)
from vesuvius_autoresearch.fibers.skeleton_io import Fiber


def _line_fiber(n=6, axis=0, spacing=2.0):
    """A straight chain of n nodes along `axis`, spaced `spacing` voxels apart."""
    coords = np.zeros((n, 3), dtype=float)
    coords[:, axis] = np.arange(n) * spacing
    edges = np.array([[i, i + 1] for i in range(n - 1)], dtype=int)
    return Fiber(id=1, name="line", node_ids=np.arange(n), coords=coords, edges=edges)


def test_straight_line_tangents_all_point_along_the_axis():
    coords, tangents, kinds = gt_tangents(_line_fiber(axis=0))
    assert len(coords) == 6
    assert all(k in (NodeKind.INTERIOR, NodeKind.ENDPOINT) for k in kinds)
    for t in tangents:
        assert abs(abs(float(t[0])) - 1.0) < 1e-9, t
        assert abs(float(t[1])) < 1e-9 and abs(float(t[2])) < 1e-9


def test_tangents_are_unit_length():
    _, tangents, _ = gt_tangents(_line_fiber())
    np.testing.assert_allclose(np.linalg.norm(tangents, axis=1), 1.0, atol=1e-9)


def test_endpoints_and_interiors_are_labelled():
    _, _, kinds = gt_tangents(_line_fiber(n=5))
    assert kinds[0] == NodeKind.ENDPOINT
    assert kinds[-1] == NodeKind.ENDPOINT
    assert kinds[1:-1] == [NodeKind.INTERIOR] * 3


def test_branch_node_is_excluded_and_counted():
    """A Y-junction node has no single tangent; including one would fake error."""
    coords = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],  # stem
            [3.0, 1.0, 0.0],
            [3.0, -1.0, 0.0],  # two arms off node 2
        ]
    )
    edges = np.array([[0, 1], [1, 2], [2, 3], [2, 4]], dtype=int)
    fib = Fiber(id=1, name="y", node_ids=np.arange(5), coords=coords, edges=edges)

    out_coords, _, kinds = gt_tangents(fib)
    assert len(out_coords) == 4, "the degree-3 node must be dropped"
    assert NodeKind.BRANCH not in kinds

    counts = count_node_kinds(fib)
    assert counts[NodeKind.BRANCH] == 1
    assert counts[NodeKind.ENDPOINT] == 3
    assert counts[NodeKind.INTERIOR] == 1


def test_isolated_node_is_excluded_and_counted():
    fib = Fiber(
        id=1,
        name="dot",
        node_ids=np.arange(1),
        coords=np.zeros((1, 3)),
        edges=np.zeros((0, 2), dtype=int),
    )
    out_coords, _, _ = gt_tangents(fib)
    assert len(out_coords) == 0
    assert count_node_kinds(fib)[NodeKind.ISOLATED] == 1


def test_duplicate_coordinates_are_excluded_as_degenerate():
    """Two nodes at the same position give a zero-length tangent."""
    coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    edges = np.array([[0, 1], [1, 2]], dtype=int)
    fib = Fiber(id=1, name="dup", node_ids=np.arange(3), coords=coords, edges=edges)

    _, tangents, _ = gt_tangents(fib)
    assert np.all(np.isfinite(tangents))
    assert count_node_kinds(fib)[NodeKind.DEGENERATE] >= 1


def test_interior_tangent_uses_a_central_difference():
    """A corner node's tangent must bisect its two edges, not follow one of them."""
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]])
    edges = np.array([[0, 1], [1, 2]], dtype=int)
    fib = Fiber(id=1, name="corner", node_ids=np.arange(3), coords=coords, edges=edges)

    _, tangents, kinds = gt_tangents(fib)
    mid = tangents[list(kinds).index(NodeKind.INTERIOR)]
    expected = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    assert abs(abs(float(np.dot(mid, expected))) - 1.0) < 1e-9


# --- chord vs. bisector estimator disagreement --------------------------------
#
# `gt_tangents` uses a length-weighted chord between a node's two neighbours;
# it only equals the true angle bisector when both edges are the same length.
# `gt_tangents_bisector` averages the two *unit* edge directions instead, so it
# is unaffected by unequal edge lengths. `tangent_estimator_disagreement`
# measures the gap between them, which is otherwise silently absorbed into
# whatever angular error we report against the model's orientation field.


def test_estimators_agree_exactly_on_an_equal_spacing_straight_line():
    fib = _line_fiber(n=6, axis=1, spacing=3.0)
    disagreement = tangent_estimator_disagreement(fib)
    assert len(disagreement) == 6
    np.testing.assert_allclose(disagreement, 0.0, atol=1e-9)


def test_estimators_agree_exactly_on_an_equal_spacing_corner():
    """Equal-length edges: the chord and the bisector coincide by construction."""
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]])
    edges = np.array([[0, 1], [1, 2]], dtype=int)
    fib = Fiber(id=1, name="corner", node_ids=np.arange(3), coords=coords, edges=edges)

    _, _, kinds = gt_tangents(fib)
    # gt_tangents and gt_tangents_bisector share ordering/exclusion, so the
    # disagreement array lines up with gt_tangents' kinds directly.
    interior_idx = kinds.index(NodeKind.INTERIOR)
    disagreement = tangent_estimator_disagreement(fib)
    # `arccos` is ill-conditioned near a dot product of 1.0: even when the two
    # unit vectors are bit-identical, self-dot rounds to slightly under 1.0
    # (squaring 1/sqrt(2) does not perfectly invert), so arccos returns
    # ~sqrt(2*eps) radians instead of exactly 0. That floor is ~1.2e-6 degrees
    # for float64, so 1e-4 is a tolerance far above the floating-point noise
    # floor and far below any real disagreement this function is meant to
    # detect on real data.
    assert abs(disagreement[interior_idx]) < 1e-4


def test_estimators_disagree_by_a_known_amount_on_an_asymmetric_corner():
    """A right angle with a 0.01-length edge and a 100-length edge.

    The chord leans almost entirely onto the long edge; the bisector still
    splits the angle in half. The expected disagreement is derived directly
    from the corner's geometry (not by calling either estimator), so this
    pins down a specific number rather than merely asserting "disagreement
    exists".
    """
    a = 0.01
    b = 100.0
    coords = np.array([[-a, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, b, 0.0]])
    edges = np.array([[0, 1], [1, 2]], dtype=int)
    fib = Fiber(
        id=1,
        name="asymmetric-corner",
        node_ids=np.arange(3),
        coords=coords,
        edges=edges,
    )

    chord = np.array([a, b, 0.0])
    chord = chord / np.linalg.norm(chord)
    bisector = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    expected_deg = float(
        np.degrees(np.arccos(np.clip(np.dot(chord, bisector), -1.0, 1.0)))
    )
    assert abs(expected_deg - 44.994) < 1e-2  # sanity check on the hand geometry

    _, _, kinds = gt_tangents(fib)
    interior_idx = kinds.index(NodeKind.INTERIOR)
    disagreement = tangent_estimator_disagreement(fib)
    assert abs(float(disagreement[interior_idx]) - expected_deg) < 1e-6


def test_bisector_falls_back_to_the_chord_when_a_node_doubles_back_on_itself():
    """Incoming and outgoing unit directions exactly cancel -- no bisector exists."""
    coords = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    edges = np.array([[0, 1], [1, 2]], dtype=int)
    fib = Fiber(
        id=1, name="doubles-back", node_ids=np.arange(3), coords=coords, edges=edges
    )

    chord_c, chord_t, chord_kinds = gt_tangents(fib)
    bisector_c, bisector_t, bisector_kinds = gt_tangents_bisector(fib)

    assert chord_kinds == bisector_kinds
    np.testing.assert_allclose(chord_c, bisector_c)

    interior_idx = chord_kinds.index(NodeKind.INTERIOR)
    # The bisector sum is exactly zero here, so it must fall back to the chord.
    np.testing.assert_allclose(
        bisector_t[interior_idx], chord_t[interior_idx], atol=1e-12
    )
    np.testing.assert_allclose(bisector_t[interior_idx], np.array([1.0, 0.0, 0.0]))

    disagreement = tangent_estimator_disagreement(fib)
    assert abs(float(disagreement[interior_idx])) < 1e-9


def test_gt_tangents_bisector_excludes_and_counts_the_same_nodes_as_gt_tangents():
    coords = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],  # stem
            [3.0, 1.0, 0.0],
            [3.0, -1.0, 0.0],  # two arms off node 2 (branch)
        ]
    )
    edges = np.array([[0, 1], [1, 2], [2, 3], [2, 4]], dtype=int)
    fib = Fiber(id=1, name="y", node_ids=np.arange(5), coords=coords, edges=edges)

    chord_c, _, chord_kinds = gt_tangents(fib)
    bisector_c, _, bisector_kinds = gt_tangents_bisector(fib)

    assert len(bisector_c) == len(chord_c) == 4
    np.testing.assert_allclose(bisector_c, chord_c)
    assert bisector_kinds == chord_kinds

    # Isolated node: excluded and counted the same way by both.
    dot = Fiber(
        id=1,
        name="dot",
        node_ids=np.arange(1),
        coords=np.zeros((1, 3)),
        edges=np.zeros((0, 2), dtype=int),
    )
    assert len(gt_tangents_bisector(dot)[0]) == len(gt_tangents(dot)[0]) == 0
    assert count_node_kinds(dot)[NodeKind.ISOLATED] == 1

    # Degenerate (duplicate coordinates): excluded and counted the same way.
    dup_coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    dup = Fiber(
        id=1,
        name="dup",
        node_ids=np.arange(3),
        coords=dup_coords,
        edges=np.array([[0, 1], [1, 2]], dtype=int),
    )
    assert len(gt_tangents_bisector(dup)[0]) == len(gt_tangents(dup)[0])
    assert count_node_kinds(dup)[NodeKind.DEGENERATE] >= 1


from vesuvius_autoresearch.fibers.field_quality import angular_error_deg


def test_identical_directions_have_zero_error():
    a = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, a), 0.0, atol=1e-9)


def test_opposite_directions_have_zero_error():
    """The load-bearing property: orientation is defined only up to sign.

    A field that returns -t where the truth is +t is perfectly correct. Scoring
    that as 180 degrees would make a good field look catastrophic.
    """
    a = np.array([[1.0, 0.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, -a), 0.0, atol=1e-9)


def test_perpendicular_directions_give_ninety_degrees():
    a = np.array([[1.0, 0.0, 0.0]])
    b = np.array([[0.0, 1.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, b), 90.0, atol=1e-9)


def test_known_angle_is_recovered_and_never_exceeds_ninety():
    for deg in (10.0, 25.0, 44.0, 89.0, 91.0, 170.0):
        r = np.deg2rad(deg)
        a = np.array([[1.0, 0.0, 0.0]])
        b = np.array([[np.cos(r), np.sin(r), 0.0]])
        got = float(angular_error_deg(a, b)[0])
        expected = min(deg, 180.0 - deg)
        assert abs(got - expected) < 1e-6, (deg, got, expected)
        assert 0.0 <= got <= 90.0


def test_unnormalised_inputs_are_handled():
    a = np.array([[3.0, 0.0, 0.0]])
    b = np.array([[0.0, 7.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, b), 90.0, atol=1e-9)


from vesuvius_autoresearch.fibers.field_quality import (  # noqa: E402
    analyse_cube,
    local_curvature_deg,
    perpendicular_offsets,
    sample_field,
)
from vesuvius_autoresearch.fibers.skeleton_io import Skeleton  # noqa: E402


def _tube_field(shape=(32, 32, 32), axis=0, angle_deg=0.0):
    """A constant orientation field rotated `angle_deg` away from `axis`."""
    r = np.deg2rad(angle_deg)
    d = np.zeros(3)
    d[axis] = np.cos(r)
    d[(axis + 1) % 3] = np.sin(r)
    dirs = np.broadcast_to(d, shape + (3,)).copy()
    valid = np.ones(shape, dtype=bool)
    return dirs, valid


def _centred_line(n=10, axis=0, spacing=2.0):
    fib = _line_fiber(n=n, axis=axis, spacing=spacing)
    fib.coords[:, 1] += 10.0
    fib.coords[:, 2] += 10.0
    return fib


def test_perfect_field_scores_near_zero():
    """The sanity check that catches an axis-convention error.

    A wrong convention would produce large, plausible-looking errors and read as
    a real finding about villa's released model. This makes that impossible to
    miss: a field that is exactly right must score exactly zero.
    """
    dirs, valid = _tube_field(axis=0, angle_deg=0.0)
    res = analyse_cube(Skeleton(fibers=[_centred_line()]), dirs, valid, (32, 32, 32))
    assert res["n_scored"] == 10
    assert float(np.median(res["error_deg"])) < 1e-4
    assert res["field_undefined_frac"] == 0.0


def test_known_rotation_is_recovered():
    dirs, valid = _tube_field(axis=0, angle_deg=17.0)
    res = analyse_cube(Skeleton(fibers=[_centred_line()]), dirs, valid, (32, 32, 32))
    assert abs(float(np.median(res["error_deg"])) - 17.0) < 1e-4


def test_negating_the_field_changes_nothing():
    dirs, valid = _tube_field(axis=0, angle_deg=17.0)
    skel = Skeleton(fibers=[_centred_line()])
    a = analyse_cube(skel, dirs, valid, (32, 32, 32))
    b = analyse_cube(skel, -dirs, valid, (32, 32, 32))
    np.testing.assert_allclose(a["error_deg"], b["error_deg"], atol=1e-12)


def test_undefined_field_is_reported_not_scored():
    dirs, valid = _tube_field(axis=0)
    valid[:5] = False
    res = analyse_cube(Skeleton(fibers=[_centred_line()]), dirs, valid, (32, 32, 32))
    assert 0.0 < res["field_undefined_frac"] < 1.0
    assert res["n_scored"] < 10


def test_out_of_bounds_nodes_count_as_undefined():
    fib = _centred_line(n=4)
    fib.coords[:, 0] += 100.0
    dirs, valid = _tube_field()
    res = analyse_cube(Skeleton(fibers=[fib]), dirs, valid, (32, 32, 32))
    assert res["field_undefined_frac"] == 1.0
    assert res["n_scored"] == 0


def test_perpendicular_offsets_are_perpendicular():
    t = np.array([1.0, 2.0, 3.0])
    t = t / np.linalg.norm(t)
    offs = perpendicular_offsets(t, radius=2.0, n=6)
    assert offs.shape == (6, 3)
    np.testing.assert_allclose(offs @ t, 0.0, atol=1e-9)
    np.testing.assert_allclose(np.linalg.norm(offs, axis=1), 2.0, atol=1e-9)


def test_local_curvature_is_zero_on_a_straight_line():
    curv = local_curvature_deg(_line_fiber(n=6))
    assert len(curv) == 6
    interior = ~np.isnan(curv)
    assert interior.sum() == 4
    np.testing.assert_allclose(curv[interior], 0.0, atol=1e-4)


def test_local_curvature_uses_the_edge_graph_not_array_order():
    """NML node order is arbitrary; array-order curvature is meaningless.

    Same geometry, shuffled node order and remapped edges: curvature must be
    identical. Comparing tangents at adjacent array positions would not be.
    """
    straight = _line_fiber(n=6)
    perm = np.array([3, 0, 5, 1, 4, 2])
    inv = np.argsort(perm)
    shuffled = Fiber(
        id=1,
        name="shuffled",
        node_ids=np.arange(6),
        coords=straight.coords[perm].copy(),
        edges=inv[straight.edges],
    )
    a = np.sort(local_curvature_deg(straight))
    b = np.sort(local_curvature_deg(shuffled))
    np.testing.assert_allclose(a[~np.isnan(a)], b[~np.isnan(b)], atol=1e-6)


def test_spacing_uses_edge_lengths_not_row_differences():
    """A shuffled fiber must report the same node spacing as an ordered one."""
    straight = _line_fiber(n=6, spacing=2.0)
    perm = np.array([3, 0, 5, 1, 4, 2])
    inv = np.argsort(perm)
    shuffled = Fiber(
        id=1,
        name="shuffled",
        node_ids=np.arange(6),
        coords=straight.coords[perm].copy(),
        edges=inv[straight.edges],
    )
    dirs, valid = _tube_field()
    for f in (straight, shuffled):
        f.coords[:, 1] += 10.0
        f.coords[:, 2] += 10.0
    a = analyse_cube(Skeleton(fibers=[straight]), dirs, valid, (32, 32, 32))
    b = analyse_cube(Skeleton(fibers=[shuffled]), dirs, valid, (32, 32, 32))
    assert abs(float(np.median(a["spacing"])) - 2.0) < 1e-9
    np.testing.assert_allclose(np.sort(a["spacing"]), np.sort(b["spacing"]), atol=1e-9)


def test_sample_field_uses_nearest_voxel():
    dirs, valid = _tube_field(shape=(8, 8, 8))
    dirs[3, 3, 3] = np.array([0.0, 1.0, 0.0])
    got, defined = sample_field(dirs, valid, np.array([[3.4, 3.4, 2.9]]))
    assert bool(defined[0]) is True
    np.testing.assert_allclose(got[0], np.array([0.0, 1.0, 0.0]), atol=1e-12)
