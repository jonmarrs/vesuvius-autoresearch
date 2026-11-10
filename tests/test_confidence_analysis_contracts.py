"""Incomplete confidence analyses must never become positive research findings."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import tifffile
from PIL import Image

from scripts import (
    confidence_inputs as inputs,
    measure_confidence_vs_reproducibility as mod,
)


def test_duplicate_arms_cannot_create_a_finding_without_comparisons(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(
        sys,
        "argv",
        ["analysis", "--spiral-out", str(tmp_path), "--arms", "same", "same", "same"],
    )
    monkeypatch.setattr(
        mod, "binned_maps", lambda *a: ((np.ones((2, 2)), np.ones((2, 2))), (0, 0))
    )
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2
    assert "CONFIDENCE PREDICTS" not in capsys.readouterr().out


def test_sparse_binning_is_finite_and_explicitly_indeterminate():
    arms = {f"seed{i}": (np.zeros((4, 4)), np.zeros((4, 4))) for i in range(3)}
    result = mod.one_binning(arms, 4, 4, np.random.default_rng(0))
    assert result.get("status") == "INDETERMINATE"
    assert result["diff"] is None and result["p"] is None


def metrics(path, pixels, foreground):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "summary": {"total_pixels": pixels, "total_fg_pixels": foreground},
                "strips": [{"total_pixels": pixels, "fg_pixels": foreground}],
            }
        )
    )


def arm_fixture(root, seed, *, empty=False):
    h, w = 8, 20
    z, theta = np.meshgrid(
        np.linspace(*mod.Z_RANGE, h),
        np.linspace(-np.pi, np.pi, w, endpoint=False),
        indexing="ij",
    )
    xyz = (500 + 100 * np.cos(theta), 500 + 100 * np.sin(theta), z)
    directory = root / "meshes/concat/w120-129_flat"
    directory.mkdir(parents=True)
    for axis, array in zip("xyz", xyz, strict=True):
        tifffile.imwrite(directory / f"{axis}.tif", array)
    selected = np.zeros((h, w), bool)
    if not empty:
        selected[:, : w // 2] = True
        if seed == 0:
            selected[:, w // 2 :] = True
    mask = selected.repeat(10, 0).repeat(10, 1)
    probability = np.full(mask.shape, 0.1, np.float32)
    probability[mask] = 0.6
    if not empty:
        probability[:, : w * 5] = 0.85
    pred = root / "ink_metric_prob/predictions"
    pred.mkdir(parents=True)
    path = pred / "w120-129_flat_flat_prob.npy"
    np.save(path, probability)
    Image.fromarray(mask.astype(np.uint8) * 255).save(pred / "w120-129_flat_mask.png")
    for scorer in ("ink_metric", "ink_metric_prob"):
        metrics(root / scorer / "metrics.json", mask.size, int(mask.sum()))
    return path


def study(tmp_path, *, empty=False):
    for seed in range(3):
        arm_fixture(tmp_path / f"outer_seed{seed}", seed, empty=empty)
    return ["--spiral-out", str(tmp_path), "--arms", "seed0", "seed1", "seed2"]


def test_real_artifacts_produce_versioned_gated_report(tmp_path):
    flags = study(tmp_path)
    output = tmp_path / "analysis.json"
    output.write_text("prior report")
    output.chmod(0o640)
    assert mod.main([*flags, "--json", str(output)]) == 0
    report = json.loads(output.read_text())
    assert report["analysis_version"] == 2
    assert report["verdict"] == "CONFIDENCE ASSOCIATES WITH BIN AGREEMENT"
    assert len(report["results"]) == 3
    assert all(row["diff"] == pytest.approx(0.25) for row in report["results"])
    assert all(1 / 1001 <= row["p"] <= 1 for row in report["results"])
    assert all(gate["passed"] for gate in report["validity_gate"].values())
    assert report["thresholding_benefit_tested"] is False
    assert output.stat().st_mode & 0o777 == 0o640


def test_sparse_cli_report_uses_nulls_and_nonzero_exit(tmp_path, capsys):
    flags = study(tmp_path, empty=True)
    output = tmp_path / "analysis.json"
    assert mod.main([*flags, "--json", str(output)]) == 1
    report = json.loads(
        output.read_text(), parse_constant=lambda value: pytest.fail(value)
    )
    assert report["status"] == report["verdict"] == "INDETERMINATE"
    assert all(row["diff"] is None and row["p"] is None for row in report["results"])
    assert "CONFIDENCE ASSOCIATES" not in capsys.readouterr().out


def test_ink_probability_reduction_ignores_background_and_tile_boundaries(
    tmp_path, monkeypatch
):
    pred = tmp_path / "ink_metric_prob/predictions"
    pred.mkdir(parents=True)
    probability = np.random.default_rng(3).random((20, 30))
    selected = np.random.default_rng(4).random(probability.shape) > 0.7
    np.save(pred / "w120-129_flat_flat_prob.npy", probability)
    for index, mask in enumerate((selected[:, :13], selected[:, 13:])):
        Image.fromarray(mask.astype(np.uint8) * 255).save(
            pred / f"w120-129_flat_mask.{index:03}.png"
        )
    monkeypatch.setattr(inputs, "BLOCK_COLUMNS", 7)
    path = inputs.probability_path(tmp_path)
    counts, sums = inputs.probability_sums(path, inputs.mask_paths(path), (2, 3))
    expected_counts = selected.reshape(2, 10, 3, 10).sum(axis=(1, 3))
    expected_sums = (probability * selected).reshape(2, 10, 3, 10).sum(axis=(1, 3))
    np.testing.assert_array_equal(counts, expected_counts)
    np.testing.assert_allclose(sums, expected_sums, rtol=1e-14)
    np.testing.assert_allclose(
        mod.load_prob(tmp_path, (2, 3)), expected_sums / expected_counts
    )
    assert not np.allclose(
        sums, probability.reshape(2, 10, 3, 10).mean(axis=(1, 3)) * counts
    )


@pytest.mark.parametrize(
    "original,rescored,passed",
    [(2000, 2002, True), (2000, 2003, False), (0, 0, True), (0, 1, False)],
)
def test_registered_count_gate_boundary(tmp_path, original, rescored, passed):
    metrics(tmp_path / "ink_metric/metrics.json", 3000, original)
    metrics(tmp_path / "ink_metric_prob/metrics.json", 3000, rescored)
    if passed:
        assert inputs.count_gate(tmp_path, 3000, rescored, 0.001)["passed"]
    else:
        with pytest.raises(ValueError, match="tolerance"):
            inputs.count_gate(tmp_path, 3000, rescored, 0.001)


@pytest.mark.parametrize(
    "damage", ["rescore_count", "original_total", "missing", "boolean", "incomplete"]
)
def test_invalid_metrics_cannot_pass_gate(tmp_path, damage):
    root = tmp_path / "arm"
    arm_fixture(root, 0)
    path = root / "ink_metric/metrics.json"
    record = json.loads(path.read_text())
    if damage == "rescore_count":
        path = root / "ink_metric_prob/metrics.json"
        record["summary"]["total_fg_pixels"] -= 1
        record["strips"][0]["fg_pixels"] -= 1
    elif damage == "original_total":
        record["summary"]["total_pixels"] += 1
        record["strips"][0]["total_pixels"] += 1
    elif damage == "boolean":
        record["summary"]["total_fg_pixels"] = True
    elif damage == "incomplete":
        record["strips"] = []
    if damage == "missing":
        path.unlink()
    else:
        path.write_text(json.dumps(record))
    with pytest.raises((OSError, ValueError)):
        mod.load_arm(root)


@pytest.mark.parametrize(
    "damage",
    [
        "nan",
        "negative",
        "above_one",
        "integer",
        "shape",
        "ambiguous",
        "mask_rgb",
        "mask_values",
        "mask_gap",
        "mask_short",
    ],
)
def test_invalid_probability_or_mask_artifacts_are_refused(tmp_path, damage):
    path = arm_fixture(tmp_path, 0)
    probability = np.load(path)
    if damage in {"nan", "negative", "above_one"}:
        probability[0, 0] = {"nan": np.nan, "negative": -0.01, "above_one": 1.01}[
            damage
        ]
    elif damage == "integer":
        probability = probability.astype(np.uint8)
    elif damage == "shape":
        probability = probability[:1]
    np.save(path, probability)
    mask = path.parent / "w120-129_flat_mask.png"
    if damage == "ambiguous":
        np.save(path.parent / "other_prob.npy", probability)
    elif damage == "mask_rgb":
        Image.fromarray(np.zeros((*probability.shape, 3), np.uint8)).save(mask)
    elif damage == "mask_values":
        Image.fromarray(np.full(probability.shape, 128, np.uint8)).save(mask)
    elif damage == "mask_gap":
        mask.rename(mask.with_name("w120-129_flat_mask.001.png"))
    elif damage == "mask_short":
        Image.fromarray(np.zeros((80, 199), np.uint8)).save(mask)
    with pytest.raises(ValueError):
        mod.load_arm(tmp_path)


def rows(diffs, ps=None):
    return [
        {
            "bins": list(binning),
            "status": "MEASURED",
            "diff": diff,
            "p": p,
            "n_unanimous": 80,
            "n_lone": 80,
        }
        for binning, diff, p in zip(mod.BINNINGS, diffs, ps or [0.001] * 3, strict=True)
    ]


@pytest.mark.parametrize(
    "diffs,ps,expected",
    [
        ([0.1] * 3, None, "CONFIDENCE ASSOCIATES WITH BIN AGREEMENT"),
        ([-0.1] * 3, None, "OPPOSITE ASSOCIATION"),
        ([0.1, 0.1, 0], None, "BIN-DEPENDENT"),
        ([-0.1, 0, 0], None, "BIN-DEPENDENT"),
        ([0.1, 0.1, -0.1], None, "BIN-DEPENDENT"),
        ([0.05] * 3, None, "NO REGISTERED EFFECT DETECTED"),
        ([0.1] * 3, [0.05] * 3, "NO REGISTERED EFFECT DETECTED"),
    ],
)
def test_decision_requires_registered_effect_at_every_binning(diffs, ps, expected):
    assert mod.decide(rows(diffs, ps))[0] == expected


def test_empty_or_nonfinite_comparisons_do_not_pass_decision():
    assert mod.decide([])[0] == "INDETERMINATE"
    assert mod.decide(rows([0.1, np.nan, 0.1]))[0] == "INDETERMINATE"
    result = rows([0.1] * 3)
    result[1]["bins"] = result[0]["bins"]
    assert mod.decide(result)[0] == "INDETERMINATE"


def test_modified_input_blocks_report_publication(tmp_path, monkeypatch):
    flags = study(tmp_path)
    output = tmp_path / "report.json"
    output.write_text("prior report")
    original = mod.one_binning

    def changed(*args):
        result = original(*args)
        path = tmp_path / "outer_seed0/ink_metric_prob/metrics.json"
        path.write_text(path.read_text() + " ")
        return result

    monkeypatch.setattr(mod, "one_binning", changed)
    with pytest.raises(SystemExit) as exc:
        mod.main([*flags, "--json", str(output)])
    assert exc.value.code == 1
    assert output.read_text() == "prior report"


def test_report_cannot_replace_an_input_alias(tmp_path):
    flags = study(tmp_path)
    source = (
        tmp_path / "outer_seed0/ink_metric_prob/predictions/w120-129_flat_flat_prob.npy"
    )
    before = source.read_bytes()
    output = tmp_path / "report.json"
    os.link(source, output)
    with pytest.raises(SystemExit) as exc:
        mod.main([*flags, "--json", str(output)])
    assert exc.value.code == 1
    assert source.read_bytes() == before


def test_input_directories_and_physical_arm_aliases_are_rejected(tmp_path):
    flags = study(tmp_path)
    output = tmp_path / "outer_seed0/new.json"
    with pytest.raises(SystemExit) as exc:
        mod.main([*flags, "--json", str(output)])
    assert exc.value.code == 1 and not output.exists()
    (tmp_path / "outer_alias").symlink_to(
        tmp_path / "outer_seed0", target_is_directory=True
    )
    with pytest.raises(SystemExit) as exc:
        mod.main(["--spiral-out", str(tmp_path), "--arms", "seed0", "alias", "seed2"])
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "key,value",
    [("p", 0), ("p", -1), ("p", 2), ("p", True), ("diff", float("inf")), ("diff", 2)],
)
def test_invalid_statistics_are_indeterminate(key, value):
    result = rows([0.1] * 3)
    result[0][key] = value
    assert mod.decide(result)[0] == "INDETERMINATE"


def test_shuffle_probability_is_never_zero():
    ink = np.zeros((3, 40, 4))
    ink[:, :, :2] = 1
    ink[0, :, 2:] = 1
    weighted = ink * 0.5
    weighted[:, :, :2] = 0.8
    data = {str(i): (ink[i], weighted[i]) for i in range(3)}
    assert mod.one_binning(data, 40, 4, np.random.default_rng(1))["p"] == 1 / 1001


def test_tile_budget_is_checked_before_decoding(tmp_path, monkeypatch):
    path = arm_fixture(tmp_path, 0)
    monkeypatch.setattr(inputs, "MAX_MASK_TILE_PIXELS", 1)
    with pytest.raises(ValueError, match="mask tile exceeds"):
        inputs.probability_sums(path, inputs.mask_paths(path), (8, 20))


def test_report_write_failure_keeps_previous_file(tmp_path, monkeypatch):
    flags = study(tmp_path)
    output = tmp_path / "analysis.json"
    output.write_text("prior report")

    def failed(value, stream, **kwargs):
        stream.write("partial")
        raise OSError("report write failed")

    monkeypatch.setattr(json, "dump", failed)
    with pytest.raises(SystemExit) as exc:
        mod.main([*flags, "--json", str(output)])
    assert exc.value.code == 1
    assert output.read_text() == "prior report"
    assert not list(tmp_path.glob(".analysis.json.*"))


def test_command_line_from_another_directory_writes_indeterminate_report(tmp_path):
    flags = study(tmp_path, empty=True)
    output = tmp_path / "analysis.json"
    result = subprocess.run(
        [sys.executable, mod.__file__, *flags, "--json", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
        timeout=30,
    )
    assert result.returncode == 1, result.stderr
    assert "VERDICT: INDETERMINATE" in result.stdout
    assert json.loads(output.read_text())["status"] == "INDETERMINATE"


# Review of #388: each test below isolates one guard that the tests above pass
# without exercising (a mutant removing the guard left them passing).


def test_a_second_probability_map_is_ambiguous_even_when_it_sorts_last(tmp_path):
    path = arm_fixture(tmp_path, 0)
    np.save(path.parent / "zz_flat_prob.npy", np.load(path))
    with pytest.raises(ValueError, match="exactly one probability map"):
        mod.load_arm(tmp_path)


@pytest.mark.parametrize(
    "name,message",
    [
        ("w130-139_flat_mask.png", "does not belong"),
        ("w120-129_flat_mask.000.png", "cannot mix"),
    ],
)
def test_unrelated_or_mixed_masks_are_refused(tmp_path, name, message):
    path = arm_fixture(tmp_path, 0)
    mask = path.parent / "w120-129_flat_mask.png"
    shutil.copy(mask, mask.with_name(name))
    with pytest.raises(ValueError, match=message):
        mod.load_arm(tmp_path)


@pytest.mark.parametrize("encoding", ["uint8", "bilevel"])
def test_zero_one_masks_count_the_same_ink_as_zero_255(tmp_path, encoding):
    path = arm_fixture(tmp_path, 1)
    expected = mod.load_arm(tmp_path)
    mask = path.parent / "w120-129_flat_mask.png"
    with Image.open(mask) as image:
        selected = np.asarray(image) > 0
    if encoding == "uint8":
        Image.fromarray(selected.astype(np.uint8)).save(mask)
    else:
        Image.fromarray(selected).save(mask)
    arm = mod.load_arm(tmp_path)
    assert arm.ink.sum() == expected.ink.sum() == selected.sum()
    np.testing.assert_array_equal(arm.ink, expected.ink)
    np.testing.assert_array_equal(arm.probability_sum, expected.probability_sum)


def test_a_missing_inkless_final_tile_is_refused_although_counts_agree(tmp_path):
    path = arm_fixture(tmp_path, 1)  # ink in the left half only
    mask = path.parent / "w120-129_flat_mask.png"
    with Image.open(mask) as image:
        values = np.asarray(image)
    mask.unlink()
    for index, columns in enumerate((slice(0, 100), slice(100, None))):
        Image.fromarray(values[:, columns]).save(
            path.parent / f"w120-129_flat_mask.{index:03}.png"
        )
    assert mod.load_arm(tmp_path).ink.sum() == (values > 0).sum()
    (path.parent / "w120-129_flat_mask.001.png").unlink()
    with pytest.raises(ValueError, match="exactly cover"):
        mod.load_arm(tmp_path)


def test_probability_must_match_the_grid_width_as_well_as_height(tmp_path):
    path = arm_fixture(tmp_path, 0)
    np.save(path, np.pad(np.load(path), ((0, 0), (0, 10)), constant_values=0.5))
    with pytest.raises(ValueError, match="exactly 10x"):
        mod.load_arm(tmp_path)


def test_coordinate_grid_cell_limit_is_enforced(tmp_path, monkeypatch):
    path = arm_fixture(tmp_path, 0)
    monkeypatch.setattr(inputs, "MAX_GRID_CELLS", 8 * 20)
    inputs.probability_sums(path, inputs.mask_paths(path), (8, 20))
    monkeypatch.setattr(inputs, "MAX_GRID_CELLS", 8 * 20 - 1)
    with pytest.raises(ValueError, match="coordinate grid exceeds"):
        inputs.probability_sums(path, inputs.mask_paths(path), (8, 20))


def test_probability_blocks_stay_within_the_pixel_budget(tmp_path, monkeypatch):
    path = arm_fixture(tmp_path, 2)
    expected = inputs.probability_sums(path, inputs.mask_paths(path), (8, 20))
    reads, load = [], np.load

    class Recorded:
        def __init__(self, array):
            self.array, self.shape, self.dtype = array, array.shape, array.dtype

        def __getitem__(self, key):
            reads.append(self.array[key].shape)
            return self.array[key]

    monkeypatch.setattr(np, "load", lambda *a, **k: Recorded(load(*a, **k)))
    monkeypatch.setattr(inputs, "MAX_BLOCK_PIXELS", 80 * 7)
    got = inputs.probability_sums(path, inputs.mask_paths(path), (8, 20))
    assert reads and max(rows * columns for rows, columns in reads) <= 80 * 7
    for value, reference in zip(got, expected, strict=True):
        np.testing.assert_array_equal(value, reference)


def test_documented_resource_bounds_match_the_constants():
    guide = (
        Path(mod.__file__).resolve().parents[1] / "docs/CONFIDENCE_REPRODUCIBILITY.md"
    )
    text = guide.read_text()
    for value in (
        inputs.MAX_BLOCK_PIXELS,
        inputs.BLOCK_COLUMNS,
        inputs.MAX_MASK_TILE_PIXELS,
        inputs.MAX_GRID_CELLS,
    ):
        assert f"{value:,}" in text


@pytest.mark.parametrize(
    "damage",
    [
        "float_total",
        "float_foreground",
        "negative_foreground",
        "strip_disagrees",
        "rescored_total",
        "original_drift",
    ],
)
def test_metrics_must_be_consistent_integers_within_tolerance(tmp_path, damage):
    root = tmp_path / "arm"
    arm_fixture(root, 1)  # 8,000 of 16,000 pixels are ink
    mod.load_arm(root)
    scorer = "ink_metric_prob" if damage == "rescored_total" else "ink_metric"
    path = root / scorer / "metrics.json"
    record = json.loads(path.read_text())
    summary, strip = record["summary"], record["strips"][0]
    for row, foreground in ((summary, "total_fg_pixels"), (strip, "fg_pixels")):
        if damage == "float_total":
            row["total_pixels"] = float(row["total_pixels"])
        elif damage == "float_foreground":
            row[foreground] = float(row[foreground])
        elif damage == "negative_foreground":
            row[foreground] = -1
        elif damage == "rescored_total":
            row["total_pixels"] += 1
        elif damage == "original_drift":
            row[foreground] += 9  # 0.1125% of 8,000
    if damage == "strip_disagrees":
        strip["fg_pixels"] -= 1
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        mod.load_arm(root)


@pytest.mark.parametrize("rescored,passed", [(1998, True), (1997, False)])
def test_count_gate_tolerance_is_a_share_of_the_original(tmp_path, rescored, passed):
    metrics(tmp_path / "ink_metric/metrics.json", 3000, 2000)
    metrics(tmp_path / "ink_metric_prob/metrics.json", 3000, rescored)
    if passed:
        assert inputs.count_gate(tmp_path, 3000, rescored, 0.001)["passed"]
    else:
        with pytest.raises(ValueError, match="tolerance"):
            inputs.count_gate(tmp_path, 3000, rescored, 0.001)


@pytest.mark.parametrize("name", ["seed2/", "x/../outer_seed2"])
def test_arm_names_cannot_carry_path_syntax(tmp_path, name):
    study(tmp_path)
    (tmp_path / "outer_x").mkdir()
    with pytest.raises(SystemExit) as exc:
        mod.main(["--spiral-out", str(tmp_path), "--arms", "seed0", "seed1", name])
    assert exc.value.code == 2


def test_a_symlinked_report_path_is_refused_not_replaced(tmp_path):
    flags = study(tmp_path)
    target = tmp_path / "elsewhere.json"
    target.write_text("kept")
    output = tmp_path / "report.json"
    output.symlink_to(target)
    with pytest.raises(SystemExit) as exc:
        mod.main([*flags, "--json", str(output)])
    assert exc.value.code == 1
    assert output.is_symlink() and target.read_text() == "kept"


def test_report_records_every_input_seed_zero_and_untested_claims(
    tmp_path, monkeypatch
):
    flags = study(tmp_path)
    seeds, default_rng = [], np.random.default_rng

    def recorded(*args, **kwargs):
        seeds.append(args[0] if args else kwargs.get("seed"))
        return default_rng(*args, **kwargs)

    monkeypatch.setattr(np.random, "default_rng", recorded)
    output = tmp_path / "analysis.json"
    assert mod.main([*flags, "--json", str(output)]) == 0
    report = json.loads(output.read_text())
    assert seeds == [0]
    assert report["n_shuffle"] == 1000
    assert report["p_method"] == "two_sided_shuffle_plus_one"
    assert report["ink_correctness_tested"] is False
    assert report["thresholding_benefit_tested"] is False
    for tag in ("seed0", "seed1", "seed2"):
        root = tmp_path / f"outer_{tag}"
        expected = [
            root / "ink_metric_prob/predictions/w120-129_flat_flat_prob.npy",
            root / "ink_metric_prob/predictions/w120-129_flat_mask.png",
            root / "ink_metric/metrics.json",
            root / "ink_metric_prob/metrics.json",
            *(root / "meshes/concat/w120-129_flat" / f"{axis}.tif" for axis in "xyz"),
        ]
        assert set(report["input_file_states"][tag]) == {
            str(path.absolute()) for path in expected
        }
        gate = report["validity_gate"][tag]
        for key, scorer in (
            ("original_metrics", "ink_metric"),
            ("rescored_metrics", "ink_metric_prob"),
        ):
            digest = hashlib.sha256((root / scorer / "metrics.json").read_bytes())
            assert gate[key]["sha256"] == digest.hexdigest()


def test_shared_axis_is_the_first_arms_valid_coordinate_mean(tmp_path):
    flags = study(tmp_path)
    grid = tmp_path / "outer_seed0/meshes/concat/w120-129_flat"
    xyz = [tifffile.imread(grid / f"{axis}.tif") for axis in "xyz"]
    for axis, array in zip("xyz", xyz, strict=True):
        array[:, :3] = -1  # unrendered cells
        tifffile.imwrite(grid / f"{axis}.tif", array)
    other = tmp_path / "outer_seed1/meshes/concat/w120-129_flat/x.tif"
    tifffile.imwrite(other, tifffile.imread(other) + 50)
    output = tmp_path / "analysis.json"
    mod.main([*flags, "--json", str(output)])
    valid = (xyz[0] > 0) & (xyz[1] > 0)
    assert json.loads(output.read_text())["shared_axis"] == pytest.approx(
        [xyz[0][valid].mean(), xyz[1][valid].mean()]
    )


def cohorts(unanimous, lone, pairs=0, confidence=(0.8, 0.5, 0.1)):
    """One-column bins: unanimous, then lone (arm 0), then two-arm bins."""
    size = unanimous + lone + pairs
    ink, probability = np.zeros((3, size, 1)), np.zeros((3, size, 1))
    start = 0
    for arms, count, value in zip(
        (3, 1, 2), (unanimous, lone, pairs), confidence, strict=True
    ):
        ink[:arms, start : start + count] = 1
        probability[:arms, start : start + count] = value
        start += count
    return {f"seed{i}": (ink[i], probability[i]) for i in range(3)}, size


@pytest.mark.parametrize(
    "unanimous,lone,status",
    [(30, 30, "MEASURED"), (30, 29, "INDETERMINATE"), (29, 30, "INDETERMINATE")],
)
def test_each_cohort_needs_thirty_bins(unanimous, lone, status):
    arms, size = cohorts(unanimous, lone)
    result = mod.one_binning(arms, size, 1, np.random.default_rng(0))
    assert result["status"] == status


def test_two_arm_bins_are_neither_unanimous_nor_lone():
    arms, size = cohorts(40, 40, 40)
    result = mod.one_binning(arms, size, 1, np.random.default_rng(0))
    assert (result["n_unanimous"], result["n_lone"]) == (40, 40)
    assert result["mean_unanimous"] == pytest.approx(0.8)
    assert result["mean_lone"] == pytest.approx(0.5)


def test_differences_within_rounding_are_ties_in_the_shuffle():
    # (0.7 * 3) / 3 != 0.7: the cohorts differ only by rounding (about 1e-16).
    arms, size = cohorts(40, 40, confidence=(0.7, 0.7, 0.0))
    result = mod.one_binning(arms, size, 1, np.random.default_rng(0))
    assert 0 < abs(result["diff"]) < 1e-14
    assert result["p"] == 1.0


def test_shuffle_test_is_two_sided():
    arms, size = cohorts(40, 40, confidence=(0.5, 0.8, 0.0))
    result = mod.one_binning(arms, size, 1, np.random.default_rng(1))
    assert result["diff"] == pytest.approx(-0.3)
    assert result["p"] == 1 / 1001
