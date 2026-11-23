"""Finding 123: the reproduction comparison on maps whose answer is known, and the driver's checks."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load():
    spec = importlib.util.spec_from_file_location(
        "studio_reproduce_under_test", CONTROL / "studio_reproduce.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sr = _load()


def _maps(noise: float, seed: int = 0):
    rng = np.random.default_rng(seed)
    theirs = np.clip(rng.random((60, 80)) ** 3, 0, 1).astype(np.float32)
    ours = np.clip(theirs + noise * rng.standard_normal(theirs.shape), 0, 1).astype(
        np.float32
    )
    mask = np.ones(theirs.shape, bool)
    mask[:, :5] = False
    return ours, theirs, mask


def test_the_verdict_table():
    close = {"r": 0.995, "abs_difference": {"p99": 0.03}}
    assert sr.verdict(0, True, close) == "EXACT"
    assert sr.verdict(0, False, close) == "REPRODUCED"
    assert (
        sr.verdict(0, False, {"r": 0.989, "abs_difference": {"p99": 0.03}}) == "DIFFERS"
    )
    assert (
        sr.verdict(0, False, {"r": 0.995, "abs_difference": {"p99": 0.051}})
        == "DIFFERS"
    )
    assert sr.verdict(1, None, None) == "DOES_NOT_RUN"
    assert sr.verdict(0, False, None) == "DOES_NOT_RUN"


def test_the_lines_are_the_registrations():
    assert (sr.R_REPRODUCED, sr.P99_REPRODUCED) == (0.99, 0.05)
    text = (
        ROOT
        / "docs/preregistration/2026-11-16_first_letters_0211_studio_reproduction.md"
    ).read_text()
    assert (
        "| r at least 0.99 over the mask and a 99th-percentile absolute difference of at most 0.05 | `REPRODUCED` |"
        in text
    )
    assert sr.RECORDED_NPY_SHA256 in text


def test_rounding_noise_reproduces_and_a_different_map_does_not():
    ours, theirs, mask = _maps(0.002)
    numbers = sr.compare(ours, theirs, mask)
    assert numbers["pixels"] == int(mask.sum()) and numbers["r"] > 0.99
    assert sr.verdict(0, False, numbers) == "REPRODUCED"
    other, _, _ = _maps(0.0, seed=1)
    assert sr.verdict(0, False, sr.compare(other, theirs, mask)) == "DIFFERS"


def test_the_command_writes_its_record_once(tmp_path):
    import cv2
    import tifffile

    ours, theirs, mask = _maps(0.002)
    np.save(tmp_path / "ink.npy", ours)
    tifffile.imwrite(tmp_path / "winner.tif", theirs)
    cv2.imwrite(str(tmp_path / "mask.png"), mask.astype(np.uint8) * 255)
    out = tmp_path / "repro.json"
    argv = [
        str(out),
        str(tmp_path / "ink.npy"),
        str(tmp_path / "winner.tif"),
        str(tmp_path / "mask.png"),
    ]
    assert sr.main(argv) == 0
    record = json.loads(out.read_text())
    assert record["verdict"] == "REPRODUCED" and record["exact"] is False
    assert sr.main(argv) == 2
    failed = tmp_path / "gate.json"
    failed.write_text('{"exit": 1, "seconds": 3}')
    out2 = tmp_path / "repro2.json"
    assert sr.main([str(out2), *argv[1:], "--gate", str(failed)]) == 0
    assert json.loads(out2.read_text())["verdict"] == "DOES_NOT_RUN"


def test_the_driver_checks_every_input_and_runs_the_recorded_command():
    path = CONTROL / "run_studio_reproduction.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in (
        "aws s3 cp",
        "gh release upload",
        "curl -T",
        "--upload-file",
        "rsync ",
    ):
        assert word not in text
    # the SHA-256 values of the winner's inference-record.json
    assert (
        "W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90" in text
    )
    assert (
        "P_SHA=e7cdd509d74958a8cb95e9bfb0b1857610e457363edfe5329850b9b009ff8c22" in text
    )
    assert (
        "CODE_SHA=09752cf7aa0b682c6ca9a46e41bf1f9f279e30d74d35eaab8fc0311504223ec0"
        in text
    )
    assert "| sha256sum -c" in text
    assert '--checkpoint "$WEIGHTS" --stride 64 --blend hann --batch-size 32' in text
    assert "HF_HUB_OFFLINE=1" in text
    order = [
        "step fetch fetch",
        "step env environment",
        "step infer infer",
        "step compare",
    ]
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)


def test_the_comparison_refuses_a_map_or_a_mask_of_another_shape():
    import pytest

    ours, theirs, mask = _maps(0.0)
    with pytest.raises(ValueError, match="shapes differ"):
        sr.compare(ours, theirs[:, :-1], mask)
    with pytest.raises(ValueError, match="shapes differ"):
        sr.compare(ours, theirs, mask[:, :-1])


def test_pixels_that_are_not_finite_are_left_out():
    ours, theirs, mask = _maps(0.002)
    ours[10, 10] = np.nan
    theirs[20, 20] = np.inf
    numbers = sr.compare(ours, theirs, mask)
    assert numbers["pixels"] == int(mask.sum()) - 2
    assert numbers["r"] > 0.99


def test_the_differences_are_read_at_their_registered_percentiles():
    rng = np.random.default_rng(2)
    theirs = rng.random((10, 100)).astype(np.float32)
    ours = theirs.copy()
    ours.flat[:15] += np.float32(
        0.5
    )  # 1.5% of the pixels differ by 0.5, the rest not at all
    numbers = sr.compare(ours, theirs, np.ones(theirs.shape, bool))
    assert numbers["abs_difference"] == {"p50": 0.0, "p99": 0.5, "max": 0.5}


def test_a_pixel_at_exactly_one_half_is_on_the_upper_side():
    theirs = np.array([[0.5, 0.2, 0.7, 0.1]], np.float32)
    ours = np.array([[0.49, 0.2, 0.7, 0.1]], np.float32)
    numbers = sr.compare(ours, theirs, np.ones(theirs.shape, bool))
    assert numbers["share_same_side_of_half"] == 0.75


def test_the_reproduction_lines_are_inclusive():
    at_lines = {"r": 0.99, "abs_difference": {"p99": 0.05}}
    assert sr.verdict(0, False, at_lines) == "REPRODUCED"


def _write_inputs(root: Path) -> list[str]:
    import cv2
    import tifffile

    ours, theirs, mask = _maps(0.002)
    np.save(root / "ink.npy", ours)
    tifffile.imwrite(root / "winner.tif", theirs)
    cv2.imwrite(str(root / "mask.png"), mask.astype(np.uint8) * 255)
    return [str(root / "ink.npy"), str(root / "winner.tif"), str(root / "mask.png")]


def test_the_record_counts_the_masks_pixels_and_hashes_our_output(tmp_path):
    import hashlib

    inputs = _write_inputs(tmp_path)
    out = tmp_path / "repro.json"
    assert sr.main([str(out), *inputs]) == 0
    record = json.loads(out.read_text())
    _, _, mask = _maps(0.002)
    assert record["numbers"]["pixels"] == int(mask.sum())
    expected = hashlib.sha256((tmp_path / "ink.npy").read_bytes()).hexdigest()
    assert record["output_sha256"] == expected


def test_a_missing_output_does_not_run_and_an_unreadable_mask_stops(tmp_path):
    import pytest

    inputs = _write_inputs(tmp_path)
    missing = tmp_path / "missing.json"
    assert sr.main([str(missing), str(tmp_path / "none.npy"), *inputs[1:]]) == 0
    record = json.loads(missing.read_text())
    assert record["numbers"] is None and record["verdict"] == "DOES_NOT_RUN"
    (tmp_path / "mask.png").write_bytes(b"not an image")
    with pytest.raises(SystemExit, match="cannot read"):
        sr.main([str(tmp_path / "repro.json"), *inputs])


def test_an_output_holding_python_objects_is_never_unpickled(tmp_path):
    import pytest

    inputs = _write_inputs(tmp_path)
    _, theirs, _ = _maps(0.002)
    np.save(tmp_path / "ink.npy", theirs.astype(object), allow_pickle=True)
    with pytest.raises(ValueError, match="allow_pickle"):
        sr.main([str(tmp_path / "repro.json"), *inputs])
