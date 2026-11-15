"""The candidate successor uses measured precision without changing Finding 111."""

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "repro/first_letters/pherc0841"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v2 = _load("surface_control_v2")


def _segment(name="a", last_positive=24749.5):
    # Actual pair ranks: 5000 positives, 45000 negatives, AUC 0.74996.
    scores = np.concatenate([np.full(4999, 33749.5), [last_positive], np.arange(45000)])
    ink = np.concatenate([np.ones(5000, bool), np.zeros(45000, bool)])
    order = np.random.default_rng(0).permutation(scores.size)
    scores, ink = scores[order].reshape(200, 250), ink[order].reshape(200, 250)
    ok = np.ones(scores.shape, bool)
    return SimpleNamespace(
        name=name,
        render=Path(f"{name}_66.zarr"),
        render_ok=ok,
        scored=ok,
        ink=ink,
        scorable=lambda: True,
        counts=lambda: {"ink_cells": 5000, "bare_cells": 45000},
        score_map=lambda *args: scores,
        auc=lambda *args: v2.auc(scores[ok], ink[ok]),
    )


GATE = {
    f"{step}_{name}": {"exit": 0} for step in ("render", "ink") for name in ("a", "b")
}


def test_actual_ranks_below_p2_stay_below_after_reading_and_json_roundtrip():
    reading = v2.held_out_reading(_segment(), 0, "reverse")
    assert reading["auc"] == 0.74996
    assert reading["slid_floor"]["largest"] != round(
        reading["slid_floor"]["largest"], 4
    )
    assert reading["p1"] is True and reading["p2"] is False
    restored = json.loads(json.dumps(reading, allow_nan=False))
    assert (
        v2.verdict(GATE, {"a": restored, "b": restored})["verdict"]
        == "BLOB_LEVEL_SIGNAL"
    )


def test_historical_boundary_behavior_is_preserved_but_not_used_by_v2():
    path = sys.path[:]
    try:
        original = _load("surface_control")
    finally:
        sys.path[:] = path
    old = original.held_out_reading(_segment(), 0, "reverse")
    assert old["auc"] == 0.75 and old["p2"] is True
    assert (
        original.verdict(GATE, {"a": old, "b": old})["verdict"] == "LETTER_LEVEL_SIGNAL"
    )
    new = v2.held_out_reading(_segment(), 0, "reverse")
    assert v2.verdict(GATE, {"a": new, "b": new})["verdict"] == "BLOB_LEVEL_SIGNAL"


@pytest.mark.parametrize(
    "value, floor, p1, p2",
    [
        (0.59996, 0.5, False, False),
        (0.6, 0.5, True, False),
        (0.64996, 0.6, False, False),
        (0.65004, 0.600049, False, False),
        (0.650049, 0.60004, True, False),
        (0.74996, 0.5, True, False),
        (np.nextafter(0.75, 0.0).item(), 0.5, True, False),
        (0.75, 0.5, True, True),
        (0.8, None, False, True),
        (None, 0.5, False, False),
    ],
)
def test_decisions_use_full_precision_on_both_sides_of_each_boundary(
    value, floor, p1, p2
):
    row = {"auc": value, "slid_floor": {"largest": floor}}
    assert v2.p1_holds(row) is p1
    assert v2.p2_holds(row) is p2


def test_sweep_compares_actual_ranks_before_applying_tiebreakers():
    near, far = _segment(), _segment(last_positive=29249.5)
    lower, higher = near.auc(), far.auc()
    assert lower == 0.74996 and higher == 0.74998
    assert round(lower, 4) == round(higher, 4)
    assert v2.choose(
        [
            {"depth": 0, "side": "reverse", "auc": lower},
            {"depth": 5, "side": "forward", "auc": higher},
        ]
    ) == {"depth": 5, "side": "forward", "auc": higher}


def test_genuine_sweep_ties_retain_the_old_tiebreakers():
    table = [
        {"depth": 3, "side": "reverse", "auc": 0.7},
        {"depth": 1, "side": "forward", "auc": 0.7},
        {"depth": 1, "side": "reverse", "auc": 0.7},
    ]
    assert v2.choose(table) == table[-1]
    assert v2.choose([{**table[0], "auc": None}]) is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1, True, "0.8"])
def test_invalid_metrics_cannot_become_decisions_or_choices(value):
    row = {"auc": value, "slid_floor": {"largest": 0.5}}
    for operation in (v2.p1_holds, v2.p2_holds):
        with pytest.raises(ValueError, match="AUC"):
            operation(row)
    with pytest.raises(ValueError, match="AUC"):
        v2.choose([{"depth": 0, "side": "reverse", "auc": value}])


