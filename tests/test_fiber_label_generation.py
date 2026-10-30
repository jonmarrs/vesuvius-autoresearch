"""Fiber-label CLI geometry, provenance and complete-run publication."""

import csv
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import tifffile
import zarr

from vesuvius_autoresearch.fibers import detection


@pytest.fixture
def generator(monkeypatch):
    # Let baseline function regressions reach the old implementation despite
    # its stale unconditional Villa import. Real CLI tests do not inject it.
    monkeypatch.setitem(
        sys.modules,
        "tools",
        SimpleNamespace(detect_vesselness=detection.detect_vesselness),
    )
    sys.modules.pop("scripts.labeling.generate_fiber_labels", None)
    return importlib.import_module("scripts.labeling.generate_fiber_labels")


@pytest.fixture
def inputs(tmp_path):
    source = tmp_path / "ct.zarr"
    values = np.random.default_rng(17).integers(0, 255, (9, 10, 11), dtype=np.uint8)
    zarr.array(values, store=str(source), chunks=(3, 4, 5), overwrite=True)
    table = tmp_path / "candidates.tsv"
    row = {
        "artifact_stem": "test",
        "local_uri": str(source),
        "z": 1,
        "y": 2,
        "x": 3,
        "width": 5,
        "height": 4,
        "review_score": 0.7,
        "scroll_id": "s1",
        "short_id": "ct",
        "division": "test",
    }
    with table.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    return source, table, tmp_path / "labels"


def args(inputs, **changes):
    _, table, output = inputs
    result = {
        "candidates": table,
        "evidence_root": output,
        "top_n": 1,
        "depth": 4,
        "threshold": 0.5,
        "use_gpu": False,
        "dry_run": False,
        "max_voxels": 128**3,
    }
    result.update(changes)
    return SimpleNamespace(**result)


def clean_cli_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["CUDA_VISIBLE_DEVICES"] = ""
    return env


def test_real_help_without_villa_or_webknossos():
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts/labeling/generate_fiber_labels.py"
    )
    run = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        env=clean_cli_env(),
        cwd=script.parent,
    )
    assert run.returncode == 0, run.stderr
    assert "--max-voxels" in run.stdout


def test_real_cpu_cli_writes_matching_scalar_tiffs_and_provenance(inputs):
    source, table, output = inputs
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts/labeling/generate_fiber_labels.py"
    )
    run = subprocess.run(
        [
            sys.executable,
            str(script),
            "--candidates",
            str(table),
            "--evidence-root",
            str(output),
            "--depth",
            "4",
            "--top-n",
            "1",
        ],
        capture_output=True,
        env=clean_cli_env(),
        cwd=table.parent,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    raw = zarr.open(str(source), mode="r")[1:5, 2:6, 3:8]
    expected = detection.detect_vesselness(raw.astype(np.float32) / 255).astype(
        np.float32
    )
    directory = output / "candidate_000"
    with tifffile.TiffFile(directory / "fiber_prob.tif") as tif:
        assert tif.series[0].axes == "ZYX"
        np.testing.assert_array_equal(tif.asarray(), expected)
    np.testing.assert_array_equal(
        tifffile.imread(directory / "fiber_label.tif"), expected >= 0.5
    )
    metadata = json.loads((directory / "fiber_labels_meta.json").read_text())
    assert metadata["evaluated_bbox_zyx"] == [1, 5, 2, 6, 3, 8]
    assert metadata["source_path"] == str(source.resolve())
    assert metadata["label_kind"] == "ct_vesselness_pseudo_label"
    assert metadata["shape_zyx"] == [4, 4, 5]
    assert (
        json.loads((directory / "candidate.json").read_text())["artifact_stem"]
        == "test"
    )
    summary = json.loads((output / "fiber_labels_summary.json").read_text())
    assert summary["complete"] is True and summary["backend"] == "numpy"
    assert summary["candidates"][0]["prob_path"] == str(directory / "fiber_prob.tif")


@pytest.mark.parametrize(
    "geometry",
    [(8, 0, 0, 4, 4, 4), (0, 8, 0, 4, 4, 4), (-1, 0, 0, 4, 4, 4), (0, 0, 0, 0, 4, 4)],
)
def test_ct_windows_are_never_silently_clipped(generator, inputs, geometry):
    with pytest.raises(ValueError):
        generator._load_ct_window(str(inputs[0]), *geometry)


def test_existing_evidence_tree_is_untouched(generator, inputs):
    output = inputs[2]
    candidate = output / "candidate_000"
    candidate.mkdir(parents=True)
    previous = candidate / "fiber_prob.tif"
    previous.write_bytes(b"previous result")
    with pytest.raises(ValueError, match="already exists"):
        generator._run_candidates_mode(args(inputs))
    assert previous.read_bytes() == b"previous result"
    assert not (candidate / "fiber_label.tif").exists()


@pytest.mark.parametrize("relation", ["same", "parent", "child", "symlink"])
def test_output_cannot_overlap_ct(generator, inputs, relation):
    source, _, output = inputs
    if relation == "same":
        output = source
    elif relation == "parent":
        output = source.parent
    elif relation == "child":
        output = source / "labels"
    else:
        output.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError):
        generator._run_candidates_mode(args(inputs, evidence_root=output))


