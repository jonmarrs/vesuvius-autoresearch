"""Small local fixtures for the interpolation study's evidence contracts."""

import json
import sys

import numpy as np
import pytest
import tifffile

from scripts import analyse_interp_windows as windows, compare_interp_smoke as smoke


def smoke_fixture(tmp_path, monkeypatch):
    root, full = tmp_path / "smoke", tmp_path / "full"
    full.mkdir()
    monkeypatch.setattr(smoke, "SMOKE", root)
    monkeypatch.setattr(smoke, "FULL_PR1905", full)
    for name, value in (("X0", 2), ("Y0", 1), ("W", 4), ("H", 3)):
        monkeypatch.setattr(smoke, name, value)
    for arm in "ABC":
        (root / arm).mkdir(parents=True)
        (root / f"{arm}.SAMPLER_SHA").write_text("a" * 40)
        for index in range(5):
            tifffile.imwrite(
                root / arm / f"{index:02d}.tif", np.full((3, 4), index, np.uint8)
            )
    for index in range(5):
        tifffile.imwrite(full / f"{index:02d}.tif", np.full((6, 8), index, np.uint8))
    output = tmp_path / "comparison.json"
    monkeypatch.setattr(sys, "argv", ["compare_interp_smoke.py", "--out", str(output)])
    return root, full, output


@pytest.mark.parametrize(
    "kind", ["missing", "wrong_name", "shape", "dtype", "short_full"]
)
def test_smoke_rejects_incomplete_or_misaligned_slices(tmp_path, monkeypatch, kind):
    root, full, output = smoke_fixture(tmp_path, monkeypatch)
    bad = root / "B/04.tif"
    if kind == "missing":
        bad.unlink()
    elif kind == "wrong_name":
        bad.rename(bad.with_name("05.tif"))
    elif kind == "shape":
        tifffile.imwrite(bad, np.ones((1, 4), np.uint8))
    elif kind == "dtype":
        tifffile.imwrite(bad, np.ones((3, 4), np.uint16))
    else:
        tifffile.imwrite(full / "04.tif", np.ones((3, 4), np.uint8))
    with pytest.raises((ValueError, SystemExit)):
        smoke.main()
    assert not output.exists()


def test_smoke_complete_arrays_preserve_comparison(tmp_path, monkeypatch):
    _, _, output = smoke_fixture(tmp_path, monkeypatch)
    smoke.main()
    report = json.loads(output.read_text())
    assert len(report["A_vs_B"]) == 5
    assert all(row["identical"] for row in report["B_vs_pr1905_full_window"])
    assert report["maxcomposite_A_vs_B"]["identical"]


def window_fixture(tmp_path, monkeypatch, foreground=100):
    xs = [windows.X_LO + i * 8192 for i in range(windows.N_SECTORS)]
    root = tmp_path / "windows"
    root.mkdir()
    (root / "WINDOWS").write_text("\n".join(map(str, xs)) + "\n")
    monkeypatch.setattr(windows, "OUT", root)
    monkeypatch.setattr(windows, "select_windows", lambda: xs)
    for x in xs:
        for mode in ("linear", "smooth"):
            dest = root / f"w{x}/{mode}/ink_metric"
            dest.mkdir(parents=True)
            (dest / "metrics.json").write_text(
                json.dumps(
                    {
                        "summary": {
                            "total_pixels": windows.WIDTH * windows.HEIGHT,
                            "total_fg_pixels": foreground,
                            "overall_line_score": 0.5,
                            "overall_column_score": 0.4,
                        },
                        "strips": [
                            {
                                "total_pixels": windows.WIDTH * windows.HEIGHT,
                                "fg_pixels": foreground,
                                "line_gap_count": 10,
                            }
                        ],
                    }
                )
            )
    return root, xs


def test_analysis_checks_frozen_window_selection(tmp_path, monkeypatch):
    root, xs = window_fixture(tmp_path, monkeypatch)
    (root / "WINDOWS").write_text("\n".join(map(str, xs[1:] + [xs[-1] + 8192])))
    with pytest.raises(ValueError, match="WINDOWS"):
        windows.analyse(tmp_path / "report.json")


