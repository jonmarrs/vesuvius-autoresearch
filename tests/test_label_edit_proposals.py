"""Boundaries for reviewable annotation edits, not a label-quality benchmark."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts import label_edit_proposals as proposals
from scripts.training.input_paths import validation_label_path

ROOT = Path(__file__).resolve().parents[1]


def fixture(tmp_path, values=None):
    directory = tmp_path / "fragment"
    directory.mkdir()
    if values is None:
        values = np.zeros((16, 16), np.uint8)
        values[3:13, 3:13] = 255
        values[6:8, 6:8] = 0
    path = directory / "inklabels.png"
    Image.fromarray(values).save(path)
    return path


def read(path):
    with Image.open(path) as image:
        return np.asarray(image).copy()


def snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def test_bundle_is_reviewable_bound_to_sources_and_never_auto_adopted(tmp_path):
    source = fixture(tmp_path)
    original = source.read_bytes()
    preferred = validation_label_path(str(source.parent / "surface_volume.zarr"))
    out = tmp_path / "proposal"
    report = proposals.create_proposal(source, out)
    assert report == json.loads((out / "proposal.json").read_text())
    assert report["status"] == "PROPOSAL_ONLY"
    assert report["approved"] is False and report["training_ready"] is False
    assert report["annotation_quality_verified"] is False
    assert report["ct_alignment_verified"] is False
    assert report["counts"]["added_pixels"] == 4
    assert report["counts"]["removed_pixels"] == 0
    assert report["counts"]["selected_holes"] == [
        {"pixels": 4, "bbox_yx": [6, 8, 6, 8]}
    ]
    expected = read(source).astype(bool)
    added = read(out / "added.png").astype(bool)
    assert np.array_equal(read(out / "proposed.png") > 0, expected | added)
    assert not np.any(added & expected)
    preview = read(out / "preview.png")
    assert preview.shape == (16, 16, 3)
    assert np.all(preview[added] == [255, 128, 0])
    assert (out / "sources/input.png").read_bytes() == original == source.read_bytes()
    for name, record in report["artifacts"].items():
        data = (out / name).read_bytes()
        assert record == {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    assert not any(name.startswith("inklabels") for name in report["artifacts"])
    assert "letter counters" in (out / "review.md").read_text()
    assert (
        validation_label_path(str(source.parent / "surface_volume.zarr")) == preferred
    )
    assert sorted(p.name for p in source.parent.iterdir()) == ["inklabels.png"]


def test_disconnected_ink_marks_do_not_turn_central_background_into_ink(tmp_path):
    values = np.zeros((64, 64), np.uint8)
    for y, x in [(20, 20), (20, 42), (42, 20), (42, 42)]:
        values[y : y + 2, x : x + 2] = 255
    source = fixture(tmp_path, values)
    report = proposals.create_proposal(
        source, tmp_path / "proposal", max_hole_pixels=4096
    )
    assert report["counts"]["original_positive_pixels"] == 16
    assert report["counts"]["added_pixels"] == 0
    assert np.array_equal(read(tmp_path / "proposal/proposed.png"), values)


@pytest.mark.parametrize("encoding", ["binary", "one_bit", "gray"])
def test_all_documented_binary_png_encodings_remain_binary(tmp_path, encoding):
    values = np.zeros((9, 9), np.uint8)
    values[2:7, 2:7] = 1
    values[4, 4] = 0
    if encoding == "one_bit":
        values = values.astype(bool)
    elif encoding == "gray":
        values *= 255
    source = fixture(tmp_path, values)
    report = proposals.create_proposal(source, tmp_path / "proposal")
    assert report["counts"]["added_pixels"] == 1
    assert set(np.unique(read(tmp_path / "proposal/proposed.png"))) == {0, 255}


@pytest.mark.parametrize("value", [0, 255])
def test_constant_masks_do_not_acquire_new_regions(tmp_path, value):
    source = fixture(tmp_path, np.full((8, 8), value, np.uint8))
    report = proposals.create_proposal(source, tmp_path / "proposal")
    assert report["counts"]["added_pixels"] == 0


@pytest.mark.parametrize("connectivity,expected", [(4, 1), (8, 0)])
def test_background_connectivity_is_explicit(tmp_path, connectivity, expected):
    values = np.full((5, 5), 255, np.uint8)
    values[0, 0] = values[1, 1] = 0
    source = fixture(tmp_path, values)
    report = proposals.create_proposal(
        source, tmp_path / "proposal", connectivity=connectivity
    )
    assert report["counts"]["added_pixels"] == expected


def test_region_mask_never_clips_a_partly_unknown_hole(tmp_path):
    source = fixture(tmp_path)
    region = np.full((16, 16), 255, np.uint8)
    region[6, 6] = 0
    path = source.parent / "eligible.png"
    Image.fromarray(region).save(path)
    report = proposals.create_proposal(source, tmp_path / "proposal", region_mask=path)
    assert report["counts"]["added_pixels"] == 0
    assert report["counts"]["outside_region_holes"] == 1
    assert (tmp_path / "proposal/sources/region.png").read_bytes() == path.read_bytes()


def test_holes_larger_than_limit_are_preserved(tmp_path):
    source = fixture(tmp_path)
    report = proposals.create_proposal(source, tmp_path / "proposal", max_hole_pixels=3)
    assert report["counts"]["added_pixels"] == 0
    assert report["counts"]["oversize_holes"] == 1


def test_total_change_budget_blocks_publication(tmp_path):
    source = fixture(tmp_path)
    with pytest.raises(ValueError, match="max_added_pixels"):
        proposals.create_proposal(source, tmp_path / "proposal", max_added_pixels=3)
    assert not (tmp_path / "proposal").exists()


def test_number_of_selected_holes_is_bounded(tmp_path):
    values = np.full((40, 40), 255, np.uint8)
    values[1:39:2, 1:39:2] = 0
    source = fixture(tmp_path, values)
    with pytest.raises(ValueError, match="256 holes"):
        proposals.create_proposal(source, tmp_path / "proposal")
    assert not (tmp_path / "proposal").exists()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_hole_pixels": 0},
        {"max_added_pixels": -1},
        {"connectivity": True},
        {"connectivity": 6},
        {"max_pixels": 2048**2 + 1},
        {"max_pixels": 0},
        {"max_added_pixels": float("nan")},
        {"max_hole_pixels": 2.5},
    ],
)
def test_bad_settings_fail_before_reading_missing_inputs(tmp_path, kwargs):
    with pytest.raises(ValueError):
        proposals.create_proposal(
            tmp_path / "missing.png", tmp_path / "proposal", **kwargs
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["gray", "mixed", "rgb", "uint16", "corrupt"])
def test_ambiguous_input_is_not_silently_binarized(tmp_path, kind):
    values = np.zeros((9, 9), np.uint8)
    if kind == "gray":
        values[2, 2] = 128
    elif kind == "mixed":
        values[2, 2], values[3, 3] = 1, 255
    elif kind == "rgb":
        values = np.zeros((9, 9, 3), np.uint8)
    elif kind == "uint16":
        values = values.astype(np.uint16)
    source = fixture(tmp_path, values)
    if kind == "corrupt":
        source.write_bytes(b"not a PNG")
    with pytest.raises(ValueError):
        proposals.create_proposal(source, tmp_path / "proposal")
    assert not (tmp_path / "proposal").exists()


def test_over_budget_image_is_rejected(tmp_path):
    source = fixture(tmp_path)
    with pytest.raises(ValueError):
        proposals.create_proposal(
            source, tmp_path / "proposal", max_pixels=64, max_added_pixels=64
        )
    assert not (tmp_path / "proposal").exists()


@pytest.mark.parametrize(
    "kind", ["animated", "transparent", "oversize_bytes", "symlink"]
)
def test_hidden_frames_transparency_oversize_files_and_links_are_rejected(
    tmp_path, kind
):
    source = fixture(tmp_path)
    if kind == "animated":
        image = Image.fromarray(read(source))
        image.save(
            source,
            save_all=True,
            append_images=[Image.fromarray(np.zeros((16, 16), np.uint8))],
            duration=100,
        )
    elif kind == "transparent":
        Image.fromarray(read(source)).save(source, transparency=0)
    elif kind == "oversize_bytes":
        with source.open("ab") as stream:
            stream.write(b"0" * (16 * 1024 * 1024))
    else:
        target = source.with_name("real.png")
        source.rename(target)
        source.symlink_to(target)
    with pytest.raises(ValueError):
        proposals.create_proposal(source, tmp_path / "proposal")
    assert not (tmp_path / "proposal").exists()


@pytest.mark.parametrize("kind", ["empty", "wrong_shape"])
def test_bad_region_is_rejected(tmp_path, kind):
    source = fixture(tmp_path)
    region = source.parent / "region.png"
    Image.fromarray(np.zeros((16, 16) if kind == "empty" else (8, 8), np.uint8)).save(
        region
    )
    with pytest.raises(ValueError):
        proposals.create_proposal(source, tmp_path / "proposal", region_mask=region)


@pytest.mark.parametrize(
    "kind", ["existing", "source", "inside_source", "image_name", "symlink"]
)
def test_destination_cannot_overwrite_or_become_an_auto_preferred_label(tmp_path, kind):
    source = fixture(tmp_path)
    out = tmp_path / "proposal"
    if kind == "existing":
        out.mkdir()
        (out / "user.txt").write_text("keep")
    elif kind == "source":
        out = source
    elif kind == "inside_source":
        out = source.parent / "inklabels_refined.png"
    elif kind == "image_name":
        out = tmp_path / "filled.png"
    elif kind == "symlink":
        out.symlink_to(tmp_path / "missing")
    before = snapshot(tmp_path)
    with pytest.raises(ValueError):
        proposals.create_proposal(source, out)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("which", ["source", "region", "code", "output"])
def test_source_or_artifact_mutation_prevents_a_completion_report(
    tmp_path, monkeypatch, which
):
    source = fixture(tmp_path)
    region = source.parent / "region.png"
    Image.fromarray(np.full((16, 16), 255, np.uint8)).save(region)
    real = proposals.verify_png_source
    staged_reports = []

    def verify(record):
        staged_reports.extend(tmp_path.glob(".proposal-*/new.zarr/proposal.json"))
        if which == "source" and record["path"] == str(source):
            source.write_bytes(b"changed")
        if which == "region" and record["path"] == str(region):
            region.write_bytes(b"changed")
        if which == "output":
            next(tmp_path.glob(".proposal-*/new.zarr/proposed.png")).write_bytes(
                b"changed"
            )
        return real(record)

    monkeypatch.setattr(proposals, "verify_png_source", verify)
    if which == "code":

        def changed(self):
            raise ValueError("code changed")

        monkeypatch.setattr(proposals.Snapshot, "verify", changed)
    with pytest.raises(ValueError, match="changed"):
        proposals.create_proposal(source, tmp_path / "proposal", region_mask=region)
    assert not staged_reports
    assert not (tmp_path / "proposal").exists()
    assert not list(tmp_path.glob(".proposal-*"))


def test_image_write_failure_does_not_report_success(tmp_path, monkeypatch):
    source = fixture(tmp_path)

    def fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Image.Image, "save", fail)
    from scripts.preprocess_labels import main

    assert main(["--input", str(source), "--out", str(tmp_path / "proposal")]) == 1
    assert not (tmp_path / "proposal").exists()


def test_dry_run_computes_actual_counts_and_writes_no_bundle(tmp_path):
    source = fixture(tmp_path)
    before = snapshot(tmp_path)
    report = proposals.create_proposal(
        source, tmp_path / "new" / "proposal", dry_run=True
    )
    assert report["status"] == "DRY_RUN" and report["counts"]["added_pixels"] == 4
    assert report["artifacts"] == {}
    assert snapshot(tmp_path) == before and not (tmp_path / "new").exists()


@pytest.mark.parametrize("script", ["preprocess_labels.py", "refine_labels_villa.py"])
def test_standalone_help_and_dry_run_work_without_training_or_villa_imports(
    tmp_path, script
):
    source = fixture(tmp_path)
    code = """