def test_dry_run_makes_no_output_and_never_probes_gpu(generator, inputs, monkeypatch):
    monkeypatch.setattr(
        generator, "_select_backend", lambda *a: pytest.fail("probed CUDA")
    )
    assert generator._run_candidates_mode(args(inputs, dry_run=True, use_gpu=True)) == 0
    assert not inputs[2].exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"threshold": float("nan")},
        {"threshold": -0.1},
        {"threshold": 1.1},
        {"depth": 0},
        {"depth": 2},
        {"top_n": 0},
        {"max_voxels": 1},
    ],
)
def test_invalid_settings_fail_before_filtering(
    generator, inputs, monkeypatch, changes
):
    monkeypatch.setattr(
        generator, "detect_vesselness", lambda *a: pytest.fail("filtered")
    )
    with pytest.raises(ValueError):
        generator._run_candidates_mode(args(inputs, **changes))
    assert not inputs[2].exists()


@pytest.mark.parametrize("failure", ["filter", "second_tiff", "nonfinite", "shape"])
def test_failed_run_never_publishes_a_partial_directory(
    generator, inputs, monkeypatch, failure
):
    original = generator.detect_vesselness

    def filtered(data):
        if failure == "filter":
            raise RuntimeError("filter failed")
        if failure == "nonfinite":
            return np.full(data.shape, np.nan)
        if failure == "shape":
            return np.ones((3, 3, 3))
        return original(data)

    monkeypatch.setattr(generator, "detect_vesselness", filtered)
    write = tifffile.imwrite
    calls = []

    def fail_second(*a, **kw):
        calls.append(a[0])
        if failure == "second_tiff" and len(calls) == 2:
            raise OSError("second TIFF failed")
        return write(*a, **kw)

    monkeypatch.setattr(tifffile, "imwrite", fail_second)
    with pytest.raises((ValueError, OSError, RuntimeError)):
        generator._run_candidates_mode(args(inputs))
    assert not inputs[2].exists()
    assert not list(inputs[2].parent.glob(".labels-*"))


@pytest.mark.parametrize("changed", ["table", "ct"])
def test_changed_inputs_block_publication(generator, inputs, monkeypatch, changed):
    original = generator.detect_vesselness

    def filtered(data):
        result = original(data)
        if changed == "table":
            inputs[1].write_text(inputs[1].read_text() + "\n")
        else:
            source = zarr.open(str(inputs[0]), mode="r+")
            source[1, 2, 3] = (int(source[1, 2, 3]) + 1) % 256
        return result

    monkeypatch.setattr(generator, "detect_vesselness", filtered)
    with pytest.raises(ValueError, match="changed"):
        generator._run_candidates_mode(args(inputs))
    assert not inputs[2].exists()


def test_the_completion_summary_follows_every_recheck(generator, inputs, monkeypatch):
    """A run killed during its rechecks must not leave a staged summary saying
    "complete": nothing reads hidden staging directories, but nothing removes
    them either."""
    candidates = importlib.import_module("scripts.labeling.fiber_candidates")
    staged = []

    def summary_staged():
        staged.append(any(inputs[2].parent.rglob("fiber_labels_summary.json")))

    for name in ("_inspect", "file_sha256"):
        check = getattr(candidates, name)

        def recorded(*a, check=check, **kw):
            summary_staged()
            return check(*a, **kw)

        monkeypatch.setattr(candidates, name, recorded)
    generator._run_candidates_mode(args(inputs))
    assert staged and not any(staged)
    assert json.loads((inputs[2] / "fiber_labels_summary.json").read_text())["complete"]


