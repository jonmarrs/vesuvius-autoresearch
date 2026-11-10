"""Header and pixel checks for a surface-volume pyramid that dropped depth.

The shapes in the published-metadata cases are the ones reported for the public
ink volumes (level 2 keeping 17 of 65 slices at z-scale 1, against a level that
declares z-scale 4). These tests do not fetch those volumes.
"""

import json
from pathlib import Path

import numpy as np
import pytest
import zarr

from repro.sota_data.pyramid_depth import (
    assess_levels,
    content_agreement,
    main,
    successive_half_depth,
)

AXES = [
    {"name": "z", "type": "space", "unit": "micrometer"},
    {"name": "y", "type": "space", "unit": "micrometer"},
    {"name": "x", "type": "space", "unit": "micrometer"},
]


def _levels(*rows):
    return [
        {"path": path, "shape": shape, "scale": scale} for path, shape, scale in rows
    ]


def test_successive_halving_of_a_65_slice_render():
    depth = 65
    assert [successive_half_depth(depth, step) for step in range(6)] == [
        65,
        33,
        17,
        9,
        5,
        3,
    ]


def test_unchanged_z_scale_with_the_short_depths_is_truncated():
    rows = [("0", [65, 8, 8], [1, 1, 1])]
    for step, depth in enumerate((33, 17, 9, 5, 3), start=1):
        rows.append((str(step), [depth, 8, 8], [1, 2**step, 2**step]))
    records = {record["path"]: record for record in assess_levels(_levels(*rows))}
    assert records["0"]["status"] == "full_depth"
    for path in ("1", "2", "3", "4", "5"):
        assert records[path]["status"] == "truncated"
        assert records[path]["depth_matches_successive_xy_halving"] is True
    assert "successive ceil-half" in records["2"]["reason"]


def test_shapes_reported_for_a_17_of_65_level_are_truncated():
    records = assess_levels(
        _levels(
            ("0", [65, 15872, 18944], [1, 1, 1]),
            ("2", [17, 3968, 4736], [1, 4, 4]),
        )
    )
    level2 = records[1]
    assert level2["status"] == "truncated"
    assert level2["z_scale_ratio"] == 1
    assert level2["shape_zyx"] == [17, 3968, 4736]
    assert level2["depth_matches_successive_xy_halving"] is True


def test_same_short_depth_with_z_scale_4_is_pooled():
    records = assess_levels(
        _levels(
            ("0", [65, 22640, 20000], [1, 1, 1]),
            ("2", [17, 5660, 5000], [4, 4, 4]),
        )
    )
    level2 = records[1]
    assert level2["status"] == "depth_pooled"
    assert level2["expected_depth_at_z_scale"] == pytest.approx(16.25)


def test_level_5_within_one_voxel_of_depth_over_32_is_pooled():
    records = assess_levels(
        _levels(
            ("0", [65, 32, 32], [1, 1, 1]),
            ("5", [3, 1, 1], [32, 32, 32]),
        )
    )
    assert records[1]["status"] == "depth_pooled"


def test_level_5_two_voxels_off_its_z_scale_is_inconsistent():
    records = assess_levels(
        _levels(
            ("0", [65, 32, 32], [1, 1, 1]),
            ("5", [5, 1, 1], [32, 32, 32]),
        )
    )
    assert records[1]["status"] == "inconsistent"


def test_full_depth_at_every_level_is_not_truncation():
    records = assess_levels(
        _levels(
            ("0", [65, 64, 64], [4.681, 4.681, 4.681]),
            ("1", [65, 32, 32], [4.681, 9.362, 9.362]),
            ("2", [65, 16, 16], [4.681, 18.724, 18.724]),
        )
    )
    assert [record["status"] for record in records] == [
        "full_depth",
        "full_depth",
        "full_depth",
    ]


