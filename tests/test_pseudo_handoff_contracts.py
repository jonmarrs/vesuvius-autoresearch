"""Pseudo-label artifacts must retain known labels, ignore semantics, and scope."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scripts import (
    generate_pseudo_labels as producer,
    iterative_pseudo_labeling as rounds,
)
from scripts.pseudo_label_quality_report import score_pseudo

REPO = Path(__file__).resolve().parents[1]


def png(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(values, dtype=np.uint8)).save(path)
    return path


def test_manual_background_and_ink_override_pseudo_and_ignore(tmp_path):
    manual, pseudo, output = [
        tmp_path / name for name in ("manual", "pseudo", "combined")
    ]
    png(manual / "segment.png", [[0, 255, 0]])
    png(manual / "segment_mask.png", [[255, 255, 0]])
    png(pseudo / "segment_pseudo.png", [[255, 128, 128]])
    rounds.combine_labels(manual, pseudo, output)
    files = list(output.glob("*.png"))
    assert len(files) == 1
    assert np.asarray(Image.open(files[0])).tolist() == [[0, 255, 128]]


def test_combined_filename_matches_actual_training_consumer(tmp_path):
    manual, pseudo, output = [
        tmp_path / name for name in ("manual", "pseudo", "combined")
    ]
    manual.mkdir()
    png(pseudo / "segment_pseudo.png", [[0, 128, 255]])
    rounds.combine_labels(manual, pseudo, output)
    assert (output / "segment_pseudo.png").is_file()


def test_manual_only_segments_are_preserved(tmp_path):
    manual, pseudo, output = [
        tmp_path / name for name in ("manual", "pseudo", "combined")
    ]
    png(manual / "segment.png", [[0, 255, 0]])
    png(manual / "segment_mask.png", [[255, 255, 0]])
    pseudo.mkdir()
    rounds.combine_labels(manual, pseudo, output)
    files = list(output.glob("*.png"))
    assert len(files) == 1
    assert np.asarray(Image.open(files[0])).tolist() == [[0, 255, 128]]


def test_bad_pseudo_values_cannot_be_published(tmp_path):
    manual, pseudo, output = [
        tmp_path / name for name in ("manual", "pseudo", "combined")
    ]
    manual.mkdir()
    png(pseudo / "segment_pseudo.png", [[0, 64, 255]])
    with pytest.raises(ValueError):
        rounds.combine_labels(manual, pseudo, output)
    assert not output.exists()


def test_all_ignore_is_unmeasured_not_chance_quality():
    result = score_pseudo(
        np.full((2, 2), 128, np.uint8), np.array([[0, 255], [255, 0]], np.uint8)
    )
    assert result["auc"] is None
    assert result["precision"] is None
    assert result["recall"] is None


def test_single_class_ground_truth_does_not_manufacture_auc():
    result = score_pseudo(np.array([[0, 255]], np.uint8), np.zeros((1, 2), np.uint8))
    assert result["auc"] is None


def test_png_producer_refuses_existing_output_before_inference(tmp_path, monkeypatch):
    destination = png(tmp_path / "output.png", [[255, 0]])
    before = destination.read_bytes()
    calls = []

    def infer(*args, **kwargs):
        calls.append(args)
        return np.array([[0, 255]], np.uint8)

    monkeypatch.setattr(producer, "_infer_region", infer)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_pseudo_labels",
            "--checkpoint",
            "missing.pt",
            "--fragment",
            "missing",
            "--region-mask",
            "missing.png",
            "--out",
            str(destination),
            "--device",
            "cpu",
        ],
    )
    with pytest.raises((ValueError, SystemExit)):
        producer.main()
    assert not calls
    assert destination.read_bytes() == before


def test_legacy_generator_entrypoint_can_show_current_help_outside_checkout(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/labeling/generate_pseudo_labels.py"),
            "--help",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--region-mask" in proc.stdout


@pytest.mark.parametrize("bad", [64, 1, 127, 129])
def test_quality_refuses_other_pseudo_encodings(bad):
    with pytest.raises(ValueError):
        score_pseudo(np.array([[bad]], np.uint8), np.array([[0]], np.uint8))


@pytest.mark.parametrize(
    "truth",
    [
        np.array([[0, 1, 255]]),
        np.array([[0, np.nan, 1]]),
        np.zeros((1, 3, 3)),
        np.array([[0, 1]], dtype=complex),
    ],
)
def test_quality_refuses_ambiguous_or_misaligned_truth(truth):
    with pytest.raises(ValueError):
        score_pseudo(np.array([[0, 128, 255]], np.uint8), truth)


def test_coverage_denominator_is_only_requested_pixels():
    pseudo = np.array([[0, 255, 128, 128]], np.uint8)
    true = np.array([[0, 255, 0, 0]], np.uint8)
    result = score_pseudo(pseudo, true, np.array([[1, 1, 0, 0]], bool))
    assert result["coverage"] == result["auc"] == 1.0
    assert result["requested_pixels"] == 2


def test_undefined_precision_is_null():
    result = score_pseudo(np.array([[0, 0]], np.uint8), np.array([[0, 1]], np.uint8))
    assert result["precision"] is None
    assert result["recall"] == 0.0
    assert result["auc"] == 0.5


@pytest.mark.parametrize(
    "mode", ["no_mask", "wrong_shape", "rgb", "orphan", "existing", "alias"]
)
def test_invalid_manual_batches_fail_without_publication(tmp_path, mode):
    manual, pseudo, output = [
        tmp_path / name for name in ("manual", "pseudo", "combined")
    ]
    png(manual / "segment.png", [[0, 255]])
    png(manual / "segment_mask.png", [[255, 255]])
    png(pseudo / "segment_pseudo.png", [[255, 0]])
    if mode == "no_mask":
        (manual / "segment_mask.png").unlink()
    elif mode == "wrong_shape":
        png(manual / "segment_mask.png", [[255]])
    elif mode == "rgb":
        Image.fromarray(np.zeros((1, 2, 3), np.uint8)).save(manual / "segment.png")
    elif mode == "orphan":
        png(manual / "unknown_mask.png", [[255]])
    elif mode == "existing":
        output.mkdir()
        (output / "keep").write_text("original")
    elif mode == "alias":
        output = manual / "combined"
    with pytest.raises((ValueError, OSError)):
        rounds.combine_labels(manual, pseudo, output)
    assert not (output / "segment_pseudo.png").exists()
    if mode == "existing":
        assert (output / "keep").read_text() == "original"
    else:
        assert not output.exists()


@pytest.fixture
def preparation(tmp_path):
    import torch
    import zarr

    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    config = {
        "architecture": "gated_unet",
        "patch_size": 16,
        "num_layers": 4,
        "base_feat": 4,
        "num_blocks": 2,
        "num_heads": 2,
        "use_ridges": False,
        "multi_task_heads": False,
    }
    model = build_inference_model(**config).eval()
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    checkpoint = tmp_path / "teacher.pt"
    torch.save({"config": config, "model_state_dict": model.state_dict()}, checkpoint)
    fragment = tmp_path / "segment"
    fragment.mkdir()
    volume = zarr.open(
        str(fragment / "surface_volume.zarr"),
        mode="w",
        shape=(12, 16, 16),
        chunks=(4, 8, 8),
        dtype="u1",
    )
    volume[:] = 64
    region = np.zeros((16, 16), np.uint8)
    region[:, :8] = 255
    png(fragment / "requested.png", region)
    known = np.zeros_like(region)
    known[0, :2] = 255
    png(fragment / "manual-known.png", known)
    manual = np.zeros_like(region)
    manual[0, 1] = 255
    png(fragment / "manual.png", manual)
    record = {
        "fragment": "segment",
        "region_mask": "segment/requested.png",
        "manual_labels": "segment/manual.png",
        "manual_mask": "segment/manual-known.png",
    }
    manifest = tmp_path / "regions.json"
    manifest.write_text(json.dumps({"regions": [record]}))
    return checkpoint, manifest, tmp_path / "batch", fragment, record


def test_dry_run_validates_without_inference_or_files(preparation, monkeypatch):
    checkpoint, manifest, output, fragment, _ = preparation

    def unexpected(*args, **kwargs):
        pytest.fail("dry run launched a process")

    monkeypatch.setattr(rounds.ProcessSupervisor, "run", unexpected)
    result = rounds.prepare_round(checkpoint, manifest, output)
    assert result["status"] == "DRY_RUN"
    assert result["training_executed"] is False
    assert not output.exists()
    assert result["commands"][0][0] == sys.executable
    assert "--region-mask" in result["commands"][0]
    assert not list(fragment.glob("*.npy"))


@pytest.mark.parametrize(
    "mode",
    [
        "empty_region",
        "grey_mask",
        "mismatch",
        "missing_manual_mask",
        "holdout",
        "duplicate",
        "oversize",
        "shallow",
        "incomplete_teacher",
        "nan_teacher",
        "source_output",
    ],
)
def test_preparation_rejects_bad_inputs_before_children(preparation, monkeypatch, mode):
    import torch
    import zarr

    checkpoint, manifest, output, fragment, record = preparation
    kwargs = {}
    if mode == "empty_region":
        png(fragment / "requested.png", np.zeros((16, 16), np.uint8))
    elif mode == "grey_mask":
        png(fragment / "requested.png", np.full((16, 16), 128))
    elif mode == "mismatch":
        png(fragment / "requested.png", np.full((16, 15), 255))
    elif mode == "missing_manual_mask":
        del record["manual_mask"]
    elif mode == "holdout":
        record["holdout_mask"] = record["region_mask"]
    elif mode == "oversize":
        kwargs["max_pixels"] = 255
    elif mode == "shallow":
        volume = zarr.open(str(fragment / "surface_volume.zarr"), mode="a")
        volume.resize((11, 16, 16))
    elif mode in {"incomplete_teacher", "nan_teacher"}:
        saved = torch.load(checkpoint, weights_only=False)
        if mode == "incomplete_teacher":
            saved["model_state_dict"].pop(next(iter(saved["model_state_dict"])))
        else:
            saved["model_state_dict"][next(iter(saved["model_state_dict"]))].fill_(
                float("nan")
            )
        torch.save(saved, checkpoint)
    elif mode == "source_output":
        output = fragment / "batch"
    manifest.write_text(
        json.dumps({"regions": [record, record] if mode == "duplicate" else [record]})
    )

    def unexpected(*args, **kwargs):
        pytest.fail("invalid inputs launched a process")

    monkeypatch.setattr(rounds.ProcessSupervisor, "run", unexpected)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        rounds.prepare_round(checkpoint, manifest, output, execute=True, **kwargs)
    assert not output.exists()


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_timeout_must_be_bounded(preparation, timeout):
    checkpoint, manifest, output, _, _ = preparation
    with pytest.raises(ValueError, match="timeout"):
        rounds.prepare_round(checkpoint, manifest, output, timeout=timeout)
    assert not output.exists()


@pytest.mark.parametrize(
    "mode",
    [
        "failed",
        "timeout",
        "interrupt",
        "malformed",
        "outside_region",
        "all_ignore",
        "changed_input",
    ],
)
def test_child_failures_never_publish_completed_batch(preparation, monkeypatch, mode):
    checkpoint, manifest, output, fragment, _ = preparation

    def child(self, command, *, timeout, check, cwd):
        path = Path(command[command.index("--out") + 1])
        if mode == "failed":
            raise subprocess.CalledProcessError(3, command)
        if mode == "timeout":
            raise subprocess.TimeoutExpired(command, timeout)
        if mode == "interrupt":
            raise KeyboardInterrupt
        values = np.full((16, 16), 128, np.uint8)
        values[:, :8] = 255
        if mode == "malformed":
            values[0, 0] = 64
        if mode == "outside_region":
            values[0, 9] = 255
        if mode == "all_ignore":
            values[:] = 128
        if mode == "changed_input":
            png(fragment / "manual.png", np.full((16, 16), 255))
        png(path, values)

    monkeypatch.setattr(rounds.ProcessSupervisor, "run", child)
    with pytest.raises(
        (
            ValueError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            KeyboardInterrupt,
        )
    ):
        rounds.prepare_round(checkpoint, manifest, output, execute=True)
    assert not output.exists()
    assert not list(output.parent.glob(".batch-*"))


def test_real_teacher_cli_publishes_manual_preserving_training_handoff(
    preparation, tmp_path
):
    checkpoint, manifest, output, fragment, _ = preparation
    # Generation is label-free: unrelated ambient fragment annotations are not
    # additional inputs and cannot alter the explicit region preparation.
    Image.fromarray(np.zeros((1, 1, 3), np.uint8)).save(fragment / "inklabels.png")
    command = [
        sys.executable,
        str(REPO / "scripts/iterative_pseudo_labeling.py"),
        "--checkpoint",
        str(checkpoint),
        "--manifest",
        str(manifest),
        "--out",
        str(output),
        "--tau-low",
        "0.1",
        "--tau-high",
        "0.4",
        "--execute",
        "--device",
        "cpu",
        "--timeout",
        "60",
    ]
    process = subprocess.run(
        command, cwd=tmp_path, capture_output=True, text=True, timeout=90
    )
    assert process.returncode == 0, process.stdout + process.stderr
    report = json.loads((output / "handoff.json").read_text())
    assert report["status"] == "PREPARED"
    assert report["training_executed"] is report["accuracy_verified"] is False
    assert report["teacher_lineage_verified"] is False
    assert report["submittable"] is None
    assert report["training_requirements"]["pseudo_label_dir"] == str(output / "labels")
    assert report["training_requirements"]["use_confidence_weight"] is True
    label = np.asarray(Image.open(output / "labels/segment_pseudo.png"))
    assert label[0, :3].tolist() == [0, 255, 255]
    assert (label[:, 8:] == 128).all()
    assert (label[1:, :8] == 255).all()
    assert not list(fragment.glob("*.npy"))
    from scripts.export_for_production import sha256_file

    assert report["input_sha256"][str(checkpoint)] == sha256_file(checkpoint)
    assert report["regions"][0]["labels_sha256"] == sha256_file(
        output / "labels/segment_pseudo.png"
    )
    # Confirm the actual dataset consumes the published 8-bit encoding.
    import torch
    from train import confidence_weight

    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    dataset = VesuviusLabeledDataset(
        str(fragment / "surface_volume.zarr"),
        str(output / "labels/segment_pseudo.png"),
        str(fragment / "requested.png"),
        16,
        12,
        cache_dir=str(output / "cache/segment"),
        jitter=False,
        strict_reads=True,
    )
    assert dataset.labels[0, 0] == 0
    assert dataset.labels[0, 1] == 1
    residual = confidence_weight(torch.tensor(dataset.labels[0, 8]))
    assert float(residual) == pytest.approx(1 / 255, abs=1e-7)


@pytest.mark.parametrize("status", ["measured", "ignore", "single_class", "malformed"])
def test_quality_cli_json_and_exit_are_truthful(tmp_path, status):
    pseudo = np.array([[0, 255]], np.uint8)
    true = np.array([[0, 255]], np.uint8)
    if status == "ignore":
        pseudo[:] = 128
    if status == "single_class":
        true[:] = 0
    if status == "malformed":
        pseudo[0, 0] = 64
    paths = [
        png(tmp_path / name, values)
        for name, values in [
            ("pseudo.png", pseudo),
            ("true.png", true),
            ("region.png", [[255, 255]]),
        ]
    ]
    process = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/pseudo_label_quality_report.py"),
            "--pseudo",
            str(paths[0]),
            "--true",
            str(paths[1]),
            "--region-mask",
            str(paths[2]),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == (0 if status == "measured" else 1)
    if status == "malformed":
        assert "pseudo labels" in process.stderr
    else:
        report = json.loads(process.stdout)
        assert report["auc"] == (1.0 if status == "measured" else None)


def test_sampler_is_actual_pinned_source_without_ml_bootstrap():
    from vesuvius_autoresearch.core.patch_catalog import (
        find_valid_patches,
        sampler_module,
    )

    module = sampler_module()
    assert (
        Path(module.__file__).resolve()
        == REPO / "villa/vesuvius/src/vesuvius/models/datasets/find_valid_patches.py"
    )
    args = {
        "label_arrays": [np.ones((16, 16), np.uint8)],
        "label_names": ["segment"],
        "patch_size": (8, 8),
        "valid_patch_find_resolution": 0,
    }
    assert find_valid_patches(**args) == module.find_valid_patches(**args)


@pytest.mark.parametrize(
    "content",
    [
        '{"regions":[],"regions":[]}',
        '{"regions":NaN}',
        '{"regions":[{"fragment":"s3://bucket/segment","region_mask":"mask.png"}]}',
        '{"regions":[{"fragment":"segment","region_mask":"mask.png","typo":true}]}',
    ],
)
def test_manifest_rejects_ambiguous_json(tmp_path, content):
    path = tmp_path / "manifest.json"
    path.write_text(content)
    with pytest.raises(ValueError):
        rounds.manifest_regions(path)


def test_later_segment_failure_rolls_back_earlier_completed_labels(
    preparation, monkeypatch
):
    import shutil

    checkpoint, manifest, output, fragment, record = preparation
    second = fragment.parent / "second"
    shutil.copytree(fragment, second)
    other_record = {
        key: str(value).replace("segment", "second") for key, value in record.items()
    }
    manifest.write_text(json.dumps({"regions": [record, other_record]}))
    completed = []

    def child(self, command, *, timeout, check, cwd):
        raw = Path(command[command.index("--out") + 1])
        if completed:
            first_label = raw.parent.parent / "labels/segment_pseudo.png"
            assert first_label.is_file()
            raise subprocess.CalledProcessError(4, command)
        values = np.full((16, 16), 128, np.uint8)
        values[:, :8] = 255
        png(raw, values)
        completed.append(raw)

    monkeypatch.setattr(rounds.ProcessSupervisor, "run", child)
    with pytest.raises(subprocess.CalledProcessError):
        rounds.prepare_round(checkpoint, manifest, output, execute=True)
    assert len(completed) == 1
    assert not output.exists()
    assert not list(output.parent.glob(".batch-*"))


def test_standalone_producer_uses_temporary_cache_and_new_file(
    preparation, tmp_path, monkeypatch
):
    checkpoint, _, _, fragment, _ = preparation
    monkeypatch.chdir(tmp_path)
    producer.main(
        [
            "--checkpoint",
            str(checkpoint),
            "--fragment",
            str(fragment),
            "--region-mask",
            str(fragment / "requested.png"),
            "--out",
            str(tmp_path / "standalone.png"),
            "--device",
            "cpu",
            "--tau-low",
            "0.1",
            "--tau-high",
            "0.4",
        ]
    )
    values = np.asarray(Image.open(tmp_path / "standalone.png"))
    assert (values[:, :8] == 255).all()
    assert (values[:, 8:] == 128).all()
    assert not list(tmp_path.glob("*.npy"))
    assert not list(fragment.glob("*.npy"))


@pytest.mark.parametrize("mode", ["output", "cache"])
def test_standalone_cannot_write_inside_symlinked_source_volume(
    preparation, monkeypatch, mode
):
    checkpoint, _, _, fragment, _ = preparation
    source = fragment / "surface_volume.zarr"
    actual = fragment.parent / "actual-volume.zarr"
    source.rename(actual)
    source.symlink_to(actual, target_is_directory=True)
    arguments = [
        "--checkpoint",
        str(checkpoint),
        "--fragment",
        str(fragment),
        "--region-mask",
        str(fragment / "requested.png"),
        "--out",
        str(
            actual / "pseudo.png"
            if mode == "output"
            else fragment.parent / "pseudo.png"
        ),
        "--device",
        "cpu",
    ]
    if mode == "cache":
        arguments.extend(["--cache-dir", str(actual / "cache")])

    def unexpected(*args, **kwargs):
        pytest.fail("aliased output reached inference")

    monkeypatch.setattr(producer, "_infer_region", unexpected)
    with pytest.raises(ValueError, match="overlap"):
        producer.main(arguments)
    assert not (actual / "pseudo.png").exists()
    assert not (actual / "cache").exists()
