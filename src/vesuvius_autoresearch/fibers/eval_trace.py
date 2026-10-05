"""Connectivity evaluation for fiber tracing: expected run length, splits, merges.

Why not voxel precision. The ground truth here is a ~1-voxel-wide hand-traced
skeleton, while any detector predicts fibers at their full thickness. A traced
centreline sitting 1-2 voxels off the annotated centreline *inside the same
fiber* is a correct trace, but voxel-wise precision scores it as a miss. Measured
across five tracer configurations, voxel precision plateaued at 0.20-0.22
regardless of coverage, which is the signature of a metric ceiling rather than a
model property (see `reports/fiber_semantic_inference.md`).

What is measured instead follows the 🙋 ask: *"a tracer that confidently follows
fewer fibers correctly is more useful than one that follows more fibers with a
higher error rate."* That is a statement about **run length** and **error type**,
so:

- **ERL (expected run length)**: walk each ground-truth fiber and split it into
  maximal contiguous stretches ("runs") assigned to a single predicted instance.
  ERL is the length-weighted mean run length, `sum(L_i^2) / sum(L_i)`, following
  Januszewski et al. Length-weighting is the point: it answers "if I pick a random
  point on a fiber, how far can I follow it before an error", which is what a
  downstream consumer of fiber connectivity cares about.
- **Splits and merges reported separately, never summed.** A split fails to help;
  a **merge actively corrupts** the U/V parameterization fibers are wanted for. A
  single aggregate would let a merge hide behind good coverage.
- **ERL with a merge penalty**, in which every run of a merging instance counts
  zero. This is the harsh connectomics convention. Both variants are reported
  because the gap between them *is* the merge cost.

Everything is tolerance-aware: a predicted centreline counts as covering a
ground-truth point if it passes within `tolerance` voxels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from vesuvius_autoresearch.fibers.provenance import SCORING_VERSION
from vesuvius_autoresearch.fibers.skeleton_io import Skeleton

# The scoring definition is ScrollGT's (github.com/jonmarrs/scrollgt, v0.4.0, its fiber scoring
# version 2): edges walked in path order, runs ending at stretch boundaries. Everything from
# `ConnectivityScores` to `oracle_from_skeleton` is vendored verbatim, except that ScrollGT's
# `score_tracing` is `_score_tracing_scrollgt` here. tests/test_fiber_scoring_matches_scrollgt.py
# fails if the two drift apart. `score_tracing` below adds input validation only, which never
# changes a score.


@dataclass
class ConnectivityScores:
    """Result of scoring one predicted instance labelling against a skeleton."""

    erl: float
    erl_merge_penalized: float
    coverage: float
    precision: float
    n_gt_fibers: int
    n_pred_instances: int
    splits: int
    merges: int
    merged_instances: int
    gt_length: float
    pred_length: float
    tolerance: float
    run_lengths: list[float] = field(default_factory=list)

    def as_row(self) -> dict:
        """Flat dict for a leaderboard table; excludes the raw run lengths."""
        return {
            "scoring_version": SCORING_VERSION,
            "erl": round(self.erl, 2),
            "erl_merge_penalized": round(self.erl_merge_penalized, 2),
            "coverage": round(self.coverage, 4),
            "precision": round(self.precision, 4),
            "splits": self.splits,
            "merges": self.merges,
            "merged_instances": self.merged_instances,
            "n_gt_fibers": self.n_gt_fibers,
            "n_pred_instances": self.n_pred_instances,
            "gt_length": round(self.gt_length, 1),
            "pred_length": round(self.pred_length, 1),
            "tolerance": self.tolerance,
        }


def _dilate_labels(instances: np.ndarray, radius: float) -> np.ndarray:
    """Grow instance labels by `radius` so a near-miss counts as a hit.

    Nearest-label growth, not binary dilation: a ground-truth point just outside a
    predicted centreline must inherit *that* centreline's id, otherwise tolerance
    would silently merge neighbouring instances.
    """
    if radius <= 0:
        return instances
    from scipy import ndimage

    background = instances == 0
    # distance_transform_edt with return_indices gives, for each background voxel,
    # the index of the nearest non-background voxel.
    dist, (iz, iy, ix) = ndimage.distance_transform_edt(background, return_indices=True)
    out = instances.copy()
    grow = background & (dist <= radius)
    out[grow] = instances[iz[grow], iy[grow], ix[grow]]
    return out


def _edge_walk(edges: np.ndarray):
    """Yield edges as (a, b) in walk order, each continuing from the last.

    Runs are read off the sample sequence, so that sequence has to follow the
    fiber; stored edge rows need not. Reversing only the rows of
    fibers_s1_00497_01497_03997_256 used to move connected-components splits
    265 -> 140. Each walk starts at the lowest-index fiber end (any node, for a
    loop) and takes the lowest-index unused neighbour, so the order depends on
    the graph alone.
    None marks a jump to a new stretch: a branch or a disconnected piece.
    """
    adj: dict[int, list[tuple[int, int]]] = {}
    for k, (a, b) in enumerate(edges):
        adj.setdefault(int(a), []).append((int(b), k))
        adj.setdefault(int(b), []).append((int(a), k))
    used: set[int] = set()
    for start in sorted(adj, key=lambda n: (len(adj[n]) != 1, n)):
        cur, walked = start, False
        while free := [(n, k) for n, k in adj[cur] if k not in used]:
            nxt, k = min(free)
            used.add(k)
            yield cur, nxt
            cur, walked = nxt, True
        if walked:
            yield None


def _resample_fiber(coords: np.ndarray, edges: np.ndarray, step: float = 0.5):
    """Yield (point, segment_length) along a fiber at ~`step` voxel spacing.

    Ground-truth nodes sit 1-2 voxels apart but are not adjacent, so runs must be
    computed on a resampled polyline, walked in path order by `_edge_walk`.
    (None, 0.0) marks the end of a stretch.
    """
    if len(edges) == 0:
        if len(coords):
            yield coords[0], 0.0
        return
    for edge in _edge_walk(edges):
        if edge is None:
            yield None, 0.0
            continue
        a, b = coords[edge[0]], coords[edge[1]]
        seg = float(np.linalg.norm(b - a))
        if seg == 0.0:
            yield a, 0.0
            continue
        n = max(2, int(np.ceil(seg / step)) + 1)
        ts = np.linspace(0.0, 1.0, n)
        dl = seg / (n - 1)
        for t in ts[:-1]:
            yield a + (b - a) * t, dl


def _runs_along_fiber(
    labels: list[int], lengths: list[float]
) -> list[tuple[int, float]]:
    """Collapse a per-sample label sequence into (label, run_length) pairs.

    Background (0) breaks a run and contributes no length, so a gap in the trace
    splits the ground-truth fiber rather than being bridged.
    """
    runs: list[tuple[int, float]] = []
    cur = None
    acc = 0.0
    for lab, dl in zip(labels, lengths, strict=False):
        if lab == 0:
            if cur is not None:
                runs.append((cur, acc))
                cur, acc = None, 0.0
            continue
        if lab != cur:
            if cur is not None:
                runs.append((cur, acc))
            cur, acc = lab, dl
        else:
            acc += dl
    if cur is not None:
        runs.append((cur, acc))
    return [(lab, ln) for lab, ln in runs if ln > 0]


def _fiber_runs(fiber, grown, step, restrict_to_bounds, zeroed=frozenset()):
    """Runs along one fiber, its split count, and its traced and covered length.

    A run cannot continue across a stretch boundary or a skipped out-of-bounds
    stretch: the prediction is not observed there, so bridging it would credit a
    run nobody saw, and breaking it is not the tracer's fault. Splits are
    therefore counted within stretches.
    """
    shape = grown.shape
    runs: list[tuple[int, float]] = []
    splits, total, covered = 0, 0.0, 0.0
    labels: list[int] = []
    lengths: list[float] = []
    samples = _resample_fiber(fiber.coords, fiber.edges, step=step)
    for p, dl in [*samples, (None, 0.0)]:
        idx = None if p is None else tuple(int(round(v)) for v in p)
        if idx is not None and all(0 <= idx[a] < shape[a] for a in range(3)):
            lab = int(grown[idx])
            labels.append(0 if lab in zeroed else lab)
            lengths.append(dl)
        elif idx is not None and not restrict_to_bounds:
            labels.append(0)
            lengths.append(dl)
        elif labels:
            stretch = _runs_along_fiber(labels, lengths)
            runs.extend(stretch)
            splits += max(0, len(stretch) - 1)
            total += float(sum(lengths))
            covered += float(
                sum(d for lab, d in zip(labels, lengths, strict=False) if lab)
            )
            labels, lengths = [], []
    return runs, splits, total, covered


def _score_tracing_scrollgt(
    gt: Skeleton,
    instances: np.ndarray,
    tolerance: float = 2.0,
    step: float = 0.5,
    restrict_to_bounds: bool = True,
) -> ConnectivityScores:
    """Score a predicted instance labelling against hand-traced fibers.

    Args:
        gt: ground-truth skeleton, already localized to the volume.
        instances: (Z, Y, X) int labels; 0 background, distinct ids per fiber.
        tolerance: a prediction covers a ground-truth point if it passes within
            this many voxels. This is the parameter that stops the 1-voxel
            skeleton geometry from dominating the score, so it must be reported
            alongside any number derived from it.
        restrict_to_bounds: ignore ground-truth nodes outside the volume.
            Annotators traced past the cube edge, so 14-34% of nodes are outside
            and scoring them would count guaranteed misses.
    """
    shape = instances.shape
    grown = _dilate_labels(instances, tolerance)

    all_runs: list[float] = []
    per_instance_gt: dict[int, set[int]] = {}
    per_gt_instances: dict[int, set[int]] = {}
    splits = 0
    gt_total = 0.0
    covered = 0.0

    for gi, fiber in enumerate(gt.fibers):
        runs, fiber_splits, fiber_total, fiber_covered = _fiber_runs(
            fiber, grown, step, restrict_to_bounds
        )
        splits += fiber_splits
        gt_total += fiber_total
        covered += fiber_covered
        for lab, ln in runs:
            all_runs.append(ln)
            per_instance_gt.setdefault(lab, set()).add(gi)
            per_gt_instances.setdefault(gi, set()).add(lab)

    # Splits count RUNS, not distinct labels: a ground-truth fiber broken into k
    # contiguous pieces contributes k-1, whether the break is a label change or a
    # gap in the trace. Counting distinct labels instead would score a fiber
    # traced in two disconnected halves under one id as zero splits, which is
    # wrong -- it is fragmented, and fragmentation is the error mode that
    # actually limits this tracer.
    # Merges: an instance covering k ground-truth fibers contributes k-1.
    merges = sum(max(0, len(v) - 1) for v in per_instance_gt.values())
    merged_instances = sum(1 for v in per_instance_gt.values() if len(v) > 1)
    merging_ids = {lab for lab, v in per_instance_gt.items() if len(v) > 1}

    def _erl(runs: list[float]) -> float:
        tot = float(sum(runs))
        if tot <= 0:
            return 0.0
        return float(sum(r * r for r in runs) / tot)

    erl = _erl(all_runs)

    # Merge-penalized: rebuild runs, zeroing any run belonging to a merging id.
    penalized: list[float] = []
    for fiber in gt.fibers:
        runs, _, _, _ = _fiber_runs(fiber, grown, step, restrict_to_bounds, merging_ids)
        penalized.extend(ln for _, ln in runs)
    # Denominator stays the full traced length, so merges genuinely cost ERL.
    tot_all = float(sum(all_runs))
    erl_pen = float(sum(r * r for r in penalized) / tot_all) if tot_all > 0 else 0.0

    # Precision: predicted length within tolerance of any ground-truth fiber.
    gt_mask = np.zeros(shape, dtype=bool)
    for fiber in gt.fibers:
        for p, _ in _resample_fiber(fiber.coords, fiber.edges, step=step):
            if p is None:
                continue
            idx = tuple(int(round(v)) for v in p)
            if all(0 <= idx[a] < shape[a] for a in range(3)):
                gt_mask[idx] = True
    if tolerance > 0 and gt_mask.any():
        from scipy import ndimage

        gt_near = ndimage.distance_transform_edt(~gt_mask) <= tolerance
    else:
        gt_near = gt_mask
    pred_vox = instances > 0
    pred_length = float(pred_vox.sum())
    precision = (
        float((pred_vox & gt_near).sum() / pred_length) if pred_length > 0 else 0.0
    )

    return ConnectivityScores(
        erl=erl,
        erl_merge_penalized=erl_pen,
        coverage=(covered / gt_total) if gt_total > 0 else 0.0,
        precision=precision,
        n_gt_fibers=len(gt.fibers),
        n_pred_instances=int(len(set(np.unique(instances)) - {0})),
        splits=splits,
        merges=merges,
        merged_instances=merged_instances,
        gt_length=gt_total,
        pred_length=pred_length,
        tolerance=tolerance,
        run_lengths=all_runs,
    )


# --- anti-gaming floors ------------------------------------------------------
#
# Every one of these is a way to score well on a badly-chosen metric. Publishing
# them alongside a real result is what makes the real result meaningful; if the
# tracer cannot beat them, that must be stated rather than hidden.


def _validate_fiber(fiber) -> None:
    coords, edges = np.asarray(fiber.coords), np.asarray(fiber.edges)
    if coords.ndim != 2 or coords.shape[1] != 3 or not np.isfinite(coords).all():
        raise ValueError("skeleton coordinates must be finite with shape (N, 3)")
    if len(edges) and (
        edges.ndim != 2
        or edges.shape[1] != 2
        or edges.dtype.kind not in "ui"
        or np.any(edges < 0)
        or np.any(edges >= len(coords))
    ):
        raise ValueError("skeleton edges must be valid integer node pairs")


def score_tracing(
    gt: Skeleton,
    instances: np.ndarray,
    tolerance: float = 2.0,
    step: float = 0.5,
    restrict_to_bounds: bool = True,
) -> ConnectivityScores:
    """Validate the inputs, then score with ScrollGT's definition (`_score_tracing_scrollgt`).

    Rejects what would otherwise be scored silently: non-integer, negative or empty instance
    arrays, nonfinite or nonpositive step, negative tolerance, and malformed skeletons.
    """
    instances = np.asarray(instances)
    if (
        instances.ndim != 3
        or any(s == 0 for s in instances.shape)
        or instances.dtype.kind not in "ui"
        or np.any(instances < 0)
    ):
        raise ValueError(
            "instances must be nonnegative integer labels with nonempty shape (Z, Y, X)"
        )
    for name, value in [("tolerance", tolerance), ("step", step)]:
        if (
            isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, float, np.integer, np.floating))
            or not math.isfinite(value)
            or (value < 0 if name == "tolerance" else value <= 0)
        ):
            raise ValueError(
                f"{name} must be finite and {'nonnegative' if name == 'tolerance' else 'positive'}"
            )
    for fiber in gt.fibers:
        _validate_fiber(fiber)
    return _score_tracing_scrollgt(gt, instances, tolerance, step, restrict_to_bounds)


def floor_single_instance(mask: np.ndarray) -> np.ndarray:
    """Label every fiber voxel as ONE instance. Maximal coverage, maximal merges.

    Scores perfectly on any coverage-only metric, which is exactly why coverage
    alone must never be the headline.
    """
    return (np.asarray(mask) > 0).astype(np.int32)


def floor_voxel_instances(mask: np.ndarray) -> np.ndarray:
    """One instance per voxel. Zero merges, maximal splits, ERL ~ one voxel."""
    m = np.asarray(mask) > 0
    out = np.zeros(m.shape, dtype=np.int32)
    out[m] = np.arange(1, int(m.sum()) + 1, dtype=np.int32)
    return out


def floor_connected_components(mask: np.ndarray, connectivity: int = 3) -> np.ndarray:
    """Connected components of the semantic mask: the obvious naive baseline.

    This is the floor that matters most. If a tracer cannot beat plain connected
    components of the fiber probability, it is not adding anything, because
    touching fibers get merged into one component.
    """
    from scipy import ndimage

    st = ndimage.generate_binary_structure(3, connectivity)
    lab, _ = ndimage.label(np.asarray(mask) > 0, structure=st)
    return lab.astype(np.int32)


def floor_random_instances(mask: np.ndarray, n: int = 50, seed: int = 0) -> np.ndarray:
    """Assign fiber voxels to `n` random instances. Destroys connectivity."""
    rng = np.random.default_rng(seed)
    m = np.asarray(mask) > 0
    out = np.zeros(m.shape, dtype=np.int32)
    out[m] = rng.integers(1, n + 1, size=int(m.sum()), dtype=np.int32)
    return out


def oracle_from_skeleton(gt: Skeleton, shape, radius: float = 1.0) -> np.ndarray:
    """Rasterize the ground truth itself: the ceiling, for sanity-checking ERL.

    A correct implementation must score this near the length-weighted mean
    ground-truth fiber length, with zero splits and zero merges. It is disclosed
    as an oracle, never as a result.
    """
    from vesuvius_autoresearch.fibers.skeleton_io import rasterize

    inst = rasterize(gt, tuple(shape))
    if radius > 0:
        inst = _dilate_labels(inst, radius)
    return inst