def test_one_missing_slice_at_z_scale_1_is_still_truncated():
    records = assess_levels(
        _levels(
            ("0", [65, 8, 8], [1, 1, 1]),
            ("1", [64, 4, 4], [1, 2, 2]),
        )
    )
    assert records[1]["status"] == "truncated"
    assert records[1]["depth_matches_successive_xy_halving"] is False


def test_a_deeper_level_than_its_reference_is_inconsistent():
    records = assess_levels(
        _levels(
            ("0", [65, 8, 8], [1, 1, 1]),
            ("1", [66, 4, 4], [1, 2, 2]),
        )
    )
    assert records[1]["status"] == "inconsistent"


@pytest.mark.parametrize(
    "levels, message",
    [
        ([], "no level 0"),
        (
            [
                {"path": "0", "shape": [4, 4, 4], "scale": [1, 1, 1]},
                {"path": "0", "shape": [4, 4, 4], "scale": [1, 1, 1]},
            ],
            "duplicate",
        ),
        ([{"path": "0", "shape": [4, 4, True], "scale": [1, 1, 1]}], "positive"),
        ([{"path": "0", "shape": [4, 4, 4], "scale": [1, 1, 0]}], "positive"),
    ],
)
def test_level_tables_reject_unusable_inputs(levels, message):
    with pytest.raises(ValueError, match=message):
        assess_levels(levels)


def _pattern(depth, height, width):
    y = np.arange(height, dtype=np.float64)[:, None]
    x = np.arange(width, dtype=np.float64)[None, :]
    volume = np.empty((depth, height, width), np.float64)
    for index in range(depth):
        volume[index] = np.sin((index + 1) * y / 3.0) + np.cos((index + 2) * x / 2.0)
        volume[index, :, index % width] += 10 + index
    return volume


def _xy_pool(volume, factor):
    depth, height, width = volume.shape
    return volume.reshape(
        depth, height // factor, factor, width // factor, factor
    ).mean(axis=(2, 4))


def test_slice_copies_and_depth_pools_are_separated():
    level0 = _pattern(16, 32, 32)
    copied = _xy_pool(level0[:4], 4)
    pooled = np.stack(
        [
            _xy_pool(level0[index * 4 : (index + 1) * 4], 4).mean(axis=0)
            for index in range(4)
        ]
    )
    copied_report = content_agreement(level0, copied, 4)
    pooled_report = content_agreement(level0, pooled, 4)
    assert copied_report["verdict"] == "slice_indexed"
    assert copied_report["median_r_slice_indexed"] > 0.99
    assert copied_report["median_r_depth_pooled"] < 0.4
    assert pooled_report["verdict"] == "depth_pooled"
    assert pooled_report["median_r_depth_pooled"] > 0.99
    assert pooled_report["median_r_slice_indexed"] < 0.4


def test_rounding_the_pool_to_integers_still_reads_as_slice_copies():
    level0 = _pattern(8, 16, 16)
    copied = np.rint(_xy_pool(level0[:4], 2))
    report = content_agreement(level0, copied, 2)
    assert report["verdict"] == "slice_indexed"
    assert report["median_r_slice_indexed"] >= 0.7


def test_a_depth_invariant_window_does_not_pick_a_verdict():
    plane = _pattern(1, 16, 16)
    level0 = np.repeat(plane, 8, axis=0)
    coarse = _xy_pool(level0, 2)[:4]
    report = content_agreement(level0, coarse, 2)
    assert report["verdict"] == "ambiguous"
    assert report["median_r_slice_indexed"] > 0.99
    assert report["median_r_depth_pooled"] > 0.99


def test_content_agreement_rejects_a_spatial_mismatch():
    with pytest.raises(ValueError, match="pooling factor"):
        content_agreement(np.zeros((4, 6, 6)), np.zeros((2, 2, 2)), 2)


