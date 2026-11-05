"""Connectivity metrics: ERL, splits, merges, and the anti-gaming floors.

The critical tests here are the ones that prove the *metric* is right, not the
tracer: an oracle must score at the ceiling, a single merged instance must be
punished, and one-instance-per-voxel must collapse ERL. If those hold, numbers
produced by this harness mean something.
"""

from __future__ import annotations

from dataclasses import replace

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


# --- graph validation ---------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        "every edge again",
        "every edge again, reversed",
        "one edge again",
    ],
)
def test_a_duplicated_edge_is_rejected_not_scored(extra):
    """The path-order walk goes out and back across a duplicate, ending a stretch
    every edge. Unvalidated, a perfect trace of this 40-voxel fiber scored ERL 2.00
    (all edges doubled, either orientation) or 20.61 (one edge doubled) instead of
    40.00, with full coverage and no splits or merges to flag it. None of the 21
    ScrollGT v0.7.0 fiber cubes contains a duplicate, so no published score moves."""
    fiber = _straight_fiber(1, 16, 16, 5, 45)
    gt = Skeleton(fibers=[fiber])
    inst = oracle_from_skeleton(gt, SHAPE, 1.0)
    added = {
        "every edge again": fiber.edges,
        "every edge again, reversed": fiber.edges[:, ::-1],
        "one edge again": fiber.edges[[20]],
    }[extra]
    doubled = Skeleton(fibers=[replace(fiber, edges=np.vstack([fiber.edges, added]))])
    with pytest.raises(ValueError, match="duplicate"):
        score_tracing(doubled, inst, tolerance=0)


def test_branches_loops_and_zero_length_edges_still_score():
    """Validation targets duplicates only; legitimate graph shapes are unaffected."""
    fiber = _straight_fiber(1, 16, 16, 5, 45)
    inst = oracle_from_skeleton(Skeleton(fibers=[fiber]), SHAPE, 1.0)
    reference = score_tracing(Skeleton(fibers=[fiber]), inst, tolerance=0).as_row()
    branched = replace(
        fiber,
        node_ids=np.arange(len(fiber.coords) + 1),
        coords=np.vstack([fiber.coords, [[16.0, 20.0, 25.0]]]),
        edges=np.vstack([fiber.edges, [[20, len(fiber.coords)]]]),
    )
    loop = replace(fiber, edges=np.vstack([fiber.edges, [[len(fiber.coords) - 1, 0]]]))
    self_edge = replace(fiber, edges=np.vstack([fiber.edges, [[7, 7]]]))
    for variant in (branched, loop):
        assert (
            score_tracing(Skeleton(fibers=[variant]), inst, tolerance=0).gt_length > 40
        )
    zero = score_tracing(Skeleton(fibers=[self_edge]), inst, tolerance=0).as_row()
    assert zero == reference


# ScrollGT 0.9.1 computes the two distance transforms in z slabs with a ceil(radius) halo (#339). The sync test
# compares the vendored code with ScrollGT's, both slabbed, and skips without a ScrollGT checkout. These tests hold
# the slabs to the whole-volume transform they replaced, which is what "changes no score" means.


def _whole_volume_dilation(instances, radius):
    """`_dilate_labels` before ScrollGT 0.9.1: one transform over the whole volume."""
    from scipy import ndimage

    background = instances == 0
    distance, (iz, iy, ix) = ndimage.distance_transform_edt(
        background, return_indices=True
    )
    out = instances.copy()
    grow = background & (distance <= radius)
    out[grow] = instances[iz[grow], iy[grow], ix[grow]]
    return out