def test_the_candidate_tsv_must_be_a_regular_file(generator, inputs):
    """Its bytes are hashed again before publication, which a pipe cannot give."""
    read, write = os.pipe()
    try:
        os.write(write, inputs[1].read_bytes())
        os.close(write)
        with pytest.raises(ValueError, match="regular file"):
            generator._run_candidates_mode(
                args(inputs, candidates=Path(f"/dev/fd/{read}"))
            )
    finally:
        os.close(read)
    assert not inputs[2].exists()


def test_all_selected_geometry_is_checked_before_backend(
    generator, inputs, monkeypatch
):
    rows = list(csv.DictReader(inputs[1].open(), delimiter="\t"))
    other = {**rows[0], "z": "100"}
    with inputs[1].open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(other), delimiter="\t")
        writer.writeheader()
        writer.writerows([rows[0], other])
    monkeypatch.setattr(
        generator, "_select_backend", lambda *a: pytest.fail("probed CUDA")
    )
    with pytest.raises(ValueError):
        generator._run_candidates_mode(args(inputs, top_n=2))
    assert not inputs[2].exists()


def tree(start, stop):
    def node(xyz):
        return SimpleNamespace(
            position=SimpleNamespace(**dict(zip(("x", "y", "z"), xyz, strict=True)))
        )

    return SimpleNamespace(edges=[(node(start), node(stop))])


def test_skeleton_bounds_follow_xyz_coordinates_and_zyx_arrays(generator):
    result = generator._fill_volume_for_tree(tree((4, 1, 1), (4, 1, 2)), (3, 4, 5))
    assert result[1, 1, 4] and result[2, 1, 4]


def test_negative_fractional_skeleton_coordinates_do_not_leak_into_zero(generator):
    result = generator._fill_volume_for_tree(
        tree((-0.2, 1, 1), (-0.1, 1, 1)), (3, 4, 5)
    )
    assert not result.any()


def test_empty_skeleton_does_not_generate_corner_fibers(generator):
    result = generator._expand_and_vesselness(np.zeros((9, 10, 11), np.uint8), 2)
    assert not result.any()


def test_many_skeleton_trees_do_not_queue_unbounded_volume_results(
    generator, monkeypatch
):
    import concurrent.futures

    outstanding = set()
    submitted = []

    class BoundedExecutor:
        def __init__(self, *, max_workers):
            self.limit = max_workers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def submit(self, *args):
            assert len(outstanding) < self.limit, "unbounded whole-volume queue"
            future = concurrent.futures.Future()
            future.set_result(
                (np.ones((3, 3, 3), np.uint16), np.zeros((3, 3, 3), np.uint16))
            )
            outstanding.add(future)
            submitted.append(future)
            return future

    original = concurrent.futures.as_completed

    def consume(futures):
        for future in original(futures):
            outstanding.remove(future)
            yield future

    monkeypatch.setattr(concurrent.futures, "ProcessPoolExecutor", BoundedExecutor)
    monkeypatch.setattr(concurrent.futures, "as_completed", consume)
    annotation = SimpleNamespace(
        skeleton=SimpleNamespace(trees=list(range(101)), groups=[])
    )
    result = generator._voxelize_skeleton(annotation, (3, 3, 3), (0, 0, 0), n_workers=2)
    assert len(submitted) == 101 and not outstanding
    np.testing.assert_array_equal(result, np.ones((3, 3, 3), np.uint8))


def test_skeleton_process_pool_preserves_overlapping_orientations(generator):
    annotation = SimpleNamespace(
        skeleton=SimpleNamespace(
            trees=[tree((0, 2, 2), (4, 2, 2)), tree((2, 2, 0), (2, 2, 4))],
            groups=[],
        )
    )
    result = generator._voxelize_skeleton(
        annotation, (5, 5, 5), (0, 0, 0), radius=0, n_workers=2
    )
    assert result.dtype == np.uint8 and result.shape == (5, 5, 5)
    assert result[2, 2, 2] == 3
    assert result[2, 2, 0] == 1 and result[0, 2, 2] == 2


@pytest.mark.parametrize(
    "changed", ["artifact_stem", "z", "width", "local_uri", "review_score"]
)
def test_malformed_selected_rows_fail_without_outputs(generator, inputs, changed):
    row = next(csv.DictReader(inputs[1].open(), delimiter="\t"))
    row[changed] = {
        "artifact_stem": "../escape",
        "z": "-1",
        "width": "4.5",
        "local_uri": "",
        "review_score": "NaN",
    }[changed]
    with inputs[1].open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    with pytest.raises(ValueError):
        generator._run_candidates_mode(args(inputs))
    assert not inputs[2].exists()


