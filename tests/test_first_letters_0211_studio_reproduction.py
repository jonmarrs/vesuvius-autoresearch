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
