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


# --- each edge of a window's crop, the inputs predict refuses, the window count, the lines, compare and run's checks -


@pytest.mark.parametrize(
    ("y", "x", "has"),
    [(260, 200, True), (275, 200, True), (276, 200, False),  # CT only in the 16 rows of context above the window
     (39, 200, True), (38, 200, False),  # only in the last 16 rows of the crop, below the window
     (200, 330, True), (200, 345, True), (200, 346, False),  # the same, left
     (200, 69, True), (200, 68, False)],  # and right
)  # fmt: skip
def test_a_windows_crop_reaches_16_pixels_each_side_of_it(y, x, has):
    # the CT block is rows 150 to 259 and columns 180 to 329
    v = _volume()
    assert sf.has_ct(sf.integral(v), *v.shape[1:], y, x) is has


def test_ct_in_any_one_plane_counts():
    v = np.zeros((16, 200, 200), np.uint8)
    v[5, 100, 100] = 7
    assert sf.has_ct(sf.integral(v), 200, 200, 64, 64)


@pytest.mark.parametrize(
    ("volume", "batch"),
    [(np.zeros((15, 64, 64), np.uint8), 1), (np.zeros((16, 64, 64), np.uint16), 1),
     (np.zeros((16, 64, 64), np.uint8), 0)],
    ids=["15-planes", "16-bit", "no-batch"],
)  # fmt: skip
def test_predict_refuses_another_input_or_an_empty_batch(tmp_path, volume, batch):
    with pytest.raises(ValueError):
        sf.predict(
            _toy_inf(), _toy_model, volume, tmp_path / "o.npy", "cpu", batch, "fp32"
        )


@pytest.mark.parametrize(
    ("stride", "blend", "windows"), [(64, "hann", 8 * 9), (96, "none", 5 * 6)]
)
def test_the_window_count_is_the_winners_starts(tmp_path, stride, blend, windows):
    # hann adds a last window flush with the bottom and the right edges: rows 304 and columns 404
    counts = sf.predict(
        _toy_inf(),
        _toy_model,
        _volume(),
        tmp_path / "o.npy",
        "cpu",
        32,
        "fp32",
        stride,
        blend,
    )
    assert counts == {"windows": windows, "run": windows}


def test_a_map_exactly_at_each_line_is_the_same_map():
    assert sf.same(_numbers(r=sf.R_SAME, p99=sf.P99_SAME, side=sf.SIDE_SAME))


def test_the_verdict_needs_pairs_and_ratios_and_takes_a_ratio_at_the_line():
    pairs = {"full_a": _numbers(), "skip_a": _numbers()}
    assert sf.verdict(True, {}, [0.5]) == "DOES_NOT_RUN"
    assert sf.verdict(True, pairs, []) == "SKIP_NOT_FASTER"
    assert sf.verdict(True, pairs, [sf.FASTER]) == "SKIP_ADOPTED"


def _compare_files(tmp_path):
    """Planes with CT in plane 3 only, over the left half; two maps equal there and different on the right."""
    planes = np.zeros((16, 8, 8), np.uint8)
    planes[3, :, :4] = 9
    rng = np.random.default_rng(0)
    ref = rng.random((8, 8)).astype(np.float32)
    ours = ref.copy()
    ours[:, 4:] += 0.3
    for name, array in (("planes", planes), ("ref", ref), ("ours", ours)):
        np.save(tmp_path / f"{name}.npy", array)
    return tmp_path / "ours.npy", tmp_path / "ref.npy", tmp_path / "planes.npy"


def test_a_pair_is_compared_over_the_pixels_any_plane_gives_ct(tmp_path):
    numbers = sf.compare_pair(*_compare_files(tmp_path))
    assert numbers["pixels"] == 32 and numbers["exact_over_the_ct"] is True


@pytest.mark.parametrize(
    ("steps_ok", "expected"), [("yes", "SKIP_ADOPTED"), ("no", "DOES_NOT_RUN")]
)
def test_the_compare_command_takes_skip_over_full_time_and_runs_once(
    tmp_path, steps_ok, expected
):
    import json

    ours, ref, planes = _compare_files(tmp_path)
    (tmp_path / "runs.json").write_text(
        json.dumps({"full_w": {"seconds": 10.0}, "skip_w": {"seconds": 6.0}})
    )
    argv = ["compare", str(tmp_path / "out.json"), "--pair", "full_w", str(ref), str(ref), str(planes),
            "--pair", "skip_w", str(ref), str(ref), str(planes), "--seconds-json", str(tmp_path / "runs.json"),
            "--band-windings", "w", "--steps-ok", steps_ok]  # fmt: skip
    assert sf.main(argv) == 0
    out = json.loads((tmp_path / "out.json").read_text())
    assert out["time_ratio_skip_over_full"] == {"w": 0.6} and out["verdict"] == expected
    assert sf.main(argv) == 2


def test_run_checks_its_code_its_output_and_its_tiling_first(tmp_path, monkeypatch):
    import argparse

    code = tmp_path / "code"
    code.mkdir()
    (code / "inference.py").write_text("")
    monkeypatch.setattr(sys, "path", list(sys.path))
    # Record a restore of a missing key, then delete it, so teardown cannot
    # leave the tmp inference module that sf.run imports.
    monkeypatch.setitem(sys.modules, "inference", None)
    monkeypatch.delitem(sys.modules, "inference")

    def args(**kw):
        base = {"code": code, "input": tmp_path / "in.npy", "output": tmp_path / "out.npy",
                "checkpoint": tmp_path / "w", "batch_size": 32, "stride": 96, "blend": "none",
                "skip_empty": False}  # fmt: skip
        return argparse.Namespace(**{**base, **kw})

    (tmp_path / "out.npy").write_bytes(b"")
    with pytest.raises(SystemExit, match="exists"):
        sf.run(args())
    with pytest.raises(SystemExit, match="needs --blend hann"):
        sf.run(args(output=tmp_path / "new.npy", stride=64))
    other = types.ModuleType("inference")
    other.__file__ = str(tmp_path / "elsewhere" / "inference.py")
    monkeypatch.setitem(sys.modules, "inference", other)
    with pytest.raises(SystemExit, match="imported"):
        sf.run(args(output=tmp_path / "new.npy"))


def test_the_run_test_does_not_leak_inference():
    # follow-on probe: the run test must not leave its stand-in inference module in sys.modules
    leaked = sys.modules.get("inference")
    assert leaked is None, f"leaked: {leaked}"
