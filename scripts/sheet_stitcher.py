#!/usr/bin/env python3
"""Publish relative-angle diagnostics from a bounded, explicit JSON graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.data_catalogue import (
    artifact_record,
    default_output,
    signature,
    write_verified_json,
)
from scripts.labeling.label_artifacts import new_output, publish_new
from scripts.sheet_graph import (
    MAX_EDGES,
    MAX_NODES,
    SheetGraph,
    assign_winding_angles_random_walk,
    assign_winding_angles_viterbi,
    graph_report,
)

MAX_SOURCE_BYTES = 16 * 1024**2


def load_graph_from_pkl(pkl_path):
    raise ValueError(
        "legacy Thaumato PKL adapter is unsupported: upstream edge variants, certainty "
        "factors and sheet_offset_k are not this JSON graph's confidence/angle contract; "
        "supply an explicitly converted JSON graph with declared units"
    )


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_graph(data):
    try:
        document = json.loads(
            data.decode("utf-8") if isinstance(data, bytes) else data,
            object_pairs_hook=unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("expected bounded UTF-8 graph JSON") from exc
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "angle_unit",
        "nodes",
        "edges",
    }:
        raise ValueError(
            "graph must contain only schema_version, angle_unit, nodes and edges"
        )
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("graph schema_version must be integer 1")
    nodes, edges = document["nodes"], document["edges"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise ValueError(f"graph must contain 1..{MAX_NODES} nodes")
    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        raise ValueError(f"graph must contain at most {MAX_EDGES} edges")
    graph = SheetGraph(angle_unit=document["angle_unit"])
    for record in nodes:
        if not isinstance(record, dict) or set(record) != {"id"}:
            raise ValueError("each node must contain only id")
        graph.add_node(record["id"])
    for record in edges:
        if not isinstance(record, dict) or set(record) != {
            "u",
            "v",
            "weight",
            "angle_delta",
        }:
            raise ValueError("each edge must contain u, v, weight and angle_delta")
        graph.add_edge(**record)
    return graph


def capture_graph(path):
    path = Path(path)
    if path.suffix.lower() != ".json":
        raise ValueError(
            "only explicit JSON graphs are supported; PKL/bin inference is retired"
        )
    before = signature(path)
    if before is None or not stat.S_ISREG(before["mode"]):
        raise ValueError("graph source must be a regular file, not a symlink")
    if before["bytes"] > MAX_SOURCE_BYTES:
        raise ValueError(f"graph source exceeds {MAX_SOURCE_BYTES} bytes")
    with path.open("rb") as stream:
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES or signature(path) != before:
        raise ValueError("graph source changed or exceeded byte budget during capture")
    graph = parse_graph(data)
    return (
        graph,
        data,
        {
            "path": str(path.resolve()),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "signature": before,
        },
    )


def generate(input_graph, output=None, **settings):
    source = Path(input_graph)
    output = new_output(
        output if output is not None else default_output("sheet_graph"), source
    )
    graph, data, identity = capture_graph(source)
    report = graph_report(graph, **settings)
    report["source"] = identity
    report["limits"]["max_source_bytes"] = MAX_SOURCE_BYTES
    with publish_new(output) as staging:
        copied = staging / "source.json"
        copied.write_bytes(data)
        if copied.read_bytes() != data:
            raise ValueError("graph source copy verification failed")
        report["artifacts"] = {"source.json": artifact_record(copied)}
        write_verified_json(staging / "estimates.json", report)
        _, current, current_identity = capture_graph(source)
        if current != data or current_identity != identity:
            raise ValueError("graph source changed before publication")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input_graph",
        "--input-graph",
        type=Path,
        required=True,
        help="schema 1 JSON graph with explicit angle_unit",
    )
    parser.add_argument(
        "--output", "--out", type=Path, help="new, separate bundle directory"
    )
    parser.add_argument(
        "--algorithm",
        choices=["max_product", "viterbi", "random_walk"],
        default="max_product",
    )
    parser.add_argument("--start-node", help="JSON node id, e.g. 7 or '\"anchor\"'")
    parser.add_argument("--start-angle", type=float, default=0.0)
    parser.add_argument("--walks", type=int, help="random_walk only; default 2000")
    parser.add_argument("--walk-length", type=int, help="random_walk only; default 20")
    parser.add_argument("--seed", type=int, help="random_walk only; default 0")
    parser.add_argument("--tolerance", type=float, default=1e-6)
    args = parser.parse_args(argv)
    try:
        start = json.loads(args.start_node) if args.start_node is not None else None
        if args.start_node is not None and start is None:
            raise ValueError("start/anchor node cannot be null")
        if args.algorithm != "random_walk" and any(
            value is not None for value in (args.walks, args.walk_length, args.seed)
        ):
            raise ValueError("walk/seed options require --algorithm random_walk")
        output = generate(
            args.input_graph,
            args.output,
            algorithm=args.algorithm,
            start_node=start,
            start_angle=args.start_angle,
            num_walks=args.walks if args.walks is not None else 2000,
            walk_length=args.walk_length if args.walk_length is not None else 20,
            seed=args.seed if args.seed is not None else 0,
            tolerance=args.tolerance,
        )
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(f"Graph diagnostic failed: {exc}", file=sys.stderr)
        return 1
    report = json.loads((output / "estimates.json").read_text(encoding="utf-8"))
    print(
        f"Graph diagnostic: {report['status']}; {report['counts']}; saved to {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
