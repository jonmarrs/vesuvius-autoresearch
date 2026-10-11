"""Bounded relative-angle diagnostics for an explicit undirected sheet graph."""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np

from scripts.data_catalogue import bounded_integer

MAX_NODES = 4096
MAX_EDGES = 16384
MAX_WALKS = 10_000
MAX_WALK_LENGTH = 1024
MAX_WALK_STEPS = 1_000_000


def node_id(value):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError("node id must be a string or integer, not boolean")
    if isinstance(value, Integral):
        result = int(value)
        if abs(result) <= 2**53 - 1:
            return result
    elif isinstance(value, str) and value.strip() and len(value) <= 256:
        return value
    raise ValueError(
        "node id must be a nonempty string <=256 characters or a JSON-safe integer"
    )


def node_key(value):
    return (0, value) if isinstance(value, int) else (1, value)


def finite_number(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite real number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite real number")
    return result


def seed_number(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise ValueError("seed must be an integer in [0, 2**32-1]")
    result = int(value)
    if not 0 <= result <= 2**32 - 1:
        raise ValueError("seed must be an integer in [0, 2**32-1]")
    return result


@dataclass(frozen=True)
class Constraint:
    u: int | str
    v: int | str
    weight: float
    angle_delta: float


class SheetGraph:
    """Simple graph: angle_delta means f(v)-f(u), with no modulo operation."""

    def __init__(self, *, angle_unit="radians"):
        if not isinstance(angle_unit, str) or angle_unit not in {"radians", "degrees"}:
            raise ValueError("angle_unit must be radians or degrees")
        self.angle_unit = angle_unit
        self._nodes = set()
        self._constraints = []
        self._pairs = set()

    @property
    def nodes(self):
        return frozenset(self._nodes)

    @property
    def constraints(self):
        return tuple(self._constraints)

    def add_node(self, node_id_value, features=None):
        node = node_id(node_id_value)
        if features is not None:
            raise ValueError(
                "node features are unsupported by this relative-angle diagnostic"
            )
        if node in self._nodes:
            raise ValueError(f"duplicate node id: {node!r}")
        if len(self._nodes) >= MAX_NODES:
            raise ValueError(f"graph exceeds {MAX_NODES} nodes")
        self._nodes.add(node)

    def add_edge(self, u, v, weight=1.0, angle_delta=0.0):
        u, v = node_id(u), node_id(v)
        if u not in self._nodes or v not in self._nodes:
            raise ValueError("edge endpoints must be declared nodes")
        if u == v:
            raise ValueError("self edges are unsupported")
        weight = finite_number(weight, "weight")
        if not 0 <= weight <= 1:
            raise ValueError("weight must be a confidence factor in [0, 1]")
        delta = finite_number(angle_delta, "angle_delta")
        if node_key(v) < node_key(u):
            u, v, delta = v, u, -delta
        pair = (u, v)
        if pair in self._pairs:
            raise ValueError("duplicate or parallel edge endpoints")
        if len(self._constraints) >= MAX_EDGES:
            raise ValueError(f"graph exceeds {MAX_EDGES} edges")
        self._pairs.add(pair)
        self._constraints.append(Constraint(u, v, weight, delta))

    def adjacency(self):
        result = {node: [] for node in sorted(self._nodes, key=node_key)}
        for edge in self._constraints:
            if edge.weight > 0:
                result[edge.u].append((edge.v, edge.weight, edge.angle_delta))
                result[edge.v].append((edge.u, edge.weight, -edge.angle_delta))
        return {
            node: tuple(sorted(edges, key=lambda edge: node_key(edge[0])))
            for node, edges in result.items()
        }


def anchor_node(graph, start_node=None):
    if not isinstance(graph, SheetGraph) or not graph.nodes:
        raise ValueError("expected a nonempty SheetGraph")
    anchor = (
        min(graph.nodes, key=node_key) if start_node is None else node_id(start_node)
    )
    if anchor not in graph.nodes:
        raise ValueError("start/anchor node must be declared in the graph")
    return anchor


def max_product_paths(graph, start_node=None, *, start_angle=0.0):
    """Dijkstra on -log(weight); finalized nodes have the strongest product path."""
    anchor = anchor_node(graph, start_node)
    start_angle = finite_number(start_angle, "start_angle")
    adjacency = graph.adjacency()
    ranks = {node: index for index, node in enumerate(adjacency)}
    distance = {anchor: 0.0}
    angles = {anchor: start_angle}
    parents = {anchor: None}
    settled = set()
    queue = [(0.0, ranks[anchor], anchor)]
    while queue:
        cost, _, u = heapq.heappop(queue)
        if u in settled or cost != distance[u]:
            continue
        settled.add(u)
        for v, weight, delta in adjacency[u]:
            if v in settled:
                continue
            candidate = cost - math.log(weight)
            if v not in distance or candidate < distance[v]:
                angle = finite_number(angles[u] + delta, "accumulated angle")
                distance[v], angles[v], parents[v] = candidate, angle, u
                heapq.heappush(queue, (candidate, ranks[v], v))
    return anchor, angles, distance, parents


def assign_winding_angles_viterbi(graph, start_node=None):
    """Compatibility name for a maximum-product-path diagnostic, not Viterbi."""
    return max_product_paths(graph, start_node)[1]


def random_walk_estimates(
    graph, num_walks=2000, *, start_node=None, start_angle=0.0, walk_length=20, seed=0
):
    count = bounded_integer(num_walks, "num_walks", MAX_WALKS)
    length = bounded_integer(walk_length, "walk_length", MAX_WALK_LENGTH)
    if count * length > MAX_WALK_STEPS:
        raise ValueError(f"random walks exceed {MAX_WALK_STEPS} total steps")
    seed = seed_number(seed)
    anchor, fallback, distance, parents = max_product_paths(
        graph, start_node, start_angle=start_angle
    )
    adjacency = graph.adjacency()
    probabilities = {}
    for node, neighbors in adjacency.items():
        if neighbors:
            weights = np.asarray([edge[1] for edge in neighbors], dtype=np.float64)
            weights /= weights.max()
            probabilities[node] = weights / weights.sum()
    rng = np.random.default_rng(seed)
    samples = defaultdict(list)
    for _ in range(count):
        current, angle = anchor, fallback[anchor]
        for _ in range(length):
            neighbors = adjacency[current]
            if not neighbors:
                break
            index = int(rng.choice(len(neighbors), p=probabilities[current]))
            current, _, delta = neighbors[index]
            angle = finite_number(angle + delta, "random-walk accumulated angle")
            # The declared reference stays fixed, even for inconsistent cycles.
            if current == anchor:
                angle = fallback[anchor]
            else:
                samples[current].append(angle)
    estimates, diagnostics = {}, {}
    for node in sorted(fallback, key=node_key):
        values = samples[node]
        if node == anchor:
            estimates[node] = fallback[node]
            diagnostics[node] = {
                "method": "fixed_anchor",
                "sample_count": 0,
                "iqr": None,
            }
        elif values:
            data = np.asarray(values, dtype=np.float64)
            # Lower order statistics avoid overflow in averaged medians/quantiles.
            ordered = np.sort(data)
            estimate = float(ordered[(len(ordered) - 1) // 2])
            spread = finite_number(
                float(ordered[(3 * (len(ordered) - 1)) // 4])
                - float(ordered[(len(ordered) - 1) // 4]),
                "random-walk sample IQR",
            )
            estimates[node] = estimate
            diagnostics[node] = {
                "method": "walk_lower_median",
                "sample_count": len(values),
                "iqr": spread,
            }
        else:
            estimates[node] = fallback[node]
            diagnostics[node] = {
                "method": "max_product_fallback",
                "sample_count": 0,
                "iqr": None,
            }
    return anchor, estimates, distance, parents, diagnostics


def assign_winding_angles_random_walk(graph, num_walks=2000, **kwargs):
    """Seeded, bounded exploratory walk estimates; unreachable nodes are omitted."""
    return random_walk_estimates(graph, num_walks, **kwargs)[1]


def graph_report(
    graph,
    *,
    algorithm="max_product",
    start_node=None,
    start_angle=0.0,
    num_walks=2000,
    walk_length=20,
    seed=0,
    tolerance=1e-6,
):
    tolerance = finite_number(tolerance, "tolerance")
    if tolerance < 0:
        raise ValueError("tolerance must be nonnegative")
    if algorithm == "viterbi":
        algorithm = "max_product"
    if algorithm == "max_product":
        anchor, angles, distance, parents = max_product_paths(
            graph, start_node, start_angle=start_angle
        )
        methods = {
            node: {"method": "max_product_path", "sample_count": None, "iqr": None}
            for node in angles
        }
        settings = {"algorithm": algorithm}
    elif algorithm == "random_walk":
        anchor, angles, distance, parents, methods = random_walk_estimates(
            graph,
            num_walks,
            start_node=start_node,
            start_angle=start_angle,
            walk_length=walk_length,
            seed=seed,
        )
        settings = {
            "algorithm": algorithm,
            "num_walks": int(num_walks),
            "walk_length": int(walk_length),
            "seed": seed_number(seed),
        }
    else:
        raise ValueError("unknown graph algorithm")
    residuals = []
    for edge in sorted(
        graph.constraints, key=lambda item: (node_key(item.u), node_key(item.v))
    ):
        eligible = edge.weight > 0 and edge.u in angles and edge.v in angles
        residual = (
            finite_number(
                angles[edge.v] - angles[edge.u] - edge.angle_delta, "edge residual"
            )
            if eligible
            else None
        )
        residuals.append(
            {
                "u": edge.u,
                "v": edge.v,
                "weight": edge.weight,
                "angle_delta": edge.angle_delta,
                "status": "checked"
                if eligible
                else "zero_weight_disabled"
                if edge.weight == 0
                else "unreachable",
                "residual": residual,
                "within_tolerance": abs(residual) <= tolerance
                if residual is not None
                else None,
            }
        )
    violated = sum(item["within_tolerance"] is False for item in residuals)
    return {
        "contract": 1,
        "limits": {
            "max_nodes": MAX_NODES,
            "max_edges": MAX_EDGES,
            "max_walks": MAX_WALKS,
            "max_walk_length": MAX_WALK_LENGTH,
            "max_walk_steps": MAX_WALK_STEPS,
        },
        "scope": "relative graph-angle diagnostic; no physical stitching, "
        "ground truth, CT registration or prize eligibility assessed",
        "angle_unit": graph.angle_unit,
        "anchor": {"id": anchor, "angle": angles[anchor]},
        "settings": {**settings, "residual_tolerance": tolerance},
        "counts": {
            "nodes": len(graph.nodes),
            "edges": len(graph.constraints),
            "reachable_nodes": len(angles),
            "unreachable_nodes": len(graph.nodes) - len(angles),
            "violated_checked_edges": violated,
            "checked_edges": sum(item["status"] == "checked" for item in residuals),
            "zero_weight_edges": sum(
                item["status"] == "zero_weight_disabled" for item in residuals
            ),
            "unreachable_edges": sum(
                item["status"] == "unreachable" for item in residuals
            ),
        },
        "status": "inconsistent_reachable_constraints"
        if violated
        else "partial_reachability"
        if len(angles) < len(graph.nodes)
        else "consistent_relative_constraints",
        "nodes": [
            {
                "id": node,
                "status": "estimated" if node in angles else "unreachable",
                "angle": angles.get(node),
                "max_product_path_cost": distance.get(node),
                "max_product_parent": parents.get(node),
                **methods.get(
                    node, {"method": None, "sample_count": None, "iqr": None}
                ),
            }
            for node in sorted(graph.nodes, key=node_key)
        ],
        "edges": residuals,
        "interpretation": "Path confidence factors are not calibrated probabilities. "
        "Walk visits are correlated; sample IQR is descriptive, not uncertainty. "
        "Inconsistent cycles can bias walk estimates; no outlier-rejection guarantee.",
    }
