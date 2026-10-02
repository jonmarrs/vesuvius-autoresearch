"""A completed research stage requires coherent outputs, not just a filename."""

import json

import pytest

from repro.spiral_render.artifacts import validate_meshes, validate_metrics


def metrics(foreground=0):
    return {
        "summary": {"total_pixels": 30, "total_fg_pixels": foreground},
        "strips": [
            {"total_pixels": 10, "fg_pixels": foreground},
            {"total_pixels": 20, "fg_pixels": 0},
        ],
    }


@pytest.mark.parametrize("foreground", [0, 5])
def test_metrics_accepts_coherent_zero_and_positive_ink(tmp_path, foreground):
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(metrics(foreground)))
    validate_metrics(path)


@pytest.mark.parametrize("change", [
    lambda m: m.update(strips=[]),
    lambda m: m["summary"].update(total_fg_pixels=31),
    lambda m: m["summary"].update(total_pixels=0),
    lambda m: m["summary"].update(total_pixels=True),
    lambda m: m["summary"].update(total_pixels=float("nan")),
    lambda m: m["summary"].update(total_fg_pixels=1),
    lambda m: m["strips"][0].update(fg_pixels=-1),
    lambda m: m["strips"][0].update(total_pixels=11),
])
def test_metrics_rejects_incomplete_or_inconsistent_counts(tmp_path, change):
    data = metrics()
    change(data)
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        validate_metrics(path)


def test_source_can_include_extra_windings_but_workdir_cannot(tmp_path):
    for winding in (119, 120, 121):
        (tmp_path / f"w{winding}_spliced_mesh").mkdir()
    validate_meshes(tmp_path, 120, 121)
    with pytest.raises(ValueError, match="unexpected winding"):
        validate_meshes(tmp_path, 120, 121, exact=True)


def test_duplicate_meshes_do_not_substitute_for_missing_windings(tmp_path):
    (tmp_path / "w120_spliced_first").mkdir()
    (tmp_path / "w120_spliced_second").mkdir()
    with pytest.raises(ValueError, match="120, 121"):
        validate_meshes(tmp_path, 120, 121)


def test_regular_files_are_not_mesh_directories(tmp_path):
    (tmp_path / "w120_spliced_mesh").touch()
    with pytest.raises(ValueError, match="120"):
        validate_meshes(tmp_path, 120, 120)
