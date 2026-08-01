"""Ground-truth tangent extraction and sign-ambiguous angular error."""

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.field_quality import (
    NodeKind,
    count_node_kinds,
    gt_tangents,
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
