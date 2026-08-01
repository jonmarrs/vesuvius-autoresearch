"""Characterise the orientation field against hand-traced ground truth.

Every walker-level fix attempted on this tracer -- tangent smoothing, bounded
coasting, seed non-maximum suppression -- assumed the orientation field is
accurate enough to follow. That assumption was never measured. This module
measures it: the angle between the Hessian tangent and the true fiber tangent,
at ground-truth nodes.

Read-only by construction. Nothing here changes tracer behaviour.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from .skeleton_io import Fiber


class NodeKind:
    """Why a ground-truth node was used or excluded."""

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
    """Unnormalised tangent at node i, or None if it has no well-defined one.

    Interior nodes use a central difference between their two neighbours, which
    bisects the two edges. Using one edge instead would bias every tangent
    toward whichever neighbour happened to be listed first.
    """
    if len(nbrs) == 1:
        return coords[nbrs[0]] - coords[i]
    if len(nbrs) == 2:
        return coords[nbrs[1]] - coords[nbrs[0]]
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
