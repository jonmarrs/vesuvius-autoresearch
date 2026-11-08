"""Scan diagnostics must not turn quantization or orientation into signal."""

import json
import subprocess
import sys
from pathlib import Path

import nrrd
import numpy as np
import pytest

from scripts import measure_scan_quality as quality


def slab(shape=(32, 32, 32)):
    mask = np.zeros(shape, dtype=np.uint16)
    mask[10:22] = 1
    return mask


def test_constant_ct_has_chance_separability():
    mask = slab()
    auc, interior, gap = quality.outcome_separability(
        np.full(mask.shape, 128, np.uint8), mask
    )
    assert interior >= 1000 and gap >= 1000
    assert auc == 0.5


def test_quantized_separability_matches_pairwise_tie_oracle():
    from scipy import ndimage

    mask = slab()
    vol = (np.indices(mask.shape).sum(axis=0) % 3).astype(np.uint8)
    interior = ndimage.binary_erosion(mask > 0, iterations=2)
    distance = ndimage.distance_transform_edt(mask == 0)
    gap = (distance >= 2) & (distance <= 6)
    rng = np.random.default_rng(0)
    n = min(int(interior.sum()), int(gap.sum()), 200_000)
    positive = rng.choice(vol[interior], n, replace=False)
    negative = rng.choice(vol[gap], n, replace=False)
    # Count integer histogram pairs, with half credit for equal intensities.
    wins = sum(
        np.count_nonzero(positive == value)
        * (
            np.count_nonzero(negative < value)
            + 0.5 * np.count_nonzero(negative == value)
        )
        for value in range(3)
    )
    expected = max(wins / n**2, 1 - wins / n**2)
    assert quality.outcome_separability(vol, mask)[0] == pytest.approx(expected)


def test_layer_feature_does_not_depend_on_axis_alignment():
    z, y, x = np.indices((12, 12, 12), dtype=np.float32)
    axis = quality.predictors(x / 11)["tensor_anisotropy"]
    diagonal = quality.predictors((x + y + z) / 33)["tensor_anisotropy"]
    assert axis == pytest.approx(1, abs=1e-6)
    assert diagonal == pytest.approx(axis, abs=1e-6)


@pytest.mark.parametrize("inverted", [False, True])
def test_separated_classes_have_unit_folded_auc(inverted):
    mask = slab()
    vol = np.where(mask, 200, 20).astype(np.uint8)
    if inverted:
        vol = 255 - vol
    assert quality.outcome_separability(vol, mask)[0] == 1


def test_auc_does_not_quantize_float64_distinctions():
    mask = slab()
    # These two values collapse to one when converted to float32.
    vol = np.where(mask, 0.5 + 1e-10, 0.5)
    assert quality.outcome_separability(vol, mask)[0] == 1


@pytest.mark.parametrize("dtype", ["<u2", ">u2"])
def test_storage_scaling_makes_equivalent_uint8_and_uint16_features_match(dtype):
    small = np.random.default_rng(5).integers(0, 256, (9, 10, 11), dtype=np.uint8)
    wide = (small.astype(np.uint16) * 257).astype(dtype)
    before = small.copy()
    assert quality.predictors(small) == pytest.approx(quality.predictors(wide))
    np.testing.assert_array_equal(small, before)


def test_flat_texture_is_finite_with_explicit_undefined_gradients():
    result = quality.predictors(np.zeros((6, 6, 6), np.uint8))
    assert result == {
        "intensity_std": 0,
        "grad_median": None,
        "grad_p90_over_p50": None,
        "tensor_anisotropy": 0,
    }
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "problem", ["shape", "nan", "complex", "signed", "float_range"]
)
def test_invalid_ct_is_refused(problem):
    value = np.zeros((5, 5, 5), np.float32)
    if problem == "shape":
        value = value[0]
    elif problem == "nan":
        value[0, 0, 0] = np.nan
    elif problem == "complex":
        value = value.astype(np.complex64)
    elif problem == "signed":
        value = value.astype(np.int16)
    else:
        value[0, 0, 0] = 2
    with pytest.raises(ValueError):
        quality.predictors(value)