def _write_headers(root: Path, rows, axes=None):
    root.mkdir()
    datasets = []
    for path, shape, scale in rows:
        level = root / path
        level.mkdir()
        (level / ".zarray").write_text(
            json.dumps(
                {
                    "chunks": [min(4, value) for value in shape],
                    "compressor": None,
                    "dtype": "<f4",
                    "fill_value": 0.0,
                    "filters": None,
                    "order": "C",
                    "shape": list(shape),
                    "zarr_format": 2,
                    "dimension_separator": ".",
                }
            ),
            encoding="utf-8",
        )
        datasets.append(
            {
                "path": path,
                "coordinateTransformations": [{"type": "scale", "scale": list(scale)}],
            }
        )
    (root / ".zattrs").write_text(
        json.dumps(
            {
                "multiscales": [
                    {"axes": axes if axes is not None else AXES, "datasets": datasets}
                ]
            }
        ),
        encoding="utf-8",
    )


def _write_arrays(root: Path, arrays):
    group = zarr.open_group(str(root), mode="w")
    datasets = []
    for path, array, scale in arrays:
        group.create_dataset(path, data=array, chunks=(4, 8, 8))
        datasets.append(
            {
                "path": path,
                "coordinateTransformations": [
                    {"type": "scale", "scale": [float(v) for v in scale]}
                ],
            }
        )
    group.attrs["multiscales"] = [{"axes": AXES, "datasets": datasets}]


