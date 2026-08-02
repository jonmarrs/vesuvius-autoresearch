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


def local_curvature_deg(fiber: Fiber) -> np.ndarray:
    """Turn angle in degrees at each node `gt_tangents` returns. NaN at endpoints.

    Computed from the fiber's **edge graph**, not from array order. NML node
    order is arbitrary -- edges on a real cube look like ``[[19, 17], [2, 19],
    [16, 2], ...]`` -- so comparing tangents at adjacent array positions would
    compare two essentially unrelated points and report meaningless curvature.

    Separates "the orientation field is noisy" from "the fiber genuinely bends
    more than the walker's turn limit". If real curvature routinely exceeded
    ``max_angle_deg``, that limit would simply be mis-set.

    The turn angle is computed via `angular_error_deg`, which folds mod 180 --
    an incoming/outgoing pair that reverses on itself (a genuine 180-degree
    hairpin) reads as ~0 degrees of turn here, the same as a straight line.
    That fold is defensible because it matches the walker's own sign-agnostic
    gate at `_direction_at` (an orientation is compared, not a direction), but
    it means this function cannot distinguish "straight" from "doubled back".
    Real hand-traced fibers essentially never do the latter, so it is not
    believed to affect these results, but it is not detected either.
    """
    coords = np.asarray(fiber.coords, dtype=float)
    adj = _adjacency(fiber)

    out: list[float] = []
    for i in range(len(coords)):
        nbrs = adj.get(i, [])
        if len(nbrs) == 0 or len(nbrs) >= 3:
            continue
        raw = _raw_tangent(coords, i, nbrs)
        if raw is None or float(np.linalg.norm(raw)) < 1e-9:
            continue
        if len(nbrs) == 1:
            out.append(float("nan"))  # endpoint: no turn defined
            continue
        incoming = coords[i] - coords[nbrs[0]]
        outgoing = coords[nbrs[1]] - coords[i]
        if min(float(np.linalg.norm(incoming)), float(np.linalg.norm(outgoing))) < 1e-9:
            out.append(float("nan"))
            continue
        out.append(float(angular_error_deg(incoming[None, :], outgoing[None, :])[0]))
    return np.asarray(out, dtype=float)


def _in_bounds(coords: np.ndarray, shape: tuple[int, int, int]) -> np.ndarray:
    """Which sampled node coordinates round to an in-bounds voxel index.

    Mirrors `sample_field`'s own in-bounds computation exactly (nearest-voxel
    index via `np.rint`, half-open range per axis), so that out-of-bounds-ness
    can be reported separately from `sample_field`'s `defined` mask without
    changing `sample_field`'s tested signature or behaviour. `sample_field`
    conflates "out of bounds" with "field says invalid" into one `defined`
    flag on purpose, because both mean "cannot be scored for angular error" --
    but that same union is the wrong thing to report as "the field is
    undefined", since out-of-bounds nodes are annotator overrun past the cube
    edge, not a property of the model.
    """
    coords = np.atleast_2d(np.asarray(coords, dtype=float))
    idx = np.rint(coords).astype(int)
    shape_arr = np.asarray(shape)
    inb = np.ones(len(idx), dtype=bool)
    for a in range(3):
        inb &= (idx[:, a] >= 0) & (idx[:, a] < shape_arr[a])
    return inb


def _scored_node_order(fiber: Fiber) -> list[int]:
    """Original node indices `gt_tangents` keeps, in the same order.

    `gt_tangents` iterates node index `i` from 0 to n-1 and keeps `i` under
    exactly this test (degree 1 or 2, non-degenerate raw tangent), appending
    in that order -- so this function's output is, index-for-index, which
    original node each row of `gt_tangents(fiber)[0]` (coords) came from. It is
    a separate function rather than a change to `gt_tangents`'s return type,
    since other code depends on that signature being stable. A test asserts
    the two stay in lockstep.
    """
    coords = np.asarray(fiber.coords, dtype=float)
    adj = _adjacency(fiber)
    idx: list[int] = []
    for i in range(len(coords)):
        nbrs = adj.get(i, [])
        if len(nbrs) == 0 or len(nbrs) >= 3:
            continue
        raw = _raw_tangent(coords, i, nbrs)
        if raw is None or float(np.linalg.norm(raw)) < 1e-9:
            continue
        idx.append(i)
    return idx


