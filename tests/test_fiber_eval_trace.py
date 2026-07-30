"""Connectivity metrics: ERL, splits, merges, and the anti-gaming floors.

The critical tests here are the ones that prove the *metric* is right, not the
tracer: an oracle must score at the ceiling, a single merged instance must be
punished, and one-instance-per-voxel must collapse ERL. If those hold, numbers
produced by this harness mean something.
"""

from __future__ import annotations

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.eval_trace import (
    ConnectivityScores,
    floor_connected_components,
    floor_random_instances,
    floor_single_instance,
    floor_voxel_instances,
    oracle_from_skeleton,
    score_tracing,
)
from vesuvius_autoresearch.fibers.skeleton_io import Fiber, Skeleton


def _straight_fiber(fid, z, y, x0, x1, n=None):
    n = n or (x1 - x0 + 1)
    xs = np.linspace(x0, x1, n)
    coords = np.stack([np.full(n, z, float), np.full(n, y, float), xs], axis=1)
    edges = np.array([[i, i + 1] for i in range(n - 1)], dtype=np.int64)
    return Fiber(
        id=fid, name=f"f{fid}", node_ids=np.arange(n), coords=coords, edges=edges
    )


def _three_fibers():
    """Three parallel straight fibers of length 40, well separated in y."""
    return Skeleton(
        fibers=[
            _straight_fiber(1, 16, 8, 5, 45),
            _straight_fiber(2, 16, 16, 5, 45),
            _straight_fiber(3, 16, 24, 5, 45),
        ],
        scale_um=(7.91, 7.91, 7.91),
        origin_zyx=(0, 0, 0),
    )


SHAPE = (32, 32, 52)


def test_oracle_scores_at_the_ceiling():
    """Rasterized ground truth must give ERL ~= fiber length, 0 splits, 0 merges.

    This validates the ERL implementation itself. If an oracle does not score at
    the ceiling, every other number from this harness is suspect.
    """
    gt = _three_fibers()
    inst = oracle_from_skeleton(gt, SHAPE, radius=1.0)
    s = score_tracing(gt, inst, tolerance=2.0)

    assert s.splits == 0, f"oracle should not split: {s.splits}"
    assert s.merges == 0, f"oracle should not merge: {s.merges}"
    assert s.coverage > 0.99, f"oracle coverage {s.coverage:.3f}"
    # Each fiber is 40 voxels long; ERL should be close to that.
    assert 35.0 <= s.erl <= 41.0, f"oracle ERL {s.erl:.1f}, expected ~40"
    assert s.erl_merge_penalized == pytest.approx(s.erl, rel=1e-6)


def test_single_instance_floor_is_punished_for_merging():
    """Max coverage, but one instance covering all three fibers is worthless."""
    gt = _three_fibers()
    mask = oracle_from_skeleton(gt, SHAPE, radius=1.0) > 0
    inst = floor_single_instance(mask)
    s = score_tracing(gt, inst, tolerance=2.0)

    assert s.n_pred_instances == 1
    assert s.coverage > 0.99, "the floor does achieve full coverage"
    assert s.merges == 2, f"one instance over 3 fibers = 2 merges, got {s.merges}"
    assert s.merged_instances == 1
    # Raw ERL looks fine because each fiber is one long run; the penalty is what
    # exposes it. That contrast is the reason both are reported.
    assert s.erl_merge_penalized == 0.0, (
        f"merge-penalized ERL must be 0, got {s.erl_merge_penalized:.2f}"
    )


def test_voxel_instances_floor_collapses_erl():
    gt = _three_fibers()
    mask = oracle_from_skeleton(gt, SHAPE, radius=1.0) > 0
    inst = floor_voxel_instances(mask)
    s = score_tracing(gt, inst, tolerance=0.0)

    assert s.erl < 3.0, f"per-voxel instances should collapse ERL, got {s.erl:.2f}"
    assert s.merges == 0, "per-voxel instances cannot merge"
    assert s.splits > 50, f"expected many splits, got {s.splits}"


def test_random_instances_floor_scores_poorly():
    gt = _three_fibers()
    mask = oracle_from_skeleton(gt, SHAPE, radius=1.0) > 0
    inst = floor_random_instances(mask, n=20, seed=0)
    s = score_tracing(gt, inst, tolerance=0.0)
    oracle = score_tracing(gt, oracle_from_skeleton(gt, SHAPE, 1.0), tolerance=0.0)
    assert s.erl < 0.5 * oracle.erl, (
        f"random labelling ERL {s.erl:.1f} not clearly below oracle {oracle.erl:.1f}"
    )


def test_connected_components_floor_merges_touching_fibers():
    """The floor that matters: touching fibers become one component."""
    # Two fibers only 1 voxel apart, so a thickened mask connects them.
    gt = Skeleton(
        fibers=[_straight_fiber(1, 16, 15, 5, 45), _straight_fiber(2, 16, 17, 5, 45)],
        origin_zyx=(0, 0, 0),
    )
    mask = oracle_from_skeleton(gt, SHAPE, radius=1.0) > 0
    inst = floor_connected_components(mask)
    s = score_tracing(gt, inst, tolerance=2.0)
    assert s.n_pred_instances == 1, "expected the two fibers to fuse"
    assert s.merges == 1
    assert s.erl_merge_penalized == 0.0


