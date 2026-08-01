"""Characterise the orientation field against hand-traced ground truth.

Every walker-level fix attempted on this tracer -- tangent smoothing, bounded
coasting, seed non-maximum suppression -- assumed the orientation field is
accurate enough to follow. That assumption was never measured. This module
measures it: the angle between the Hessian tangent and the true fiber tangent,
at ground-truth nodes.

Two ways to estimate the ground-truth tangent at an interior node are provided,
and they are not the same thing. `gt_tangents` uses the straight-line chord
between a node's two neighbours -- a length-weighted secant estimate that
coincides with the true angle bisector of the two edge directions only when
both edges happen to be equal length. Real hand-traced NML skeletons have
irregular node spacing, so on an unevenly-sampled node the chord leans toward
the longer edge. `gt_tangents_bisector` instead averages the two *unit* edge
directions, which is the equal-weight bisector regardless of spacing.
`tangent_estimator_disagreement` measures how far apart the two get on a given
fiber, so that any downstream angular-error measurement can report whether the
ground-truth reference itself is uncertain, rather than silently assuming it
is exact.

Read-only by construction. Nothing here changes tracer behaviour.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from .skeleton_io import Fiber


class NodeKind:
    """Why a ground-truth node was used or excluded.

    A plain class with `str` class attributes, not `enum.Enum` -- equality,
    dict-key lookups and `in` all behave the same as a real enum, but
    `isinstance(x, NodeKind)` would silently be False. Do not write that check.
    """

    INTERIOR = "interior"
    ENDPOINT = "endpoint"
    BRANCH = "branch"
    ISOLATED = "isolated"
    DEGENERATE = "degenerate"


def _adjacency(fiber: Fiber) -> dict[int, list[int]]:
    adj: dict[int, list[int]] = defaultdict(list)
    for a, b in np.asarray(fiber.edges, dtype=int):
        adj[int(a)].append(int(b))
        adj[int(b)].append(int(a))
    return adj


def _raw_tangent(coords: np.ndarray, i: int, nbrs: list[int]) -> np.ndarray | None:
    """Unnormalised chord (secant) tangent estimate at node i, or None if none exists.

    For an interior node this is `coords[nbrs[1]] - coords[nbrs[0]]`, the
    straight-line chord between its two neighbours. That chord equals the true
    angle bisector of the two edge directions only when both edges have equal
    length -- using one edge alone would bias the tangent toward that edge, but
    the chord itself is still a *length-weighted* estimate that leans toward
    whichever edge is longer when the two are unequal. See
    `_bisector_tangent` / `gt_tangents_bisector` for the equal-weight
    alternative and `tangent_estimator_disagreement` for measuring how much
    this matters on a given fiber.
    """
    if len(nbrs) == 1:
        return coords[nbrs[0]] - coords[i]
    if len(nbrs) == 2:
        return coords[nbrs[1]] - coords[nbrs[0]]
    return None


def _bisector_tangent(coords: np.ndarray, i: int, nbrs: list[int]) -> np.ndarray | None:
    """Unnormalised equal-weight bisector tangent estimate at node i, or None.

    For an interior node this averages the two *unit* edge directions --
    `unit(coords[nbrs[1]] - coords[i]) + unit(coords[i] - coords[nbrs[0]])` --
    which bisects the incoming and outgoing directions regardless of how
    unevenly the two edges are spaced, unlike the length-weighted chord in
    `_raw_tangent`. Falls back to the chord when a node doubles back on itself
    (the incoming and outgoing unit directions are exactly opposite, so their
    sum is ~0 and the bisector is undefined), or when either edge has ~zero
    length (its unit direction is undefined).
    """
    if len(nbrs) == 1:
        return coords[nbrs[0]] - coords[i]
    if len(nbrs) == 2:
        out_dir = coords[nbrs[1]] - coords[i]
        in_dir = coords[i] - coords[nbrs[0]]
        out_n = float(np.linalg.norm(out_dir))
        in_n = float(np.linalg.norm(in_dir))
        if out_n < 1e-9 or in_n < 1e-9:
            return _raw_tangent(coords, i, nbrs)
        summed = out_dir / out_n + in_dir / in_n
        if float(np.linalg.norm(summed)) < 1e-9:
            return _raw_tangent(coords, i, nbrs)
        return summed
    return None


def count_node_kinds(fiber: Fiber) -> dict[str, int]:
    """Count every node by kind, including the ones `gt_tangents` excludes."""
    coords = np.asarray(fiber.coords, dtype=float)
    adj = _adjacency(fiber)
    counts = {
        k: 0
        for k in (
            NodeKind.INTERIOR,
            NodeKind.ENDPOINT,
            NodeKind.BRANCH,
            NodeKind.ISOLATED,
            NodeKind.DEGENERATE,
        )
    }
    for i in range(len(coords)):
        nbrs = adj.get(i, [])
        if len(nbrs) == 0:
            counts[NodeKind.ISOLATED] += 1
            continue
        if len(nbrs) >= 3:
            counts[NodeKind.BRANCH] += 1
            continue
        raw = _raw_tangent(coords, i, nbrs)
        if raw is None or float(np.linalg.norm(raw)) < 1e-9:
            counts[NodeKind.DEGENERATE] += 1
            continue
        counts[NodeKind.ENDPOINT if len(nbrs) == 1 else NodeKind.INTERIOR] += 1
    return counts


def gt_tangents(fiber: Fiber) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Coordinates, unit tangents and kinds for every usable node of one fiber.

    Interior-node tangents are the chord (secant) between a node's two
    neighbours: `coords[n1] - coords[n0]`. This is a standard, legitimate
    estimator, but it is a length-weighted one -- it coincides with the true
    bisector of the two edge directions only when both edges are equal length,
    and on unevenly-spaced real NML nodes it leans toward the longer edge. See
    `gt_tangents_bisector` for the equal-weight alternative and
    `tangent_estimator_disagreement` to measure how much that matters here.

    Branch nodes (degree >= 3) are excluded: a junction has no single tangent,
    and silently picking one would inject error that is not the field's fault.
    Isolated and zero-length cases are excluded for the same reason. All of them
    are still counted by `count_node_kinds`.
    """
    coords = np.asarray(fiber.coords, dtype=float)
    adj = _adjacency(fiber)

    out_c: list[np.ndarray] = []
    out_t: list[np.ndarray] = []
    kinds: list[str] = []

    for i in range(len(coords)):
        nbrs = adj.get(i, [])
        if len(nbrs) == 0 or len(nbrs) >= 3:
            continue
        raw = _raw_tangent(coords, i, nbrs)
        if raw is None:
            continue
        n = float(np.linalg.norm(raw))
        if n < 1e-9:
            continue
        out_c.append(coords[i])
        out_t.append(raw / n)
        kinds.append(NodeKind.ENDPOINT if len(nbrs) == 1 else NodeKind.INTERIOR)

    if not out_c:
        return np.zeros((0, 3)), np.zeros((0, 3)), []
    return np.asarray(out_c), np.asarray(out_t), kinds