def _chains(fiber: Fiber) -> list[list[int]]:
    """Decompose a fiber's edge graph into maximal simple paths ("chains").

    A chain is a walk of node indices that starts and ends at a "special" node
    (degree != 2 -- an endpoint, a branch, or an isolated node) and passes only
    through degree-2 nodes in between, exactly as WebKnossos annotation order
    would visit them along one traced strand. Splitting at branch nodes (rather
    than, say, silently picking one arm) means a run-length measurement never
    treats two different arms of a Y as adjacent.

    Every edge appears in exactly one chain. A fiber with no special node at
    all (a pure cycle) is returned as one chain that starts and ends at the
    same node. Isolated nodes are returned as length-1 chains.
    """
    coords = np.asarray(fiber.coords, dtype=float)
    n = len(coords)
    adj = _adjacency(fiber)
    degree = {i: len(adj.get(i, [])) for i in range(n)}

    def edge_key(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    all_edges = {
        edge_key(int(a), int(b)) for a, b in np.asarray(fiber.edges, dtype=int)
    }
    visited: set[tuple[int, int]] = set()
    chains: list[list[int]] = []

    def walk_from(start: int, first: int) -> list[int]:
        chain = [start, first]
        visited.add(edge_key(start, first))
        prev, cur = start, first
        while degree.get(cur, 0) == 2:
            nxts = [x for x in adj[cur] if edge_key(cur, x) not in visited]
            if not nxts:
                break
            nxt = nxts[0]
            visited.add(edge_key(cur, nxt))
            chain.append(nxt)
            prev, cur = cur, nxt
        return chain

    specials = [i for i in range(n) if degree.get(i, 0) != 2]
    for s in specials:
        for nbr in adj.get(s, []):
            if edge_key(s, nbr) in visited:
                continue
            chains.append(walk_from(s, nbr))

    # Any edges not yet claimed belong to pure cycles (no special node at all).
    remaining = sorted(all_edges - visited)
    while remaining:
        a, b = remaining[0]
        chains.append(walk_from(a, b))
        remaining = sorted(all_edges - visited)

    for i in range(n):
        if degree.get(i, 0) == 0:
            chains.append([i])

    return chains


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


def _run_lengths(chain: list[int], over25_by_idx: dict[int, bool]) -> list[int]:
    """Lengths of maximal runs of consecutive over-25-degree nodes along one chain.

    "Consecutive" means chain-adjacent AND both scored -- a node with no error
    value (branch, out-of-bounds, or field-undefined) breaks a run rather than
    being silently skipped over, so a run reported here is genuinely a run of
    physically adjacent annotated nodes, not two distant bad nodes bridged by a
    gap.
    """
    runs: list[int] = []
    current = 0
    for idx in chain:
        flag = over25_by_idx.get(idx)
        if flag is True:
            current += 1
        else:
            if current > 0:
                runs.append(current)
            current = 0
    if current > 0:
        runs.append(current)
    return runs


def analyse_cube(
    skeleton,
    dirs: np.ndarray,
    valid: np.ndarray,
    shape: tuple[int, int, int],
    offsets: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0),
    prob: np.ndarray | None = None,
) -> dict:
    """Angular error of the orientation field against one cube's ground truth.

    `prob` is an optional semantic fiber-probability volume (e.g. the
    `fiber_hz_vt` output), sampled nearest-voxel at the same ground-truth node
    coordinates used for everything else. It plays no role in the angular-error
    measurement; it exists to characterise what the model was actually looking
    at where the *orientation* field (a downstream, Hessian-derived quantity)
    reports no direction -- see `prob_at_defined_nodes` /
    `prob_at_undefined_nodes`.

    Note on population alignment: `curvature_deg` and `estimator_disagreement_deg`
    are reported only at nodes where the field is `defined` (scored nodes),
    since they are meant to be read alongside `error_deg`, which is defined
    only there. `spacing` is **not** filtered this way -- it is every edge
    length in the fiber, regardless of whether the field is defined at either
    endpoint -- because node spacing is a property of the annotation, not of
    the field. Dividing a `curvature_deg` statistic by a `spacing` statistic
    therefore divides two different populations of nodes; see the report's
    degrees-per-voxel section for how that is handled.
    """
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
    all_edge_turn: list[np.ndarray] = []
    all_run_lengths: list[int] = []
    all_prob_defined: list[np.ndarray] = []
    all_prob_undefined: list[np.ndarray] = []
    n_nodes = 0
    n_oob = 0
    n_inbounds = 0
    n_undefined_inbounds = 0
    off_err: dict[float, list[np.ndarray]] = {float(o): [] for o in offsets}

    for fib in skeleton.fibers:
        for k, v in count_node_kinds(fib).items():
            kind_counts[k] += v

        coords, tangents, kinds = gt_tangents(fib)
        if len(coords) == 0:
            continue

        inb = _in_bounds(coords, shape)
        sampled, defined = sample_field(dirs, valid, coords)
        n_nodes += len(coords)
        n_oob += int((~inb).sum())
        n_inbounds += int(inb.sum())
        # `defined` is False both out-of-bounds and where the field itself says
        # invalid; restricting to `inb` isolates the latter, which is the only
        # one that is a fact about the model rather than about the annotation.
        n_undefined_inbounds += int((inb & ~defined).sum())

        per_node_err = np.full(len(coords), np.nan)
        if defined.any():
            e = angular_error_deg(tangents[defined], sampled[defined])
            per_node_err[defined] = e
            all_err.append(e)
            curv = local_curvature_deg(fib)
            assert len(curv) == len(defined), (
                "local_curvature_deg must return one entry per gt_tangents node"
            )
            all_curv.append(curv[defined])
            dis = tangent_estimator_disagreement(fib)
            assert len(dis) == len(defined), (
                "tangent_estimator_disagreement must return one entry per "
                "gt_tangents node"
            )
            all_disagree.append(dis[defined])

        if prob is not None:
            idx = np.rint(coords).astype(int)
            if defined.any():
                sel = idx[defined]
                all_prob_defined.append(prob[sel[:, 0], sel[:, 1], sel[:, 2]])
            undef_inb = inb & ~defined
            if undef_inb.any():
                sel = idx[undef_inb]
                all_prob_undefined.append(prob[sel[:, 0], sel[:, 1], sel[:, 2]])

        # Run-length of consecutive over-25-degree nodes along the annotation
        # chain -- the question is whether bad nodes are isolated (as the
        # per-node rate alone would suggest under independence) or clustered.
        node_order = _scored_node_order(fib)
        over25_by_idx = {
            node_order[i]: bool(per_node_err[i] > 25.0)
            for i in range(len(coords))
            if defined[i]
        }
        for chain in _chains(fib):
            all_run_lengths.extend(_run_lengths(chain, over25_by_idx))

        # Field-self-consistency: the turn the *field itself* makes between two
        # adjacent ground-truth nodes, i.e. what actually gates the walker's
        # tangent-window comparison (mean of recent field directions), unlike
        # error_deg, which the walker never computes -- it has no access to
        # ground truth. Uses every edge in the fiber, not only scored nodes,
        # since branch/endpoint nodes still carry a field sample.
        if len(fib.edges):
            a_idx = np.asarray(fib.edges, dtype=int)[:, 0]
            b_idx = np.asarray(fib.edges, dtype=int)[:, 1]
            a_coords = np.asarray(fib.coords, dtype=float)[a_idx]
            b_coords = np.asarray(fib.coords, dtype=float)[b_idx]
            sa, da = sample_field(dirs, valid, a_coords)
            sb, db = sample_field(dirs, valid, b_coords)
            ok = da & db
            if ok.any():
                all_edge_turn.append(angular_error_deg(sa[ok], sb[ok]))

        # Edge lengths, not consecutive-row differences: NML node order is
        # arbitrary, so diffing the coords array measures nothing.
        seg = fib.segment_lengths()
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
    edge_turn = np.concatenate(all_edge_turn) if all_edge_turn else np.zeros(0)
    prob_defined = np.concatenate(all_prob_defined) if all_prob_defined else np.zeros(0)
    prob_undefined = (
        np.concatenate(all_prob_undefined) if all_prob_undefined else np.zeros(0)
    )

    frac_over_25 = float((err > 25.0).mean()) if len(err) else float("nan")
    run_lengths = np.asarray(all_run_lengths, dtype=float)
    independent_run_prediction = (
        float(1.0 / (1.0 - frac_over_25))
        if len(err) and frac_over_25 < 1.0
        else float("nan")
    )

    return {
        "n_fibers": len(skeleton.fibers),
        "node_kinds": kind_counts,
        "n_scored": int(len(err)),
        # Fraction of ALL ground-truth nodes (in- and out-of-bounds) that lie
        # outside the cube -- a fact about the annotation, not the model.
        "oob_frac": (float(n_oob / n_nodes) if n_nodes else 0.0),
        # Fraction of IN-BOUNDS nodes where the field itself is invalid -- the
        # only one of the two that is a fact about the model.
        "field_undefined_frac": (
            float(n_undefined_inbounds / n_inbounds) if n_inbounds else 0.0
        ),
        "error_deg": err,
        "curvature_deg": curv,
        "spacing": spacing,
        "estimator_disagreement_deg": disagree,
        "field_self_consistency_deg": edge_turn,
        "field_self_consistency_frac_over_25": (
            float((edge_turn > 25.0).mean()) if len(edge_turn) else float("nan")
        ),
        "run_lengths": run_lengths,
        "mean_run_length": (
            float(run_lengths.mean()) if len(run_lengths) else float("nan")
        ),
        "frac_runs_ge_2": (
            float((run_lengths >= 2).mean()) if len(run_lengths) else float("nan")
        ),
        "max_run_length": (
            float(run_lengths.max()) if len(run_lengths) else float("nan")
        ),
        "independent_run_length_prediction": independent_run_prediction,
        "prob_at_defined_nodes": prob_defined,
        "prob_at_undefined_nodes": prob_undefined,
        "offset_error": {
            o: (float(np.median(np.concatenate(v))) if v else float("nan"))
            for o, v in off_err.items()
        },
        "frac_over_25": frac_over_25,
    }