def test_a_split_reduces_erl_without_creating_merges():
    """Cutting one fiber in half should halve its runs, not register a merge."""
    gt = Skeleton(fibers=[_straight_fiber(1, 16, 16, 5, 45)], origin_zyx=(0, 0, 0))
    inst = oracle_from_skeleton(gt, SHAPE, radius=1.0)
    whole = score_tracing(gt, inst, tolerance=2.0)

    # Relabel the second half as a different instance id.
    cut = inst.copy()
    cut[:, :, 26:] = np.where(cut[:, :, 26:] > 0, 7, 0)
    split = score_tracing(gt, cut, tolerance=2.0)

    assert split.merges == 0, "a clean split must not be reported as a merge"
    assert split.splits == 1, f"expected 1 split, got {split.splits}"
    assert split.erl < whole.erl, "splitting must reduce ERL"
    assert split.erl == pytest.approx(whole.erl / 2, rel=0.25)


def test_gap_is_not_bridged_and_costs_coverage():
    gt = Skeleton(fibers=[_straight_fiber(1, 16, 16, 5, 45)], origin_zyx=(0, 0, 0))
    inst = oracle_from_skeleton(gt, SHAPE, radius=1.0)
    holed = inst.copy()
    holed[:, :, 22:30] = 0
    s = score_tracing(gt, holed, tolerance=0.0)
    assert s.coverage < 0.85, f"gap should cost coverage, got {s.coverage:.3f}"
    assert s.splits == 1, "a gap splits the fiber into two runs of one instance"


def test_tolerance_rescues_a_one_voxel_offset():
    """The reason this harness exists: 1-voxel offset is not an error."""
    gt = Skeleton(fibers=[_straight_fiber(1, 16, 16, 5, 45)], origin_zyx=(0, 0, 0))
    # Predicted centreline runs parallel, offset by 2 voxels in y.
    shifted = Skeleton(fibers=[_straight_fiber(1, 16, 18, 5, 45)], origin_zyx=(0, 0, 0))
    inst = oracle_from_skeleton(shifted, SHAPE, radius=0.0)

    strict = score_tracing(gt, inst, tolerance=0.0)
    lenient = score_tracing(gt, inst, tolerance=2.5)
    assert strict.coverage < 0.05, "strict scoring should see almost nothing"
    assert lenient.coverage > 0.95, (
        f"tolerance should recognise the offset trace, got {lenient.coverage:.3f}"
    )
    assert lenient.erl > 10 * max(strict.erl, 1e-6)


def test_tolerance_does_not_silently_merge_neighbours():
    """Growing labels must use nearest-label, not blanket dilation."""
    gt = Skeleton(
        fibers=[_straight_fiber(1, 16, 14, 5, 45), _straight_fiber(2, 16, 20, 5, 45)],
        origin_zyx=(0, 0, 0),
    )
    inst = oracle_from_skeleton(gt, SHAPE, radius=0.0)
    s = score_tracing(gt, inst, tolerance=2.5)
    assert s.merges == 0, "tolerance leaked labels across fibers"
    assert s.n_pred_instances == 2


def test_empty_prediction_is_zero_not_an_error():
    gt = _three_fibers()
    s = score_tracing(gt, np.zeros(SHAPE, dtype=np.int32), tolerance=2.0)
    assert s.erl == 0.0 and s.coverage == 0.0 and s.precision == 0.0
    assert s.merges == 0 and s.splits == 0


def test_out_of_bounds_gt_nodes_are_excluded():
    """Annotators traced past the cube edge; scoring those is a guaranteed miss."""
    gt = Skeleton(fibers=[_straight_fiber(1, 16, 16, -20, 70)], origin_zyx=(0, 0, 0))
    inst = oracle_from_skeleton(gt, SHAPE, radius=1.0)
    inside = score_tracing(gt, inst, tolerance=2.0, restrict_to_bounds=True)
    outside = score_tracing(gt, inst, tolerance=2.0, restrict_to_bounds=False)
    assert inside.coverage > 0.95
    assert outside.coverage < inside.coverage
    assert inside.gt_length < outside.gt_length


def test_as_row_is_serialisable():
    gt = _three_fibers()
    s = score_tracing(gt, oracle_from_skeleton(gt, SHAPE, 1.0), tolerance=2.0)
    row = s.as_row()
    import json

    json.loads(json.dumps(row))
    assert "erl" in row and "merges" in row and "tolerance" in row
    assert "run_lengths" not in row


def test_scores_dataclass_reports_tolerance():
    """A number from this harness is meaningless without its tolerance."""
    gt = _three_fibers()
    s = score_tracing(gt, oracle_from_skeleton(gt, SHAPE, 1.0), tolerance=1.75)
    assert isinstance(s, ConnectivityScores)
    assert s.tolerance == 1.75