def _slab_test_labels(seed):
    """Labels in the middle slabs, with ties straddling their boundaries, and one in the last slice. The first slab
    and its halo are empty: SciPy measures an all-background window to an outside (-1, 0, 0) seed, whose index
    would wrap to that last-slice label."""
    from vesuvius_autoresearch.fibers import eval_trace as ev

    block = ev._EDT_BLOCK_DEPTH
    rng = np.random.default_rng(seed)
    labels = np.zeros((4 * block + 7, 9, 9), np.int32)
    part = labels[2 * block : 3 * block]
    hit = rng.random(part.shape) < 0.02
    part[hit] = rng.integers(1, 5, int(hit.sum()))
    for b in (2 * block, 3 * block):
        labels[b - 2, 4, 4], labels[b + 2, 4, 4] = 5, 6
        labels[b - 3, 2, 6], labels[b + 1, 6, 2] = 7, 8
    labels[-1, 0, 0] = 9
    return labels


@pytest.mark.parametrize("radius", [0.5, 1.0, 2.0, 2.5, 4.0, 70.0])
def test_slab_distance_transforms_equal_the_whole_volume_transform(radius):
    from scipy import ndimage

    from vesuvius_autoresearch.fibers import eval_trace as ev

    labels = _slab_test_labels(int(10 * radius))
    np.testing.assert_array_equal(
        ev._dilate_labels(labels, radius), _whole_volume_dilation(labels, radius)
    )
    gt = labels > 0
    near = np.zeros(gt.shape, bool)
    for slab, distance, _ in ev._distance_blocks(~gt, radius):
        near[slab] = distance <= radius
    np.testing.assert_array_equal(near, ndimage.distance_transform_edt(~gt) <= radius)


@pytest.mark.parametrize("tolerance", [1.0, 2.0, 4.0])
def test_slab_scores_equal_whole_volume_scores(monkeypatch, tolerance):
    from vesuvius_autoresearch.fibers import eval_trace as ev

    depth = 4 * ev._EDT_BLOCK_DEPTH + 7
    n = depth - 4
    fibers = []
    for fid, (y, x) in enumerate([(3, 3), (3, 9), (9, 6)], start=1):
        coords = np.stack(
            [np.linspace(2, depth - 3, n), np.full(n, y, float), np.full(n, x, float)],
            axis=1,
        )
        edges = np.array([[i, i + 1] for i in range(n - 1)], dtype=np.int64)
        fibers.append(
            Fiber(
                id=fid,
                name=f"f{fid}",
                node_ids=np.arange(n),
                coords=coords,
                edges=edges,
            )
        )
    gt = Skeleton(fibers=fibers, scale_um=(7.91,) * 3, origin_zyx=(0, 0, 0))
    rng = np.random.default_rng(int(tolerance))
    inst = np.zeros((depth, 13, 13), np.int32)
    for fid, (y, x) in enumerate([(3, 3), (3, 9), (9, 6)], start=1):
        for z in range(2, depth - 3):
            if rng.random() < 0.9:
                dy, dx = rng.integers(-1, 2, 2)
                inst[z, y + dy, x + dx] = fid + 3 * int(z // 50)
    inst[rng.random(inst.shape) < 0.002] = 99
    slab = ev.score_tracing(gt, inst, tolerance=tolerance).as_row()
    monkeypatch.setattr(ev, "_EDT_BLOCK_DEPTH", depth)
    assert ev.score_tracing(gt, inst, tolerance=tolerance).as_row() == slab


def test_precision_counts_a_voxel_exactly_at_the_tolerance():
    """A predicted voxel exactly `tolerance` from the reference is on it (`<=`, as ScrollGT counts)."""
    gt = Skeleton(
        fibers=[_straight_fiber(1, 16, 8, 5, 45)],
        scale_um=(7.91, 7.91, 7.91),
        origin_zyx=(0, 0, 0),
    )
    inst = np.zeros(SHAPE, np.int32)
    inst[16, 10, 6:45] = 1  # two voxels from the fiber's interior
    assert score_tracing(gt, inst, tolerance=2.0).as_row()["precision"] == 1.0
    assert score_tracing(gt, inst, tolerance=1.9).as_row()["precision"] == 0.0
