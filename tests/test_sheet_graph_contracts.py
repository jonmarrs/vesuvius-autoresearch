"""Graph estimates must not fabricate solutions or lock in weaker paths."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import sheet_stitcher as stitcher

REPO = Path(__file__).resolve().parents[1]


def triangle():
    graph = stitcher.SheetGraph()
    for node in ("s", "a", "b"):
        graph.add_node(node)
    graph.add_edge("s", "b", weight=0.1, angle_delta=99)
    graph.add_edge("s", "a", weight=0.9, angle_delta=1)
    graph.add_edge("a", "b", weight=0.9, angle_delta=1)
    return graph


def test_maximum_product_path_can_replace_first_discovered_route():
    assert stitcher.assign_winding_angles_viterbi(triangle(), "s")["b"] == 2


def test_equal_priorities_do_not_compare_heterogeneous_node_ids():
    graph = stitcher.SheetGraph()
    for node in ("s", 1, "b"):
        graph.add_node(node)
    graph.add_edge("s", 1, angle_delta=1)
    graph.add_edge("s", "b", angle_delta=2)
    result = stitcher.assign_winding_angles_viterbi(graph, "s")
    assert result == {"s": 0, 1: 1, "b": 2}


def test_random_walk_does_not_invent_zero_for_unreachable_nodes():
    graph = stitcher.SheetGraph()
    graph.add_node("anchor")
    graph.add_node("unreachable")
    assert "unreachable" not in stitcher.assign_winding_angles_random_walk(
        graph, num_walks=2
    )


def test_missing_anchor_is_rejected():
    with pytest.raises(ValueError, match="start|anchor"):
        stitcher.assign_winding_angles_viterbi(triangle(), "not a node")


@pytest.mark.parametrize("weight", [-1, 2, float("nan"), float("inf")])
def test_invalid_confidence_is_rejected(weight):
    graph = stitcher.SheetGraph()
    graph.add_node("a")
    graph.add_node("b")
    with pytest.raises(ValueError, match="weight|confidence"):
        graph.add_edge("a", "b", weight=weight)


def test_undeclared_endpoint_is_rejected():
    graph = stitcher.SheetGraph()
    graph.add_node("a")
    with pytest.raises(ValueError, match="node|endpoint"):
        graph.add_edge("a", "missing")


def test_missing_cli_input_cannot_generate_dummy_results(tmp_path):
    output = tmp_path / "result"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/sheet_stitcher.py"),
            "--input_graph",
            str(tmp_path / "missing.json"),
            "--output",
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not output.exists()


def test_graph_cli_does_not_overwrite_existing_output(tmp_path):
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "angle_unit": "radians",
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [{"u": "a", "v": "b", "weight": 0.9, "angle_delta": 0.2}],
            }
        )
    )
    output = tmp_path / "existing.json"
    output.write_text("preserve")
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/sheet_stitcher.py"),
            "--input_graph",
            str(source),
            "--output",
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert output.read_text() == "preserve"


def test_legacy_solver_does_not_report_missing_prerequisite_as_success(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/autoresearch_thaumato_solver.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def source_graph(tmp_path, document=None):
    document = (
        document
        if document is not None
        else {
            "schema_version": 1,
            "angle_unit": "degrees",
            "nodes": [{"id": "a"}, {"id": "b"}, {"id": "unreachable"}],
            "edges": [{"u": "a", "v": "b", "weight": 0.9, "angle_delta": 20}],
        }
    )
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def bundle(tmp_path, **settings):
    output = stitcher.generate(source_graph(tmp_path), tmp_path / "output", **settings)
    return output, json.loads((output / "estimates.json").read_text())


def test_stronger_product_path_has_explicit_conflict_residual():
    report = stitcher.graph_report(triangle(), start_node="s")
    nodes = {row["id"]: row for row in report["nodes"]}
    assert nodes["b"]["angle"] == 2
    assert nodes["b"]["max_product_parent"] == "a"
    assert report["counts"]["violated_checked_edges"] == 1
    assert report["status"] == "inconsistent_reachable_constraints"
    residual = next(
        edge for edge in report["edges"] if {edge["u"], edge["v"]} == {"s", "b"}
    )
    assert abs(residual["residual"]) == 97
    assert "no physical stitching" in report["scope"]


def test_consistent_graph_respects_orientation_units_anchor_and_multiple_turns():
    graph = stitcher.SheetGraph(angle_unit="degrees")
    for node in ("a", "b", "c"):
        graph.add_node(node)
    graph.add_edge("b", "a", 0.9, -720)
    graph.add_edge("b", "c", 0.8, 20)
    graph.add_edge("a", "c", 0.1, 740)
    report = stitcher.graph_report(graph, start_node="b", start_angle=10)
    assert {row["id"]: row["angle"] for row in report["nodes"]} == {
        "a": -710,
        "b": 10,
        "c": 30,
    }
    assert report["angle_unit"] == "degrees"
    assert report["status"] == "consistent_relative_constraints"
    assert all(edge["within_tolerance"] for edge in report["edges"])


@pytest.mark.parametrize("algorithm", ["max_product", "random_walk"])
def test_zero_weight_does_not_connect_components_or_invent_angles(algorithm):
    graph = stitcher.SheetGraph()
    for node in ("a", "b", "c"):
        graph.add_node(node)
    graph.add_edge("a", "b", 0, 10)
    graph.add_edge("b", "c", 0.9, 20)
    report = stitcher.graph_report(graph, algorithm=algorithm, num_walks=2)
    rows = {row["id"]: row for row in report["nodes"]}
    assert rows["a"]["angle"] == 0
    assert rows["b"]["angle"] is rows["c"]["angle"] is None
    assert report["counts"]["unreachable_nodes"] == 2
    assert report["status"] == "partial_reachability"
    assert [edge["status"] for edge in report["edges"]] == [
        "zero_weight_disabled",
        "unreachable",
    ]


def test_source_copy_hash_and_typed_ids_are_preserved(tmp_path):
    import hashlib

    document = {
        "schema_version": 1,
        "angle_unit": "radians",
        "nodes": [{"id": 1}, {"id": "1"}],
        "edges": [{"u": 1, "v": "1", "weight": 1, "angle_delta": 0.25}],
    }
    source = source_graph(tmp_path, document)
    data = source.read_bytes()
    output = stitcher.generate(source, tmp_path / "output")
    report = json.loads((output / "estimates.json").read_text())
    assert [row["id"] for row in report["nodes"]] == [1, "1"]
    assert [row["angle"] for row in report["nodes"]] == [0, 0.25]
    assert (output / "source.json").read_bytes() == data
    assert report["source"]["sha256"] == hashlib.sha256(data).hexdigest()
    assert report["source"]["bytes"] == len(data)
    assert report["artifacts"]["source.json"]["sha256"] == report["source"]["sha256"]
    assert report["limits"]["max_walk_steps"] == 1_000_000
    assert source.read_bytes() == data


@pytest.mark.parametrize("algorithm", ["max_product", "random_walk"])
def test_node_and_edge_serialization_order_does_not_change_estimates(algorithm):
    graphs = []
    for reverse in (False, True):
        graph = stitcher.SheetGraph()
        nodes = ["s", "a", "b", 1]
        edges = [
            ("s", "a", 0.8, 1),
            ("s", "b", 0.8, 2),
            ("a", 1, 0.5, 3),
            ("b", 1, 0.5, 4),
        ]
        for node in nodes[::-1] if reverse else nodes:
            graph.add_node(node)
        for u, v, weight, delta in edges[::-1] if reverse else edges:
            graph.add_edge(
                v if reverse else u,
                u if reverse else v,
                weight,
                -delta if reverse else delta,
            )
        graphs.append(graph)
    reports = [
        stitcher.graph_report(
            graph,
            algorithm=algorithm,
            start_node="s",
            num_walks=5,
            walk_length=6,
            seed=9,
        )
        for graph in graphs
    ]
    assert reports[0] == reports[1]


def test_max_product_matches_exhaustive_simple_path_oracle():
    import math

    from scripts.sheet_graph import max_product_paths

    graph = stitcher.SheetGraph()
    for node in range(5):
        graph.add_node(node)
    edges = [
        (0, 1, 0.8, 1),
        (0, 2, 0.2, 9),
        (1, 2, 0.9, 1),
        (1, 3, 0.3, 5),
        (2, 3, 0.7, 1),
        (3, 4, 0.95, 2),
        (0, 4, 0.01, 99),
    ]
    adjacency = {node: [] for node in range(5)}
    for u, v, weight, delta in edges:
        graph.add_edge(u, v, weight, delta)
        adjacency[u].append((v, weight, delta))
        adjacency[v].append((u, weight, -delta))
    best = {node: (0, None) for node in range(5)}

    def enumerate_paths(node, visited, product, angle):
        if product > best[node][0]:
            best[node] = (product, angle)
        for neighbor, weight, delta in adjacency[node]:
            if neighbor not in visited:
                enumerate_paths(
                    neighbor, visited | {neighbor}, product * weight, angle + delta
                )

    enumerate_paths(0, {0}, 1, 0)
    _, angles, costs, _ = max_product_paths(graph, 0)
    for node, (product, angle) in best.items():
        assert costs[node] == pytest.approx(-math.log(product))
        assert angles[node] == angle


def test_long_weak_paths_keep_log_costs_without_product_underflow():
    from scripts.sheet_graph import max_product_paths

    graph = stitcher.SheetGraph()
    for node in range(10):
        graph.add_node(node)
    for node in range(9):
        graph.add_edge(node, node + 1, 1e-100, 1)
    _, angles, cost, _ = max_product_paths(graph)
    assert angles[9] == 9
    assert cost[9] > 2000


def test_walks_are_reproducible_without_mutating_global_rng():
    import numpy as np

    state = np.random.get_state()
    first = stitcher.graph_report(
        triangle(),
        algorithm="random_walk",
        start_node="s",
        num_walks=10,
        walk_length=6,
        seed=32,
    )
    second = stitcher.graph_report(
        triangle(),
        algorithm="random_walk",
        start_node="s",
        num_walks=10,
        walk_length=6,
        seed=32,
    )
    after = np.random.get_state()
    assert first == second
    assert state[0] == after[0] and state[2:] == after[2:]
    assert np.array_equal(state[1], after[1])
    assert first["anchor"] == {"id": "s", "angle": 0}
    assert any(row["sample_count"] for row in first["nodes"])
    assert "not uncertainty" in first["interpretation"]


def test_walk_fallback_is_explicit_for_reachable_unsampled_nodes():
    graph = stitcher.SheetGraph()
    for node in range(3):
        graph.add_node(node)
    graph.add_edge(0, 1, 1, 10)
    graph.add_edge(1, 2, 1, 20)
    report = stitcher.graph_report(
        graph, algorithm="random_walk", num_walks=1, walk_length=1
    )
    node = report["nodes"][2]
    assert node["angle"] == 30
    assert node["method"] == "max_product_fallback"
    assert node["sample_count"] == 0
    assert node["iqr"] is None


@pytest.mark.parametrize("algorithm", ["max_product", "random_walk"])
def test_unwrapped_angle_overflow_fails(algorithm):
    graph = stitcher.SheetGraph()
    for node in range(3):
        graph.add_node(node)
    graph.add_edge(0, 1, 1, 1e308)
    graph.add_edge(1, 2, 1, 1e308)
    with pytest.raises(ValueError, match="finite"):
        stitcher.graph_report(graph, algorithm=algorithm)


@pytest.mark.parametrize(
    "bad", [True, None, 1.0, [], {}, (), "", "  ", "x" * 257, 2**53]
)
def test_node_ids_are_strict_and_bounded(bad):
    with pytest.raises(ValueError, match="node id"):
        stitcher.SheetGraph().add_node(bad)


@pytest.mark.parametrize("field", ["weight", "angle_delta"])
@pytest.mark.parametrize("bad", [True, None, "0.5", [], float("nan"), float("inf")])
def test_edge_numbers_are_finite_real_values(field, bad):
    graph = stitcher.SheetGraph()
    graph.add_node("a")
    graph.add_node("b")
    with pytest.raises(ValueError, match=field):
        graph.add_edge("a", "b", **{field: bad})


def test_duplicate_self_and_parallel_constraints_are_rejected():
    graph = stitcher.SheetGraph()
    graph.add_node("a")
    graph.add_node("b")
    with pytest.raises(ValueError, match="duplicate node"):
        graph.add_node("a")
    with pytest.raises(ValueError, match="self"):
        graph.add_edge("a", "a")
    graph.add_edge("a", "b", 0.5, 1)
    with pytest.raises(ValueError, match="duplicate|parallel"):
        graph.add_edge("b", "a", 0.9, 9)
    assert len(graph.constraints) == 1


@pytest.mark.parametrize("unit", [None, [], "turns", 1])
def test_unknown_angle_units_are_rejected(unit):
    with pytest.raises(ValueError, match="angle_unit"):
        stitcher.SheetGraph(angle_unit=unit)


@pytest.mark.parametrize(
    "settings",
    [
        {"num_walks": 0},
        {"num_walks": True},
        {"num_walks": 10_001},
        {"walk_length": 0},
        {"walk_length": 1025},
        {"walk_length": 1.5},
        {"seed": -1},
        {"seed": 2**32},
        {"seed": True},
        {"seed": 1.5},
        {"num_walks": 10_000, "walk_length": 1024},
    ],
)
def test_walk_parameters_have_hard_budgets(settings):
    with pytest.raises(ValueError):
        stitcher.graph_report(triangle(), algorithm="random_walk", **settings)


def test_walk_step_budget_includes_every_requested_step(monkeypatch):
    from scripts import sheet_graph

    monkeypatch.setattr(sheet_graph, "MAX_WALK_STEPS", 12)
    stitcher.graph_report(
        triangle(), algorithm="random_walk", num_walks=3, walk_length=4
    )
    with pytest.raises(ValueError, match="total steps"):
        stitcher.graph_report(
            triangle(), algorithm="random_walk", num_walks=3, walk_length=5
        )


@pytest.mark.parametrize(
    "settings",
    [
        {"tolerance": -1},
        {"tolerance": True},
        {"tolerance": float("nan")},
        {"start_angle": float("inf")},
        {"start_angle": True},
        {"algorithm": "unknown"},
    ],
)
def test_estimation_settings_are_validated(settings):
    with pytest.raises(ValueError):
        stitcher.graph_report(triangle(), **settings)


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": True},
        {"schema_version": 2},
        {"angle_unit": []},
        {"nodes": []},
        {"nodes": {}},
        {"edges": {}},
        {"unexpected": 1},
        {"nodes": [{"id": True}]},
        {"nodes": [{"id": "a", "feature": 1}]},
        {"nodes": [{"id": "a"}, {"id": "a"}]},
        {"edges": [{"u": "a", "v": "b", "weight": 0.9}]},
        {"edges": [{"u": "a", "v": "missing", "weight": 0.9, "angle_delta": 1}]},
    ],
)
def test_json_schema_rejects_ambiguous_or_malformed_graphs(tmp_path, change):
    source = source_graph(tmp_path)
    document = json.loads(source.read_text())
    document.update(change)
    source.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        stitcher.generate(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "data",
    [
        b"not JSON",
        b"\xff",
        b"{}",
        b"[]",
        b'{"schema_version":1,"schema_version":1}',
        '{"schema_version": 1}'.encode("utf-16"),
        b"[" * 1200 + b"]" * 1200,
    ],
)
def test_json_parser_is_strict_utf8_and_rejects_duplicate_keys(data):
    with pytest.raises(ValueError):
        stitcher.parse_graph(data)


@pytest.mark.parametrize("limit", ["nodes", "edges"])
def test_graph_count_limits_precede_construction(tmp_path, monkeypatch, limit):
    if limit == "nodes":
        monkeypatch.setattr(stitcher, "MAX_NODES", 1)
    else:
        monkeypatch.setattr(stitcher, "MAX_EDGES", 0)
    with pytest.raises(ValueError, match=limit):
        stitcher.generate(source_graph(tmp_path), tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_source_byte_budget_precedes_json_decode(tmp_path, monkeypatch):
    source = source_graph(tmp_path)
    monkeypatch.setattr(stitcher, "MAX_SOURCE_BYTES", 8)
    monkeypatch.setattr(
        stitcher, "parse_graph", lambda *args: pytest.fail("oversized JSON decoded")
    )
    with pytest.raises(ValueError, match="bytes"):
        stitcher.generate(source, tmp_path / "output")


@pytest.mark.parametrize("kind", ["missing", "directory", "link", "pkl"])
def test_graph_source_is_a_regular_explicit_json_file(tmp_path, kind):
    source = tmp_path / ("source.pkl" if kind == "pkl" else "source.json")
    if kind == "directory":
        source.mkdir()
    elif kind == "link":
        source.symlink_to(source_graph(tmp_path))
    elif kind == "pkl":
        source.write_bytes(b"unsupported legacy pickle")
    with pytest.raises(ValueError):
        stitcher.generate(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_legacy_pkl_adapter_never_imports_or_deserializes(tmp_path, monkeypatch):
    import builtins

    original = builtins.__import__

    def guard(name, *args, **kwargs):
        if name.startswith("ThaumatoAnakalyptor") or name == "pickle":
            pytest.fail("legacy graph imported/deserialized")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    with pytest.raises(ValueError, match="unsupported"):
        stitcher.load_graph_from_pkl(tmp_path / "graph.pkl")


@pytest.mark.parametrize(
    "kind", ["directory", "file", "link", "broken_link", "source", "ancestor"]
)
def test_existing_and_aliased_outputs_are_preserved(tmp_path, kind):
    source = source_graph(tmp_path)
    before = source.read_bytes()
    output = tmp_path / "output"
    if kind == "directory":
        output.mkdir()
        (output / "marker").write_text("preserve")
    elif kind == "file":
        output.write_text("preserve")
    elif kind == "link":
        output.symlink_to(source)
    elif kind == "broken_link":
        output.symlink_to(tmp_path / "missing")
    elif kind == "source":
        output = source
    else:
        output = tmp_path
    with pytest.raises(ValueError, match="exists|overlap"):
        stitcher.generate(source, output)
    assert source.read_bytes() == before
    if kind == "directory":
        assert (output / "marker").read_text() == "preserve"
    elif kind == "file":
        assert output.read_text() == "preserve"
    elif kind in {"link", "broken_link"}:
        assert output.is_symlink()


def test_json_write_failure_rolls_back_complete_bundle(tmp_path, monkeypatch):
    source = source_graph(tmp_path)

    def fail(*args, **kwargs):
        raise OSError("injected write failure")

    monkeypatch.setattr(stitcher, "write_verified_json", fail)
    with pytest.raises(OSError, match="injected"):
        stitcher.generate(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()
    assert not list(tmp_path.glob(".output-*"))


def test_source_copy_readback_failure_rolls_back(tmp_path, monkeypatch):
    source = source_graph(tmp_path)
    original = Path.read_bytes

    def corrupt(path):
        if path.name == "source.json":
            return b"corrupt copy"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", corrupt)
    with pytest.raises(ValueError, match="copy verification"):
        stitcher.generate(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()
    assert not list(tmp_path.glob(".output-*"))


@pytest.mark.parametrize("keep_metadata", [False, True])
def test_changed_source_cannot_publish_old_estimates(
    tmp_path, monkeypatch, keep_metadata
):
    import os

    source = source_graph(tmp_path)
    before = source.stat()
    original = stitcher.write_verified_json

    def mutate(*args, **kwargs):
        original(*args, **kwargs)
        source.write_bytes(
            source.read_bytes().replace(b'"angle_delta": 20', b'"angle_delta": 30')
        )
        if keep_metadata:
            os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))

    monkeypatch.setattr(stitcher, "write_verified_json", mutate)
    with pytest.raises(ValueError, match="source changed"):
        stitcher.generate(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()
    assert not list(tmp_path.glob(".output-*"))


def test_source_signature_changes_during_capture_are_rejected(tmp_path, monkeypatch):
    source = source_graph(tmp_path)
    original = stitcher.signature
    calls = 0

    def change(path):
        nonlocal calls
        calls += 1
        info = original(path)
        return info if calls == 1 else {**info, "mtime_ns": info["mtime_ns"] + 1}

    monkeypatch.setattr(stitcher, "signature", change)
    with pytest.raises(ValueError, match="during capture"):
        stitcher.capture_graph(source)


def test_destination_appearing_during_processing_is_preserved(tmp_path, monkeypatch):
    source = source_graph(tmp_path)
    output = tmp_path / "output"
    original = stitcher.write_verified_json

    def appear(*args, **kwargs):
        original(*args, **kwargs)
        output.mkdir()
        (output / "marker").write_text("other writer")

    monkeypatch.setattr(stitcher, "write_verified_json", appear)
    with pytest.raises(ValueError, match="appeared"):
        stitcher.generate(source, output)
    assert (output / "marker").read_text() == "other writer"
    assert not (output / "estimates.json").exists()
    assert not list(tmp_path.glob(".output-*"))


def test_cli_runs_outside_checkout_and_names_partial_reachability(tmp_path):
    source = source_graph(tmp_path)
    output = tmp_path / "bundle"
    command = [
        sys.executable,
        str(REPO / "scripts/sheet_stitcher.py"),
        "--input-graph",
        str(source),
        "--out",
        str(output),
        "--start-node",
        '"a"',
        "--start-angle",
        "10",
    ]
    result = subprocess.run(command, cwd="/tmp", capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "partial_reachability" in result.stdout
    report = json.loads((output / "estimates.json").read_text())
    assert report["anchor"] == {"id": "a", "angle": 10}
    assert report["counts"]["reachable_nodes"] == 2
    assert report["nodes"][-1]["angle"] is None
    again = subprocess.run(command, cwd="/tmp", capture_output=True, text=True)
    assert again.returncode != 0 and "exists" in again.stderr


def test_cli_random_walk_records_only_applied_settings(tmp_path):
    source = source_graph(tmp_path)
    output = tmp_path / "bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/sheet_stitcher.py"),
            "--input-graph",
            str(source),
            "--out",
            str(output),
            "--algorithm",
            "random_walk",
            "--walks",
            "3",
            "--walk-length",
            "5",
            "--seed",
            "8",
        ],
        cwd="/tmp",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((output / "estimates.json").read_text())
    assert report["settings"] == {
        "algorithm": "random_walk",
        "num_walks": 3,
        "walk_length": 5,
        "seed": 8,
        "residual_tolerance": 1e-6,
    }


@pytest.mark.parametrize(
    "extra",
    [
        ["--start-node", "null"],
        ["--start-node", "true"],
        ["--start-node", "not_json"],
        ["--start-node", '"missing"'],
        ["--start-angle", "nan"],
        ["--tolerance", "-1"],
        ["--algorithm", "random_walk", "--walks", "0"],
        ["--algorithm", "random_walk", "--seed", "-1"],
        ["--seed", "8"],
        ["--walks", "0"],
    ],
)
def test_cli_invalid_settings_cannot_publish(tmp_path, extra):
    source = source_graph(tmp_path)
    output = tmp_path / "bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/sheet_stitcher.py"),
            "--input-graph",
            str(source),
            "--out",
            str(output),
            *extra,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not output.exists()


def test_cli_requires_input_and_does_not_run_demo(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/sheet_stitcher.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not list(tmp_path.iterdir())


def test_legacy_sweep_cannot_launch_producers_or_create_history(
    tmp_path, monkeypatch, capsys
):
    from scripts import autoresearch_thaumato_solver as legacy

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: pytest.fail("producer launched")
    )
    assert legacy.main([]) == 1
    assert "retired" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_viterbi_compatibility_name_records_actual_algorithm():
    report = stitcher.graph_report(triangle(), algorithm="viterbi")
    assert report["settings"]["algorithm"] == "max_product"


def test_low_median_and_iqr_are_finite_near_float_limit():
    graph = stitcher.SheetGraph()
    graph.add_node(0)
    graph.add_node(1)
    graph.add_edge(0, 1, 1, 1e308)
    report = stitcher.graph_report(
        graph, algorithm="random_walk", num_walks=2, walk_length=4
    )
    row = report["nodes"][1]
    assert row["angle"] == 1e308
    assert row["iqr"] == 0


def test_empty_graph_and_features_do_not_silently_produce_solution():
    graph = stitcher.SheetGraph()
    with pytest.raises(ValueError, match="nonempty"):
        stitcher.assign_winding_angles_viterbi(graph)
    with pytest.raises(ValueError, match="features"):
        graph.add_node("a", features={"anchor": 0})