def test_duplicate_physical_windows_are_rejected(generator, inputs):
    row = next(csv.DictReader(inputs[1].open(), delimiter="\t"))
    with inputs[1].open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row), delimiter="\t")
        writer.writeheader()
        writer.writerows([row, {**row, "artifact_stem": "other"}])
    with pytest.raises(ValueError, match="duplicate physical"):
        generator._run_candidates_mode(args(inputs, top_n=2))


def test_source_header_changes_after_filtering_block_completion(
    generator, inputs, monkeypatch
):
    original = generator.detect_vesselness

    def filtered(data):
        result = original(data)
        zarr.open(str(inputs[0]), mode="r+").attrs["frame"] = "changed"
        return result

    monkeypatch.setattr(generator, "detect_vesselness", filtered)
    with pytest.raises(ValueError, match="changed"):
        generator._run_candidates_mode(args(inputs))
    assert not inputs[2].exists()


def test_gpu_allocation_failure_has_no_cpu_retry(generator, inputs, monkeypatch):
    calls = []

    def fail(data):
        calls.append(data.shape)
        raise MemoryError("GPU allocation failed")

    monkeypatch.setitem(
        sys.modules, "cupy", SimpleNamespace(asarray=fail, asnumpy=np.asarray)
    )
    monkeypatch.setattr(generator, "_select_backend", lambda *a: "cupy")
    with pytest.raises(MemoryError, match="GPU allocation"):
        generator._run_candidates_mode(args(inputs, use_gpu=True))
    assert calls == [(4, 4, 5)] and not inputs[2].exists()


def test_explicit_gpu_request_does_not_fall_back_when_cupy_is_missing(
    generator, monkeypatch
):
    monkeypatch.setitem(sys.modules, "cupy", None)
    with pytest.raises(RuntimeError, match="CuPy"):
        generator._select_backend(True)


def skeleton_args(tmp_path, **changes):
    source = tmp_path / "fibers_s5_00010z_00020y_00030x_4_v00.nml"
    source.write_text("<things/>")
    values = {
        "nml_path": source,
        "output_dir": tmp_path / "skeleton",
        "radius": 2,
        "n_workers": 1,
        "max_voxels": 128**3,
        "dry_run": False,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_skeleton_planning_needs_no_optional_import_or_output(
    generator, tmp_path, monkeypatch
):
    monkeypatch.setitem(sys.modules, "webknossos", None)
    settings = skeleton_args(tmp_path, dry_run=True)
    assert generator._run_skeleton_mode(settings) == 0
    assert not settings.output_dir.exists()


def test_skeleton_publish_has_source_hash_and_preserves_old_outputs(
    generator, tmp_path, monkeypatch
):
    settings = skeleton_args(tmp_path)
    monkeypatch.setitem(
        sys.modules,
        "webknossos",
        SimpleNamespace(Annotation=SimpleNamespace(load=lambda *a: object())),
    )
    labels = np.zeros((4, 4, 4), np.uint8)
    labels[1, 1, 1] = 2
    monkeypatch.setattr(generator, "_voxelize_skeleton", lambda *a, **kw: labels)
    assert generator._run_skeleton_mode(settings) == 0
    np.testing.assert_array_equal(
        tifffile.imread(settings.output_dir / "labels.tif"), labels
    )
    meta = json.loads((settings.output_dir / "labels_meta.json").read_text())
    assert meta["origin_zyx"] == [10, 20, 30] and meta["source_nml_sha256"]
    before = (settings.output_dir / "labels.tif").read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        generator._run_skeleton_mode(settings)
    assert (settings.output_dir / "labels.tif").read_bytes() == before


@pytest.mark.parametrize("failure", ["serialization", "source_change", "bad_labels"])
def test_failed_skeleton_outputs_are_not_published(
    generator, tmp_path, monkeypatch, failure
):
    settings = skeleton_args(tmp_path)
    monkeypatch.setitem(
        sys.modules,
        "webknossos",
        SimpleNamespace(Annotation=SimpleNamespace(load=lambda *a: object())),
    )

    def voxelize(*a, **kw):
        if failure == "source_change":
            settings.nml_path.write_text("changed")
        return np.full((4, 4, 4), 9 if failure == "bad_labels" else 1, np.uint8)

    monkeypatch.setattr(generator, "_voxelize_skeleton", voxelize)
    if failure == "serialization":

        def fail(*a, **kw):
            raise OSError("disk error")

        monkeypatch.setattr(tifffile, "imwrite", fail)
    with pytest.raises((ValueError, OSError)):
        generator._run_skeleton_mode(settings)
    assert not settings.output_dir.exists()
