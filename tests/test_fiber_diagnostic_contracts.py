"""Diagnostic evidence gates run without a sibling ScrollGT checkout."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts import fiber_miss_diagnostic as mod

REPO = Path(__file__).resolve().parents[1]


def recorded():
    return json.loads((REPO / "reports/fiber_miss_diagnostic.json").read_text())


def points():
    return np.array([[0, 0, 0], [1, 0, 0]]), np.ones(2)


def test_recorded_complete_verdict_is_preserved():
    report = recorded()
    assert mod.verdict(report["cubes"]) == report["verdict"]


def test_verdict_requires_every_registered_control():
    report = recorded()
    rows = {c: report["cubes"][c] for c in (*mod.NEW_S5, *mod.IN_S5)}
    with pytest.raises(ValueError, match="partial"):
        mod.verdict(rows)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1, True])
def test_nonfinite_or_invalid_gate_never_yields_a_conclusion(value):
    rows = copy.deepcopy(recorded()["cubes"])
    rows[mod.NEW_S5[0]]["g2_zero_shift_coverage"] = value
    result = mod.verdict(rows)
    assert result["status"] == "INSTRUMENT_FAILED"
    assert "conclusion" not in result


def test_nan_threshold_does_not_claim_rescue():
    rows = copy.deepcopy(recorded()["cubes"])
    rows[mod.NEW_S5[0]]["sweep"]["coverage"]["0.1"] = float("nan")
    result = mod.verdict(rows)
    assert result["status"] == "INSTRUMENT_FAILED"
    assert "conclusion" not in result


def test_empty_mask_does_not_gain_fictitious_boundary_coverage():
    idx, weights = points()
    mask = np.zeros((8, 8, 8), dtype=bool)
    assert mod.shift_search(mask, idx, weights, max_shift=0)["zero"] == 0


def test_perfect_coverage_has_no_soft_misses_to_measure():
    idx, weights = points()
    result = mod.threshold_sweep(np.ones((8, 8, 8)), idx, weights)
    assert result["soft_miss_fraction"] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_probabilities_are_rejected(value):
    idx, weights = points()
    probability = np.zeros((8, 8, 8), dtype=np.float32)
    probability[7, 7, 7] = value
    with pytest.raises(ValueError, match="probability"):
        mod.threshold_sweep(probability, idx, weights)


def test_no_in_bounds_length_is_not_zero_coverage():
    idx, weights = points()
    idx += 50
    with pytest.raises(ValueError, match="in-bounds"):
        mod.threshold_sweep(np.ones((8, 8, 8)), idx, weights)


def test_rescuing_one_cube_does_not_claim_both_are_rescued():
    rows = copy.deepcopy(recorded()["cubes"])
    row = rows[mod.NEW_S5[0]]
    row["sweep"]["coverage"]["0.1"] = 0.9
    row["sweep"]["soft_miss_fraction"] = (0.9 - row["g2_ballmax_coverage_at_0.5"]) / (
        1 - row["g2_ballmax_coverage_at_0.5"]
    )
    assert mod.verdict(rows)["conclusion"] == "THRESHOLD_PARTIAL"


@pytest.mark.parametrize("key", ["published_cc_coverage", "g2_ballmax_coverage_at_0.5"])
def test_other_gate_values_cannot_be_nan(key):
    rows = recorded()["cubes"]
    rows[mod.NEW_S5[0]][key] = float("nan")
    assert mod.verdict(rows)["status"] == "INSTRUMENT_FAILED"


def test_a_control_cannot_hide_by_changing_its_split():
    rows = recorded()["cubes"]
    rows[mod.IN_S5[0]]["split"] = "held_out"
    assert mod.verdict(rows)["status"] == "INSTRUMENT_FAILED"


def test_undefined_soft_comparison_never_claims_a_verdict():
    rows = recorded()["cubes"]
    row = rows[mod.NEW_S5[0]]
    row.update(
        {
            "published_cc_coverage": 1.0,
            "g2_zero_shift_coverage": 1.0,
            "g2_ballmax_coverage_at_0.5": 1.0,
        }
    )
    row["shift"].update(best=1.0, gain=0.0)
    row["sweep"]["coverage"]["0.1"] = 1.0
    row["sweep"]["soft_miss_fraction"] = None
    assert mod.verdict(rows)["status"] == "INSTRUMENT_FAILED"


@pytest.mark.parametrize(
    "bad", [np.empty((0, 3), dtype=int), np.ones((2, 3)), np.ones((2, 2), dtype=int)]
)
def test_invalid_sample_indices_are_rejected(bad):
    with pytest.raises(ValueError, match="indices"):
        mod.threshold_sweep(np.zeros((8, 8, 8)), bad, np.ones(len(bad)))


@pytest.mark.parametrize(
    "weights",
    [
        np.zeros(2),
        np.array([1.0, -1.0]),
        np.array([1.0, np.nan]),
        np.ones(3),
        np.ones(2, dtype=bool),
    ],
)
def test_invalid_sample_lengths_are_rejected(weights):
    idx, _ = points()
    with pytest.raises(ValueError, match="lengths"):
        mod.shift_search(np.ones((8, 8, 8), dtype=bool), idx, weights, max_shift=0)


@pytest.mark.parametrize("max_shift", [True, -1, 5, 1.5])
def test_shift_work_is_bounded_to_the_registered_search(max_shift):
    idx, weights = points()
    with pytest.raises(ValueError, match="max_shift"):
        mod.shift_search(
            np.ones((8, 8, 8), dtype=bool), idx, weights, max_shift=max_shift
        )


def prepared(tmp_path, monkeypatch, rows=None):
    """Publication tests use committed rows, without pretending to rerun ScrollGT."""
    root, cache = tmp_path / "scrollgt", tmp_path / "probabilities"
    cache.mkdir()
    for cube in mod.CUBES:
        (root / "data" / f"fibers_{cube}").mkdir(parents=True)
        np.save(cache / f"{cube}_fiberprob.npy", np.zeros((2, 2, 2)))
    monkeypatch.setattr(mod, "configure_scrollgt", lambda path: path)
    rows = recorded()["cubes"] if rows is None else rows
    monkeypatch.setattr(
        mod, "diagnose", lambda cube, **kwargs: copy.deepcopy(rows[cube])
    )
    output = tmp_path / "results" / "diagnostic.json"
    args = [
        "--scrollgt-root",
        str(root),
        "--prob-dir",
        str(cache),
        "--out",
        str(output),
    ]
    return root, cache, output, args


def test_full_publication_retains_the_saved_verdict(tmp_path, monkeypatch):
    root, cache, output, args = prepared(tmp_path, monkeypatch)
    assert mod.main(args) == 0
    result = json.loads(output.read_text())
    assert result["verdict"] == recorded()["verdict"]
    assert result["mode"] == "registered_full" and len(result["cubes"]) == 21
    assert result["scrollgt_root"] == str(root)
    assert result["probability_dirs"] == [str(cache)]


def test_missing_control_fails_before_computing_any_cube(tmp_path, monkeypatch):
    root, _, output, args = prepared(tmp_path, monkeypatch)
    (root / "data" / f"fibers_{mod.IN_S1[0]}").rmdir()
    monkeypatch.setattr(
        mod, "diagnose", lambda *a, **k: pytest.fail("partial sample was executed")
    )
    assert mod.main(args) == 1 and not output.exists()


def test_failed_instrument_is_preserved_as_failure_not_success(tmp_path, monkeypatch):
    rows = recorded()["cubes"]
    rows[mod.NEW_S5[0]]["g1_prob_threshold_equals_shipped_mask"] = False
    _, _, output, args = prepared(tmp_path, monkeypatch, rows)
    assert mod.main(args) == 1
    result = json.loads(output.read_text())
    assert result["verdict"]["status"] == "INSTRUMENT_FAILED"
    assert "conclusion" not in result["verdict"]


def test_subset_is_explicit_and_never_has_a_full_verdict(tmp_path, monkeypatch):
    _, _, output, args = prepared(tmp_path, monkeypatch)
    assert mod.main([*args, "--cubes", mod.NEW_S5[0]]) == 0
    result = json.loads(output.read_text())
    assert result["mode"] == "descriptive_subset"
    assert "verdict" not in result and len(result["cubes"]) == 1


def test_subset_also_returns_failure_for_bad_evidence(tmp_path, monkeypatch):
    rows = recorded()["cubes"]
    rows[mod.NEW_S5[0]]["g1_prob_threshold_equals_shipped_mask"] = False
    _, _, output, args = prepared(tmp_path, monkeypatch, rows)
    assert mod.main([*args, "--cubes", mod.NEW_S5[0]]) == 1
    assert json.loads(output.read_text())["instrument"]["status"] == "INSTRUMENT_FAILED"


def test_perfect_subset_can_report_null_without_claiming_a_full_verdict(
    tmp_path, monkeypatch
):
    rows = recorded()["cubes"]
    row = rows[mod.NEW_S5[0]]
    row.update(
        {
            "published_cc_coverage": 1.0,
            "g2_zero_shift_coverage": 1.0,
            "g2_ballmax_coverage_at_0.5": 1.0,
        }
    )
    row["shift"].update(best=1.0, gain=0.0)
    row["sweep"]["coverage"]["0.1"] = 1.0
    row["sweep"]["soft_miss_fraction"] = None
    _, _, output, args = prepared(tmp_path, monkeypatch, rows)
    assert mod.main([*args, "--cubes", mod.NEW_S5[0]]) == 0
    result = json.loads(output.read_text())
    assert result["cubes"][mod.NEW_S5[0]]["sweep"]["soft_miss_fraction"] is None
    assert result["instrument"]["status"] == "OK" and "verdict" not in result


def test_selected_source_cannot_reuse_another_checkouts_code(tmp_path, monkeypatch):
    from types import SimpleNamespace

    root = tmp_path / "selected"
    package = root / "src" / "scrollgt" / "fibers"
    package.mkdir(parents=True)
    (package / "target.py").write_text("")
    (package / "eval_trace.py").write_text("")
    monkeypatch.syspath_prepend(str(root))
    monkeypatch.setattr(
        mod.importlib,
        "import_module",
        lambda name: SimpleNamespace(
            __file__=str(tmp_path / "different" / "source.py")
        ),
    )
    with pytest.raises(ValueError, match="different ScrollGT checkout"):
        mod.configure_scrollgt(root)


def test_existing_output_is_never_replaced(tmp_path, monkeypatch):
    _, _, output, args = prepared(tmp_path, monkeypatch)
    output.parent.mkdir()
    output.write_text("previous artifact")
    monkeypatch.setattr(
        mod, "diagnose", lambda *a, **k: pytest.fail("existing output was accepted")
    )
    assert mod.main(args) == 1 and output.read_text() == "previous artifact"


def test_output_cannot_enter_an_input_tree(tmp_path, monkeypatch):
    _, cache, output, args = prepared(tmp_path, monkeypatch)
    forbidden = cache / "diagnostic.json"
    args[args.index(str(output))] = str(forbidden)
    assert mod.main(args) == 1 and not forbidden.exists()


def test_ambiguous_probability_sources_are_rejected(tmp_path, monkeypatch):
    _, cache, output, args = prepared(tmp_path, monkeypatch)
    duplicate = tmp_path / "duplicate"
    duplicate.mkdir()
    np.save(duplicate / f"{mod.NEW_S5[0]}_fiberprob.npy", np.zeros((2, 2, 2)))
    assert mod.main([*args, "--prob-dir", str(duplicate)]) == 1 and not output.exists()


def test_duplicate_cube_selection_is_rejected(tmp_path, monkeypatch):
    _, _, output, args = prepared(tmp_path, monkeypatch)
    assert mod.main([*args, "--cubes", mod.NEW_S5[0], mod.NEW_S5[0]]) == 1
    assert not output.exists()


def test_read_failure_does_not_publish_a_partial_artifact(tmp_path, monkeypatch):
    _, _, output, args = prepared(tmp_path, monkeypatch)

    def broken(*args, **kwargs):
        raise OSError("probability file torn during read")

    monkeypatch.setattr(mod, "diagnose", broken)
    assert mod.main(args) == 1 and not output.exists()


def test_nonfinite_report_cannot_be_published_as_json(tmp_path, monkeypatch):
    rows = recorded()["cubes"]
    rows[mod.NEW_S5[0]]["sweep"]["soft_miss_fraction"] = float("nan")
    _, _, output, args = prepared(tmp_path, monkeypatch, rows)
    assert mod.main(args) == 1 and not output.exists()


def test_real_cli_from_another_directory(tmp_path):
    """A tiny explicit stub tests the CLI contract, not scientific ScrollGT equivalence."""
    root, cache = tmp_path / "scrollgt", tmp_path / "prob"
    package = root / "src" / "scrollgt" / "fibers"
    package.mkdir(parents=True)
    cache.mkdir()
    (package.parent / "__init__.py").write_text("")
    (package / "__init__.py").write_text("")
    (package / "eval_trace.py").write_text(
        "def _resample_fiber(coords, edges, step):\n"
        "    for coord in coords:\n"
        "        yield coord, 1.0\n"
    )
    (package / "target.py").write_text(
        "import json\nimport numpy as np\nfrom types import SimpleNamespace\n"
        "def load_fiber_target(path):\n"
        "    fiber = SimpleNamespace(coords=np.array([[6.,6.,6.],[13.,13.,13.]]), edges=None)\n"
        "    return SimpleNamespace(fibers=[fiber]), np.load(path/'mask.npy'), json.loads((path/'meta.json').read_text())\n"
    )
    cube = mod.NEW_S5[0]
    target = root / "data" / f"fibers_{cube}"
    target.mkdir(parents=True)
    probability = np.zeros((20, 20, 20), dtype=np.float32)
    probability[6, 6, 6] = 0.9
    np.save(cache / f"{cube}_fiberprob.npy", probability)
    np.save(target / "mask.npy", probability >= 0.5)
    (target / "meta.json").write_text(
        json.dumps(
            {
                "split": "held_out",
                "floors": {"floor_connected_components": {"coverage": 0.5}},
            }
        )
    )
    output = tmp_path / "result.json"
    command = [
        sys.executable,
        str(REPO / "scripts/fiber_miss_diagnostic.py"),
        "--scrollgt-root",
        str(root),
        "--prob-dir",
        str(cache),
        "--out",
        str(output),
        "--cubes",
        cube,
    ]
    run = subprocess.run(
        command, cwd=tmp_path, capture_output=True, text=True, timeout=30
    )
    assert run.returncode == 0, run.stderr
    result = json.loads(output.read_text())
    assert (
        result["mode"] == "descriptive_subset"
        and result["instrument"]["status"] == "OK"
    )
    assert result["cubes"][cube]["g2_zero_shift_coverage"] == 0.5
    assert "verdict" not in result
    # Corrupt source geometry: the real CLI must fail and leave no report.
    np.save(target / "mask.npy", np.zeros((3, 3, 3), dtype=bool))
    command[command.index(str(output))] = str(tmp_path / "bad.json")
    bad = subprocess.run(
        command, cwd=tmp_path, capture_output=True, text=True, timeout=30
    )
    assert bad.returncode == 1 and "match the probability shape" in bad.stderr
    assert not (tmp_path / "bad.json").exists()