def test_analysis_rejects_an_incomplete_selection(tmp_path, monkeypatch):
    _, xs = window_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(windows, "select_windows", lambda: xs[:-1])
    with pytest.raises(ValueError, match="8|WINDOWS"):
        windows.analyse(tmp_path / "report.json")


def test_zero_ink_baseline_is_reported_as_undefined(tmp_path, monkeypatch):
    window_fixture(tmp_path, monkeypatch, foreground=0)
    output = tmp_path / "report.json"
    assert windows.analyse(output) == 0
    report = json.loads(output.read_text())
    assert all(row["d_fg"] is None for row in report["windows"])
    assert report["summary"]["d_fg_median"] is None
    assert report["summary"]["n_fg_undefined"] == 8
    assert report["predictions_held"]["fg_abs_below_1pct_every_window"] is None


def test_positive_baselines_keep_registered_statistics(tmp_path, monkeypatch):
    root, xs = window_fixture(tmp_path, monkeypatch, foreground=1000)
    for index, x in enumerate(xs):
        path = root / f"w{x}/smooth/ink_metric/metrics.json"
        data = json.loads(path.read_text())
        foreground = 1005 if index % 2 else 995
        data["summary"]["total_fg_pixels"] = foreground
        data["strips"][0]["fg_pixels"] = foreground
        path.write_text(json.dumps(data))
    output = tmp_path / "report.json"
    windows.analyse(output)
    data = json.loads(output.read_text())
    assert data["summary"]["n_windows"] == 8
    assert data["summary"]["n_fg_undefined"] == 0
    assert data["summary"]["d_fg_pos"] == data["summary"]["d_fg_neg"] == 4
    assert data["summary"]["d_fg_range"] == pytest.approx([-0.005, 0.005])
    assert data["predictions_held"]["fg_abs_below_1pct_every_window"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_pixels", 1),
        ("total_fg_pixels", -1),
        ("overall_line_score", float("nan")),
    ],
)
def test_analysis_rejects_invalid_scores_without_replacing_report(
    tmp_path, monkeypatch, field, value
):
    root, xs = window_fixture(tmp_path, monkeypatch)
    path = root / f"w{xs[0]}/linear/ink_metric/metrics.json"
    data = json.loads(path.read_text())
    data["summary"][field] = value
    path.write_text(json.dumps(data))
    output = tmp_path / "report.json"
    output.write_text("existing report")
    with pytest.raises(ValueError):
        windows.analyse(output)
    assert output.read_text() == "existing report"


def test_strip_builder_preserves_the_pinned_composite_recipe(tmp_path, monkeypatch):
    from PIL import Image

    monkeypatch.setattr(windows, "HEIGHT", 6)
    monkeypatch.setattr(windows, "WIDTH", 8)
    ref = tmp_path / "reference"
    (ref / "spiral-fitting").mkdir(parents=True)
    (ref / "spiral-fitting/provenance.txt").write_text("pinned scorer")
    monkeypatch.setattr(windows, "REF", ref)
    tifdir = tmp_path / "tifs"
    tifdir.mkdir()
    layers = [np.arange(48, dtype=np.uint8).reshape(6, 8) + i for i in range(5)]
    for i, layer in enumerate(layers):
        tifffile.imwrite(tifdir / f"{i:02d}.tif", layer)
    arm = tmp_path / "arm"
    windows.build_strip(arm, tifdir)
    expected = np.maximum.reduce(layers).astype(np.float32)
    expected = (np.clip(expected / np.percentile(expected, 95), 0, 1) * 255).astype(
        np.uint8
    )
    expected_file = tmp_path / "expected.jpg"
    Image.fromarray(expected).save(expected_file, quality=95)
    assert (arm / "meshes/ink/crop.jpg").read_bytes() == expected_file.read_bytes()
    assert (arm / "spiral-fitting/provenance.txt").read_text() == "pinned scorer"