def test_verdict_recomputes_flags_and_failed_steps_decide_before_metrics():
    row = {"auc": 0.74996, "slid_floor": {"largest": 0.5}, "p1": False, "p2": True}
    assert v2.verdict(GATE, {"a": row, "b": row}) == {
        "verdict": "BLOB_LEVEL_SIGNAL",
        "p1": {"a": True, "b": True},
        "p2": {"a": False, "b": False},
    }
    for status in (None, False, "0", 1):
        failed = {**GATE, "ink_a": {"exit": status}}
        assert v2.verdict(failed, {"a": {}}) == {
            "verdict": "DOES_NOT_RUN",
            "failed_steps": ["ink_a"],
        }


def _confirm_args(out, choice, gate, names=("a", "b")):
    args = ["confirm", str(out), "--choice", str(choice), "--gate", str(gate)]
    for name in names:
        args += ["--segment", name, "mesh", "maps", f"{name}_66.zarr", "labels"]
    return args


def _choice(path):
    row = {"depth": 0, "side": "reverse", "auc": 0.74996}
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "protocol": v2.PROTOCOL,
                "table": [row],
                "chosen": row,
            }
        )
    )
    return path


def test_sweep_and_confirmation_keep_raw_metrics_and_bind_the_captured_choice(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(v2, "_segment", lambda values: _segment(values[0]))
    choice = tmp_path / "sweep.json"
    assert (
        v2.main(
            [
                "sweep",
                str(choice),
                "--segment",
                "dev",
                "mesh",
                "maps",
                "dev_66.zarr",
                "labels",
                "--depths",
                "0",
                "0",
            ]
        )
        == 0
    )
    sweep = json.loads(choice.read_bytes())
    assert all(row["auc"] == 0.74996 for row in sweep["table"])
    assert sweep["chosen"]["auc"] == 0.74996
    assert "0 reverse 0.7500" in capsys.readouterr().out
    choice_bytes = choice.read_bytes()
    gate = tmp_path / "gate"
    gate.mkdir()
    for name, step in GATE.items():
        (gate / f"{name}.json").write_text(json.dumps(step))
    out = tmp_path / "confirm.json"
    assert v2.main(_confirm_args(out, choice, gate)) == 0
    record = json.loads(out.read_bytes())
    assert record["protocol"] == v2.PROTOCOL
    assert record["choice_sha256"] == hashlib.sha256(choice_bytes).hexdigest()
    assert record["held_out"]["a"]["auc"] == 0.74996
    assert record["verdict"] == "BLOB_LEVEL_SIGNAL"
    with pytest.raises(SystemExit, match="exists: this is measured once"):
        v2.main(_confirm_args(out, choice, gate))


@pytest.mark.parametrize(
    "invalid", ["historical", "precision", "choice", "duplicate", "nonfinite"]
)
def test_incompatible_or_corrupt_sweeps_fail_before_loading_inputs(
    tmp_path, monkeypatch, invalid
):
    path = _choice(tmp_path / "sweep.json")
    sweep = json.loads(path.read_bytes())
    if invalid == "historical":
        del sweep["protocol"]
        del sweep["schema_version"]
    elif invalid == "precision":
        sweep["protocol"]["auc_precision"] = "rounded-four-decimals"
    elif invalid == "choice":
        sweep["chosen"] = {**sweep["chosen"], "auc": 0.75}
    elif invalid == "duplicate":
        sweep["table"] *= 2
    else:
        sweep["table"][0]["auc"] = float("nan")
    path.write_text(json.dumps(sweep))
    monkeypatch.setattr(
        v2, "_segment", lambda _: pytest.fail("must not load scientific inputs")
    )
    out = tmp_path / "confirm.json"
    with pytest.raises((ValueError, SystemExit)):
        v2.main(_confirm_args(out, path, tmp_path))
    assert not out.exists()


def test_missing_step_is_recorded_without_loading_inputs(tmp_path, monkeypatch):
    path = _choice(tmp_path / "sweep.json")
    monkeypatch.setattr(
        v2, "_segment", lambda _: pytest.fail("failed gate must decide first")
    )
    out = tmp_path / "confirm.json"
    assert v2.main(_confirm_args(out, path, tmp_path)) == 0
    record = json.loads(out.read_bytes())
    assert record["held_out"] is None and record["verdict"] == "DOES_NOT_RUN"
    assert sorted(record["failed_steps"]) == sorted(GATE)


def test_choice_hash_and_parsed_choice_use_one_capture(tmp_path, monkeypatch):
    path = _choice(tmp_path / "sweep.json")
    original = path.read_bytes()
    loads = json.loads

    def rewrite_after_capture(data):
        value = loads(data)
        if data == original:
            changed = loads(original)
            changed["chosen"]["depth"] = 99
            path.write_text(json.dumps(changed))
        return value

    monkeypatch.setattr(v2.json, "loads", rewrite_after_capture)
    out = tmp_path / "out.json"
    v2.main(_confirm_args(out, path, tmp_path))
    record = loads(out.read_bytes())
    assert record["chosen"]["depth"] == 0
    assert record["choice_sha256"] == hashlib.sha256(original).hexdigest()
    assert record["choice_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()


def test_output_created_during_scoring_cannot_be_overwritten(tmp_path, monkeypatch):
    out = tmp_path / "sweep.json"

    def segment_with_competing_writer(values):
        out.write_bytes(b"existing measurement")
        return _segment(values[0])

    monkeypatch.setattr(v2, "_segment", segment_with_competing_writer)
    with pytest.raises(FileExistsError):
        v2.main(
            [
                "sweep",
                str(out),
                "--segment",
                "dev",
                "mesh",
                "maps",
                "dev_66.zarr",
                "labels",
                "--depths",
                "0",
                "0",
            ]
        )
    assert out.read_bytes() == b"existing measurement"


def test_wrong_checkout_helper_fails_without_changing_import_path(
    monkeypatch, tmp_path
):
    fake = SimpleNamespace(
        __name__="mesh_step_analysis", __file__=str(tmp_path / "mesh_step_analysis.py")
    )
    monkeypatch.setitem(sys.modules, "mesh_step_analysis", fake)
    path = sys.path[:]
    with pytest.raises(ImportError, match="another checkout"):
        _load("surface_control_v2")
    assert sys.path == path


def test_transfer_helper_cannot_keep_another_cached_analysis(monkeypatch):
    monkeypatch.setattr(v2.transfer_maps, "analysis", object())
    with pytest.raises(ImportError, match="inconsistent cached imports"):
        _load("surface_control_v2")


@pytest.mark.parametrize("names", [("a", "a"), ("a/x", "b/x")])
def test_segment_or_gate_names_cannot_collapse_into_one_reading(
    tmp_path, monkeypatch, names
):
    path = _choice(tmp_path / "sweep.json")
    monkeypatch.setattr(
        v2, "_segment", lambda _: pytest.fail("names must be checked first")
    )
    with pytest.raises(SystemExit, match="2"):
        v2.main(_confirm_args(tmp_path / "out.json", path, tmp_path, names))


@pytest.mark.parametrize(
    "scores, labels",
    [
        (np.array([0.0, np.nan]), np.array([False, True])),
        (np.array([0.0, np.inf]), np.array([False, True])),
        (np.array([0.0, 1.0]), np.array([0, 1])),
        (np.ones((1, 2)), np.array([False, True])),
    ],
)
def test_auc_rejects_invalid_measurements(scores, labels):
    with pytest.raises(ValueError):
        v2.auc(scores, labels)


def test_unscorable_held_out_segment_cannot_claim_a_threshold_pass():
    segment = _segment()
    segment.scorable = lambda: False
    with pytest.raises(ValueError, match="too few scored cells"):
        v2.held_out_reading(segment, 0, "reverse")


def test_geometry_and_map_preparation_are_the_historical_snapshot():
    names = {
        "labels_on_lattice",
        "cell_classes",
        "ensemble",
        "slid_floor",
        "Segment",
        "read_gate",
    }
    constants = {
        "LABEL_LEVEL",
        "SUPERVISED_MIN",
        "INK_MIN",
        "BARE_MAX",
        "SLIDE_CELLS",
        "MIN_CELLS",
        "P1_AUC",
        "P1_MARGIN",
        "P2_AUC",
    }

    def definitions(path):
        tree = ast.parse(path.read_text())
        out = {
            node.name: ast.dump(node)
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
        }
        out.update(
            {
                node.targets[0].id: ast.dump(node)
                for node in tree.body
                if isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id in constants
            }
        )
        return out

    assert hashlib.sha256((HERE / "surface_control.py").read_bytes()).hexdigest() == (
        "809bffb85ac3b21006a0f80df66a194b69b3817e3a0c6aec17b4dce9b75f982a"
    )
    assert definitions(HERE / "surface_control_v2.py") == definitions(
        HERE / "surface_control.py"
    )


def test_published_rounded_record_is_not_implicitly_upgraded():
    record = json.loads(
        (ROOT / "reports/first_letters_0841_surface_control.json").read_bytes()
    )
    assert record.get("protocol") != v2.PROTOCOL
    readings = record["held_out"]
    assert sorted(row["auc"] for row in readings.values()) == [0.7194, 0.7478]
    assert (
        v2.verdict(GATE, readings)["verdict"]
        == record["verdict"]
        == "BLOB_LEVEL_SIGNAL"
    )


def test_isolated_cli_works_from_another_directory(tmp_path):
    command = [sys.executable, "-I", str(HERE / "surface_control_v2.py"), "--help"]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "Candidate v2" in result.stdout