def test_cli_flags_truncated_headers_and_accepts_pooled_ones(tmp_path, capsys):
    truncated = tmp_path / "truncated.zarr"
    _write_headers(
        truncated,
        [("0", [65, 8, 8], [1, 1, 1]), ("2", [17, 2, 2], [1, 4, 4])],
    )
    assert main([str(truncated), "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
    assert report["levels"][1]["status"] == "truncated"
    assert report["usable_levels"] == ["0"]

    pooled = tmp_path / "pooled.zarr"
    _write_headers(
        pooled,
        [("0", [65, 8, 8], [1, 1, 1]), ("2", [17, 2, 2], [4, 4, 4])],
    )
    assert main([str(pooled)]) == 0
    text = capsys.readouterr().out
    assert "level 2: shape [17,2,2] z-scale 4 depth_pooled" in text
    assert " truncated" not in text


def test_cli_compares_slice_copies_and_a_real_depth_pool(tmp_path, capsys):
    level0 = _pattern(16, 32, 32)
    copied = _xy_pool(level0[:4], 4).astype(np.float32)
    pooled = np.stack(
        [
            _xy_pool(level0[index * 4 : (index + 1) * 4], 4).mean(axis=0)
            for index in range(4)
        ]
    ).astype(np.float32)
    short = tmp_path / "short.zarr"
    _write_arrays(
        short,
        [
            ("0", level0.astype(np.float32), [1, 1, 1]),
            ("2", copied, [1, 4, 4]),
        ],
    )
    assert (
        main(
            [
                str(short),
                "--json",
                "--compare",
                "2",
                "--origin",
                "0",
                "0",
                "--size",
                "32",
                "32",
            ]
        )
        == 1
    )
    report = json.loads(capsys.readouterr().out)
    assert report["content"]["verdict"] == "slice_indexed"
    assert report["content"]["agrees_with_metadata"] is False

    full = tmp_path / "pooled.zarr"
    _write_arrays(
        full,
        [
            ("0", level0.astype(np.float32), [1, 1, 1]),
            ("2", pooled, [4, 4, 4]),
        ],
    )
    assert (
        main(
            [
                str(full),
                "--json",
                "--compare",
                "2",
                "--origin",
                "0",
                "0",
                "--size",
                "32",
                "32",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["content"]["verdict"] == "depth_pooled"
    assert report["content"]["agrees_with_metadata"] is True


def test_cli_accepts_a_full_depth_xy_downsample(tmp_path, capsys):
    level0 = _pattern(8, 16, 16).astype(np.float32)
    coarse = _xy_pool(level0, 2).astype(np.float32)
    root = tmp_path / "full.zarr"
    _write_arrays(
        root,
        [("0", level0, [1, 1, 1]), ("1", coarse, [1, 2, 2])],
    )
    assert (
        main([str(root), "--compare", "1", "--origin", "0", "0", "--size", "16", "16"])
        == 0
    )
    assert "full_depth" in capsys.readouterr().out


def test_an_ambiguous_window_fails_the_pixel_check_only(tmp_path, capsys):
    plane = _pattern(1, 16, 16)
    level0 = np.repeat(plane, 8, axis=0).astype(np.float32)
    coarse = _xy_pool(level0, 2)[:4].astype(np.float32)
    root = tmp_path / "flat.zarr"
    _write_arrays(
        root,
        [("0", level0, [1, 1, 1]), ("1", coarse, [2, 2, 2])],
    )
    assert main([str(root)]) == 0
    capsys.readouterr()
    assert (
        main([str(root), "--compare", "1", "--origin", "0", "0", "--size", "16", "16"])
        == 1
    )
    text = capsys.readouterr().out
    assert "ambiguous" in text


def test_cli_rejects_a_partial_compare_request(tmp_path, capsys):
    root = tmp_path / "headers.zarr"
    _write_headers(root, [("0", [4, 4, 4], [1, 1, 1])])
    assert main([str(root), "--compare", "1"]) == 2
    assert "used together" in capsys.readouterr().err


def test_cli_rejects_a_window_over_the_voxel_cap(tmp_path, capsys):
    level0 = _pattern(4, 8, 8).astype(np.float32)
    coarse = _xy_pool(level0, 2).astype(np.float32)
    root = tmp_path / "small.zarr"
    _write_arrays(root, [("0", level0, [1, 1, 1]), ("1", coarse, [1, 2, 2])])
    assert (
        main(
            [
                str(root),
                "--compare",
                "1",
                "--origin",
                "0",
                "0",
                "--size",
                "8",
                "8",
                "--max-voxels",
                "10",
            ]
        )
        == 2
    )
    assert "cap" in capsys.readouterr().err


def test_cli_rejects_a_missing_chunk(tmp_path, capsys):
    level0 = _pattern(8, 16, 16).astype(np.float32)
    coarse = _xy_pool(level0[:4], 2).astype(np.float32)
    root = tmp_path / "gapped.zarr"
    _write_arrays(
        root,
        [("0", level0, [1, 1, 1]), ("1", coarse, [1, 2, 2])],
    )
    chunk = next((root / "0").glob("*.*"))
    chunk.unlink()
    assert (
        main([str(root), "--compare", "1", "--origin", "0", "0", "--size", "16", "16"])
        == 2
    )
    assert "missing" in capsys.readouterr().err


def test_cli_rejects_axes_that_are_not_zyx(tmp_path, capsys):
    root = tmp_path / "xy.zarr"
    swapped = [
        {"name": "x", "type": "space"},
        {"name": "y", "type": "space"},
        {"name": "z", "type": "space"},
    ]
    _write_headers(root, [("0", [4, 4, 4], [1, 1, 1])], axes=swapped)
    assert main([str(root)]) == 2
    assert "z, y, x" in capsys.readouterr().err


def test_cli_rejects_a_dataset_path_that_escapes_the_group(tmp_path, capsys):
    root = tmp_path / "group.zarr"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".zarray").write_text(
        json.dumps({"shape": [2, 2, 2], "zarr_format": 2}), encoding="utf-8"
    )
    (root / "0").symlink_to(outside, target_is_directory=True)
    (root / ".zattrs").write_text(
        json.dumps(
            {
                "multiscales": [
                    {
                        "axes": AXES,
                        "datasets": [
                            {
                                "path": "0",
                                "coordinateTransformations": [
                                    {"type": "scale", "scale": [1, 1, 1]}
                                ],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert main([str(root)]) == 2
    assert "escapes" in capsys.readouterr().err


def test_cli_reports_a_missing_pyramid(tmp_path, capsys):
    assert main([str(tmp_path / "missing.zarr")]) == 2
    assert "error:" in capsys.readouterr().err


def test_help_exits_cleanly():
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