@pytest.mark.parametrize("problem", ["shape", "float_ids", "negative"])
def test_invalid_instance_mask_is_refused(problem):
    mask = slab().astype(np.int32)
    if problem == "shape":
        mask = mask[0]
    elif problem == "float_ids":
        mask = mask.astype(np.float32)
    else:
        mask[0, 0, 0] = -1
    with pytest.raises(ValueError, match="mask must match"):
        quality.outcome_separability(np.ones((32, 32, 32), np.uint8), mask)


def _rows(x, y):
    return [
        {"separability_auc": b, **{name: a for name in quality.FEATURES}}
        for a, b in zip(x, y, strict=True)
    ]


def test_spearman_uses_tied_ranks_and_is_row_order_invariant():
    # Average ranks [1.5,1.5,3.5,3.5] against [1,2,3,4] give 2/sqrt(5).
    rows = _rows([0, 0, 1, 1], [0.5, 0.6, 0.7, 0.8])
    a = quality.correlations(rows)
    b = quality.correlations(rows[::-1])
    for name in quality.FEATURES:
        assert a[name]["spearman"] == pytest.approx(2 / np.sqrt(5))
        assert a[name]["spearman"] == pytest.approx(b[name]["spearman"])


@pytest.mark.parametrize(
    "case", ["none", "few", "constant_predictor", "constant_outcome"]
)
def test_undefined_correlations_have_nulls_and_counts(case):
    x, y = [0, 1, 2, 3], [0.5, 0.6, 0.7, 0.8]
    if case == "none":
        x, y = [], []
    elif case == "few":
        x, y = x[:3], y[:3]
    elif case == "constant_predictor":
        x = [0] * 4
    else:
        y = [0.5] * 4
    result = quality.correlations(_rows(x, y))
    assert all(
        row["status"] == "INDETERMINATE"
        and row["pearson"] is None
        and row["spearman"] is None
        and row["n"] == len(x)
        for row in result.values()
    )
    json.dumps(result, allow_nan=False)


def _cube(root, name, vol=None, mask=None):
    folder = root / name
    folder.mkdir(parents=True)
    if vol is not None:
        nrrd.write(str(folder / f"{name}_volume.nrrd"), vol, index_order="F")
    if mask is not None:
        nrrd.write(str(folder / f"{name}_mask.nrrd"), mask, index_order="F")
    return folder


def test_oversized_headers_fail_before_decoding_either_payload(tmp_path, monkeypatch):
    _cube(tmp_path, "000", np.zeros((4, 4, 4), np.uint8), np.zeros((4, 4, 4), np.uint8))
    monkeypatch.setattr(nrrd, "read", lambda *a, **k: pytest.fail("payload decoded"))
    report = quality.build_report(tmp_path, max_voxels=1)
    assert report["status"] == "FAILED"
    assert report["counts"]["failed"] == 1
    assert "max_voxels=1" in report["cubes"][0]["reason"]


def test_header_shape_mismatch_fails_before_payloads(tmp_path, monkeypatch):
    _cube(tmp_path, "000", np.zeros((4, 4, 4), np.uint8), np.zeros((5, 4, 4), np.uint8))
    monkeypatch.setattr(nrrd, "read", lambda *a, **k: pytest.fail("payload decoded"))
    report = quality.build_report(tmp_path)
    assert report["status"] == "FAILED"
    assert "header shapes must match" in report["cubes"][0]["reason"]


def test_nrrd_declared_channel_axis_is_not_treated_as_spatial(tmp_path, monkeypatch):
    folder = _cube(tmp_path, "000", mask=np.zeros((3, 8, 8), np.uint8))
    nrrd.write(
        str(folder / "000_volume.nrrd"),
        np.zeros((3, 8, 8), np.uint8),
        header={"kinds": ["vector", "domain", "domain"]},
    )
    monkeypatch.setattr(nrrd, "read", lambda *a, **k: pytest.fail("payload decoded"))
    report = quality.build_report(tmp_path)
    assert report["status"] == "FAILED"
    assert "axes must be spatial" in report["cubes"][0]["reason"]


def test_all_insufficient_cubes_are_reported_without_empty_reduction(tmp_path):
    for name in ("000", "001", "002", "003"):
        _cube(
            tmp_path, name, np.zeros((6, 6, 6), np.uint8), np.zeros((6, 6, 6), np.uint8)
        )
    report = quality.build_report(tmp_path)
    assert report["status"] == "INDETERMINATE"
    assert report["counts"] == {
        "requested": 4,
        "measured": 0,
        "indeterminate": 4,
        "failed": 0,
    }
    assert report["auc_summary"] is None
    assert all(row["separability_auc"] is None for row in report["cubes"])
    json.dumps(report, allow_nan=False)


