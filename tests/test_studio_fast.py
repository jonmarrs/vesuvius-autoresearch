"""Finding 132: Studio's loop with empty windows skipped. The window rule, the skip on a toy model, the copy of the
winner's loop against the winner's file where this machine has it, the verdict table and the run script."""

import importlib.util
import os
import re
import sys
import types
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"
WINNER_CODE = Path(
    "/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc0211_control/inputs/winner/v9/inference"
)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sf = _load("studio_fast_under_test", CONTROL / "studio_fast.py")


def _toy_inf():
    """crop and hann96 as the winner's inference.py defines them."""

    def crop(array, y, x):
        h, w = array.shape[-2:]
        tile = np.asarray(
            array[:, max(0, y) : min(h, y + 128), max(0, x) : min(w, x + 128)]
        )
        padding = (
            (0, 0),
            (max(0, -y), max(0, y + 128 - h)),
            (max(0, -x), max(0, x + 128 - w)),
        )
        return (
            np.pad(tile, padding, mode="reflect")
            if any(a or b for a, b in padding)
            else tile
        )

    def hann96():
        w = 0.5 - 0.5 * np.cos(2 * np.pi * (np.arange(96) + 0.5) / 96)
        return (w[:, None] * w[None, :]).astype(np.float32)

    return types.SimpleNamespace(crop=crop, hann96=hann96)


def _toy_model(x):
    """A per-pixel stand-in for the network ([B, 1, 16, 128, 128] in, [B, 1, 128, 128] out, as Studio's), so the
    batch a window is in cannot change its output."""
    return x.mean(dim=2) * 6.0 - 1.0


def _volume(h=400, w=500):
    rng = np.random.default_rng(0)
    v = np.zeros((16, h, w), np.uint8)
    v[:, 150:260, 180:330] = rng.integers(
        1, 200, size=(16, 110, 150), dtype=np.uint8
    )  # CT in one block only
    return v


def test_a_window_has_ct_when_its_crop_does():
    v = _volume()
    ii = sf.integral(v)
    h, w = v.shape[1:]
    assert sf.has_ct(
        ii, h, w, 128, 128
    )  # crop rows 112-239, columns 112-239: overlaps the block
    assert not sf.has_ct(ii, h, w, 0, 0)  # crop rows -16-111: nothing
    assert not sf.has_ct(ii, h, w, 0, 64)
    assert sf.has_ct(
        ii, h, w, 64 + 2, 64 + 52
    )  # crop rows 52-179, columns 102-229: just reaches the block
    assert not sf.has_ct(ii, h, w, 384, 448)


@pytest.mark.parametrize(("stride", "blend"), [(64, "hann"), (96, "none")])
def test_skipping_empty_windows_changes_no_pixel_with_ct(tmp_path, stride, blend):
    v = _volume()
    full = sf.predict(
        _toy_inf(),
        _toy_model,
        v,
        tmp_path / "full.npy",
        "cpu",
        32,
        "fp32",
        stride,
        blend,
    )
    skip = sf.predict(
        _toy_inf(),
        _toy_model,
        v,
        tmp_path / "skip.npy",
        "cpu",
        32,
        "fp32",
        stride,
        blend,
        True,
    )
    a, b = np.load(tmp_path / "full.npy"), np.load(tmp_path / "skip.npy")
    assert np.array_equal(a, b)
    assert (
        full["windows"] == skip["windows"]
        and skip["run"] < full["run"] == full["windows"]
    )
    assert (b[(v == 0).all(0)] == 0).all()


@pytest.mark.skipif(
    not (WINNER_CODE / "inference.py").exists(),
    reason="the winner's inference.py is local only",
)
def test_the_copied_loop_is_the_winners(tmp_path):
    sys.path.insert(0, str(WINNER_CODE))
    try:
        winner = _load("winner_inference_for_test", WINNER_CODE / "inference.py")
    finally:
        sys.path.remove(str(WINNER_CODE))
    v = _volume()
    winner.predict(
        _toy_model,
        v,
        tmp_path / "w.npy",
        device="cpu",
        batch_size=32,
        amp="fp32",
        stride=64,
        blend="hann",
    )
    sf.predict(winner, _toy_model, v, tmp_path / "o.npy", "cpu", 32, "fp32", 64, "hann")
    sf.predict(
        winner, _toy_model, v, tmp_path / "s.npy", "cpu", 32, "fp32", 64, "hann", True
    )
    w, o, s = (np.load(tmp_path / f) for f in ("w.npy", "o.npy", "s.npy"))
    assert np.array_equal(w, o) and np.array_equal(w, s)


def _numbers(r=1.0, p99=0.0006, side=0.9999):
    return {"r": r, "abs_difference": {"p99": p99}, "share_same_side_of_half": side}


@pytest.mark.parametrize(
    ("full", "skip", "ratios", "expected"),
    [
        (_numbers(), _numbers(), [0.6, 0.7], "SKIP_ADOPTED"),
        (_numbers(), _numbers(), [0.6, 0.81], "SKIP_NOT_FASTER"),
        (_numbers(), _numbers(r=0.9998), [0.6, 0.7], "SKIP_DIFFERS"),
        (_numbers(), _numbers(p99=0.0021), [0.6, 0.7], "SKIP_DIFFERS"),
        (_numbers(), _numbers(side=0.9994), [0.6, 0.7], "SKIP_DIFFERS"),
        (
            _numbers(r=0.99),
            _numbers(),
            [0.6, 0.7],
            "DOES_NOT_RUN",
        ),  # the copy is not the winner's loop
    ],
)
def test_the_verdict_table(full, skip, ratios, expected):
    pairs = {"full_a": full, "skip_a": skip, "full_b": _numbers(), "skip_b": _numbers()}
    assert sf.verdict(True, pairs, ratios) == expected
    assert sf.verdict(False, pairs, ratios) == "DOES_NOT_RUN"


def test_the_lines_are_the_registrations():
    assert (sf.R_SAME, sf.P99_SAME, sf.SIDE_SAME, sf.FASTER) == (
        0.9999,
        0.002,
        0.9995,
        0.8,
    )
    reg = " ".join(
        (ROOT / "docs/preregistration/2026-11-20_studio_skip_empty_windows.md")
        .read_text()
        .split()
    )
    assert (
        "r ≥ 0.9999, p99 ≤ 0.002 and at least 99.95%" in reg and "at most 0.8 of" in reg
    )


def test_the_run_keeps_the_winners_command_and_uploads_nothing():
    path = CONTROL / "run_studio_fast.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    assert "--batch-size 32" in text and "--stride 64 --blend hann" in text
    assert "BAND_WINDINGS=(w062 w065)" in text
    shas = dict(re.findall(r"^(W_SHA|CODE_SHA|P_SHA)=(\w+)", text, flags=re.M))
    f123 = dict(re.findall(r"^(W_SHA|CODE_SHA|P_SHA)=(\w+)", (CONTROL / "run_studio_reproduction.sh").read_text(),
                           flags=re.M))  # fmt: skip
    assert shas == f123 and len(shas) == 3