def gt_tangents_bisector(fiber: Fiber) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Coordinates, unit tangents and kinds using the equal-weight bisector.

    Same signature, same node inclusion/exclusion rules, and the same
    coordinates/kinds as `gt_tangents` -- branch, isolated and zero-length-chord
    nodes are excluded and counted identically, and endpoint tangents are
    identical (a single neighbour has only one direction to estimate). The only
    difference is the interior-node tangent: this averages the two *unit* edge
    directions (the true angle bisector) instead of taking the raw chord, so it
    is unaffected by unequal edge lengths. See `_bisector_tangent` for the
    doubling-back fallback.
    """
    coords = np.asarray(fiber.coords, dtype=float)
    adj = _adjacency(fiber)

    out_c: list[np.ndarray] = []
    out_t: list[np.ndarray] = []
    kinds: list[str] = []

    for i in range(len(coords)):
        nbrs = adj.get(i, [])
        if len(nbrs) == 0 or len(nbrs) >= 3:
            continue
        # Exclusion is decided from the chord, exactly as in `gt_tangents`, so
        # the two functions exclude and count precisely the same set of nodes.
        raw = _raw_tangent(coords, i, nbrs)
        if raw is None:
            continue
        raw_n = float(np.linalg.norm(raw))
        if raw_n < 1e-9:
            continue
        tangent = _bisector_tangent(coords, i, nbrs)
        if tangent is None:
            continue
        t_n = float(np.linalg.norm(tangent))
        if t_n < 1e-9:
            # Should not happen given the fallback in `_bisector_tangent`, but
            # guard against it rather than emit a non-unit or NaN vector.
            tangent = raw
            t_n = raw_n
        out_c.append(coords[i])
        out_t.append(tangent / t_n)
        kinds.append(NodeKind.ENDPOINT if len(nbrs) == 1 else NodeKind.INTERIOR)

    if not out_c:
        return np.zeros((0, 3)), np.zeros((0, 3)), []
    return np.asarray(out_c), np.asarray(out_t), kinds


def tangent_estimator_disagreement(fiber: Fiber) -> np.ndarray:
    """Per-node angle, in degrees, between the chord and bisector tangent estimates.

    Uses the same exclusion rules as `gt_tangents` / `gt_tangents_bisector`, so
    the result has one entry per usable node, in the same order as their
    `coords`. A small value on real cubes means the chord-vs-bisector choice
    does not matter for this fiber; a large value means the node spacing is
    uneven enough that the ground-truth tangent itself is uncertain, and any
    measured field-vs-ground-truth angular error is only an upper bound.
    """
    _, chord_t, _ = gt_tangents(fiber)
    _, bisector_t, _ = gt_tangents_bisector(fiber)
    if len(chord_t) == 0:
        return np.zeros(0)
    dots = np.clip(np.sum(chord_t * bisector_t, axis=1), -1.0, 1.0)
    return np.degrees(np.arccos(dots))


def angular_error_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Angle between two orientation fields, in degrees, modulo 180.

    Taking `abs` of the dot product is what makes this an *orientation*
    comparison rather than a *direction* one. An eigenvector field is defined
    only up to sign, so `-t` is exactly as correct as `t`; scoring the flip as
    180 degrees would make a perfectly good field look catastrophic. Errors
    therefore live in [0, 90], and 90 means "perpendicular", the worst possible.
    """
    a = np.atleast_2d(np.asarray(a, dtype=float))
    b = np.atleast_2d(np.asarray(b, dtype=float))
    na = np.linalg.norm(a, axis=1, keepdims=True)
    nb = np.linalg.norm(b, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        a = a / np.where(na < 1e-12, np.nan, na)
        b = b / np.where(nb < 1e-12, np.nan, nb)
    cos = np.abs(np.sum(a * b, axis=1))
    return np.degrees(np.arccos(np.clip(cos, 0.0, 1.0)))


def sample_field(
    dirs: np.ndarray, valid: np.ndarray, coords: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-voxel lookup of the orientation field at float coordinates.

    Nearest-neighbour rather than interpolation, because that is what
    ``_direction_at`` does during a walk -- this must characterise the field the
    tracer actually sees, not a smoothed version of it. Out-of-bounds positions
    are reported undefined rather than clipped: clipping would silently score an
    edge voxel against a ground-truth node lying outside the cube.
    """
    coords = np.atleast_2d(np.asarray(coords, dtype=float))
    idx = np.rint(coords).astype(int)
    shape = np.asarray(valid.shape)

    inb = np.ones(len(idx), dtype=bool)
    for a in range(3):
        inb &= (idx[:, a] >= 0) & (idx[:, a] < shape[a])

    out = np.zeros((len(idx), 3), dtype=float)
    defined = np.zeros(len(idx), dtype=bool)
    if inb.any():
        sel = idx[inb]
        out[inb] = dirs[sel[:, 0], sel[:, 1], sel[:, 2]]
        defined[inb] = valid[sel[:, 0], sel[:, 1], sel[:, 2]]
    return out, defined


def local_curvature_deg(
    coords: np.ndarray, tangents: np.ndarray, kinds: list[str]
) -> np.ndarray:
    """Turn angle at each interior node, in degrees. NaN at endpoints.

    Separates "the orientation field is noisy" from "the fiber genuinely bends
    more than the walker's turn limit". If real curvature routinely exceeds
    ``max_angle_deg``, that limit is simply mis-set and no amount of field
    improvement will help.
    """
    n = len(coords)
    out = np.full(n, np.nan, dtype=float)
    for i in range(n):
        if kinds[i] != NodeKind.INTERIOR or i == 0 or i == n - 1:
            continue
        out[i] = float(
            angular_error_deg(tangents[i - 1][None, :], tangents[i + 1][None, :])[0]
        )
    return out


def perpendicular_offsets(tangent: np.ndarray, radius: float, n: int = 6) -> np.ndarray:
    """``n`` vectors of length ``radius``, evenly spaced in the plane normal to ``tangent``."""
    t = np.asarray(tangent, dtype=float)
    t = t / max(float(np.linalg.norm(t)), 1e-12)
    seed = np.array([1.0, 0.0, 0.0]) if abs(t[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(t, seed)
    u /= max(float(np.linalg.norm(u)), 1e-12)
    v = np.cross(t, u)
    ang = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return radius * (
        np.cos(ang)[:, None] * u[None, :] + np.sin(ang)[:, None] * v[None, :]
    )


def analyse_cube(
    skeleton,
    dirs: np.ndarray,
    valid: np.ndarray,
    shape: tuple[int, int, int],
    offsets: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0),
) -> dict:
    """Angular error of the orientation field against one cube's ground truth."""
    kind_counts = {
        k: 0
        for k in (
            NodeKind.INTERIOR,
            NodeKind.ENDPOINT,
            NodeKind.BRANCH,
            NodeKind.ISOLATED,
            NodeKind.DEGENERATE,
        )
    }
    all_err: list[np.ndarray] = []
    all_curv: list[np.ndarray] = []
    all_spacing: list[np.ndarray] = []
    all_disagree: list[np.ndarray] = []
    n_nodes = 0
    n_undefined = 0
    off_err: dict[float, list[np.ndarray]] = {float(o): [] for o in offsets}

    for fib in skeleton.fibers:
        for k, v in count_node_kinds(fib).items():
            kind_counts[k] += v

        coords, tangents, kinds = gt_tangents(fib)
        if len(coords) == 0:
            continue

        sampled, defined = sample_field(dirs, valid, coords)
        n_nodes += len(coords)
        n_undefined += int((~defined).sum())
        if defined.any():
            all_err.append(angular_error_deg(tangents[defined], sampled[defined]))
            curv = local_curvature_deg(coords, tangents, kinds)
            all_curv.append(curv[defined])
            dis = tangent_estimator_disagreement(fib)
            if len(dis) == len(defined):
                all_disagree.append(dis[defined])

        seg = np.linalg.norm(
            np.diff(np.asarray(fib.coords, dtype=float), axis=0), axis=1
        )
        if len(seg):
            all_spacing.append(seg)

        # Secondary cut: does the field degrade away from the centreline? Inside
        # a fiber's cross-section the true tangent is the centreline's tangent.
        for o in offsets:
            if o == 0.0:
                if defined.any():
                    off_err[0.0].append(
                        angular_error_deg(tangents[defined], sampled[defined])
                    )
                continue
            pts, tgt = [], []
            for c, t in zip(coords, tangents, strict=False):
                for d in perpendicular_offsets(t, o):
                    pts.append(c + d)
                    tgt.append(t)
            if not pts:
                continue
            s2, d2 = sample_field(dirs, valid, np.asarray(pts))
            if d2.any():
                off_err[float(o)].append(angular_error_deg(np.asarray(tgt)[d2], s2[d2]))

    err = np.concatenate(all_err) if all_err else np.zeros(0)
    curv = np.concatenate(all_curv) if all_curv else np.zeros(0)
    spacing = np.concatenate(all_spacing) if all_spacing else np.zeros(0)
    disagree = np.concatenate(all_disagree) if all_disagree else np.zeros(0)

    return {
        "n_fibers": len(skeleton.fibers),
        "node_kinds": kind_counts,
        "n_scored": int(len(err)),
        "field_undefined_frac": (float(n_undefined / n_nodes) if n_nodes else 0.0),
        "error_deg": err,
        "curvature_deg": curv,
        "spacing": spacing,
        "estimator_disagreement_deg": disagree,
        "offset_error": {
            o: (float(np.median(np.concatenate(v))) if v else float("nan"))
            for o, v in off_err.items()
        },
        "frac_over_25": (float((err > 25.0).mean()) if len(err) else float("nan")),
    }