import builtins, runpy, sys
old = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'pytorch_lightning', 'wandb', 'vesuvius'}:
        raise RuntimeError('unexpected training or Villa import: ' + name)
    return old(name, *args, **kwargs)
builtins.__import__ = guarded
script = sys.argv[1]; sys.argv = sys.argv[1:]
runpy.run_path(script, run_name='__main__')
"""
    command = [sys.executable, "-B", "-c", code, str(ROOT / "scripts" / script)]
    help_run = subprocess.run(
        command + ["--help"], cwd=tmp_path, capture_output=True, text=True, timeout=30
    )
    assert help_run.returncode == 0, help_run.stderr
    run = subprocess.run(
        command
        + ["--input", str(source), "--out", str(tmp_path / "proposal"), "--dry-run"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["counts"]["added_pixels"] == 4
    assert not (tmp_path / "proposal").exists()
    run = subprocess.run(
        command + ["--input", str(source), "--out", str(tmp_path / "proposal")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stderr
    assert "PROPOSAL_ONLY" in run.stdout
    assert (
        json.loads((tmp_path / "proposal/proposal.json").read_text())["counts"][
            "added_pixels"
        ]
        == 4
    )


@pytest.mark.parametrize(
    "flag",
    [
        "--in_place",
        "--in-place",
        "--labels_dir=/missing",
        "--output_dir",
        "--sigma_frangi",
        "--dry_run",
    ],
)
def test_retired_bulk_and_in_place_flags_cannot_write(flag, tmp_path, capsys):
    from scripts.refine_labels_villa import main

    assert main([flag]) == 2
    assert "retired" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "flag", ["--alpha", "--fill-value", "--skip-inner", "--skip-outer"]
)
def test_spiral_flags_are_rejected_with_migration_guidance(flag, tmp_path, capsys):
    from scripts.preprocess_labels import main

    args = ["--input", "/missing", "--out", str(tmp_path / "proposal"), flag]
    if flag in {"--alpha", "--fill-value"}:
        args.append("0.5")
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2 and "retired" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