def test_failed_cube_does_not_erase_other_cube_results(tmp_path):
    _cube(tmp_path, "000", np.zeros((6, 6, 6), np.uint8), np.zeros((6, 6, 6), np.uint8))
    _cube(tmp_path, "001", np.zeros((6, 6, 6), np.uint8))
    report = quality.build_report(tmp_path)
    assert report["status"] == "FAILED"
    assert [row["status"] for row in report["cubes"]] == ["INDETERMINATE", "FAILED"]
    assert report["counts"]["requested"] == 2


def test_real_cli_json_report_from_external_directory(tmp_path):
    data = tmp_path / "data"
    mask = slab()
    _cube(data, "000", np.where(mask, 200, 20).astype(np.uint8), mask)
    output = tmp_path / "reports" / "quality.json"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(quality.__file__).resolve()),
            "--data",
            str(data),
            "--out",
            str(output),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1  # One cube cannot establish four-cube correlations.
    report = json.loads(result.stdout, parse_constant=lambda x: pytest.fail(x))
    assert json.loads(output.read_text()) == report
    assert report["status"] == "INDETERMINATE"
    assert report["cubes"][0]["separability_auc"] == 1
    assert report["recipe"]["sampling_seed"] == 0
    assert not list(output.parent.glob(".quality-*"))


def test_four_valid_varying_cubes_produce_complete_descriptive_report(tmp_path, capsys):
    data = tmp_path / "data"
    mask = slab()
    for index, contrast in enumerate([0.0, 0.02, 0.08, 0.2]):
        rng = np.random.default_rng(index)
        vol = np.clip(
            rng.normal(0.4, 0.05, mask.shape) + contrast * (mask > 0), 0, 1
        ).astype(np.float32)
        _cube(data, f"00{index}", vol, mask)
    assert quality.main(["--data", str(data)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "MEASURED"
    assert report["counts"] == {
        "requested": 4,
        "measured": 4,
        "indeterminate": 0,
        "failed": 0,
    }
    assert report["auc_summary"]["min"] < report["auc_summary"]["max"]
    assert all(
        value["status"] == "MEASURED" and value["n"] == 4
        for value in report["correlations"].values()
    )


@pytest.mark.parametrize("kind", ["existing", "broken_symlink", "inside_inputs"])
def test_report_destination_is_checked_before_analysis(tmp_path, monkeypatch, kind):
    data = tmp_path / "data"
    data.mkdir()
    output = tmp_path / "report.json"
    if kind == "existing":
        output.write_text("previous report")
    elif kind == "broken_symlink":
        output.symlink_to(tmp_path / "missing")
    else:
        output = data / "report.json"
    monkeypatch.setattr(
        quality, "build_report", lambda *a, **k: pytest.fail("analysis ran")
    )
    assert quality.main(["--data", str(data), "--out", str(output)]) == 1
    if kind == "existing":
        assert output.read_text() == "previous report"


def test_report_cannot_be_published_inside_an_external_cube_alias(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    cube = _cube(
        tmp_path / "external",
        "000",
        np.zeros((6, 6, 6), np.uint8),
        np.zeros((6, 6, 6), np.uint8),
    )
    (data / "000").symlink_to(cube, target_is_directory=True)
    before = {path.name: path.read_bytes() for path in cube.iterdir()}
    output = cube / "review.json"
    assert quality.main(["--data", str(data), "--out", str(output)]) == 1
    assert {path.name: path.read_bytes() for path in cube.iterdir()} == before


def test_empty_data_has_truthful_exit_and_report(tmp_path, capsys):
    assert quality.main(["--data", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "INDETERMINATE"
    assert report["counts"]["requested"] == 0


@pytest.mark.parametrize("budget", ["0", "-1"])
def test_bad_budget_is_usage_error(tmp_path, budget):
    with pytest.raises(SystemExit) as exc:
        quality.main(["--data", str(tmp_path), "--max-voxels", budget])
    assert exc.value.code == 2
