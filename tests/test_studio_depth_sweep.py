"""Finding 135's analysis: shifted planes, the chosen shift, and the registered verdict with its failure branches."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ds = _load("depth_sweep_under_test", CONTROL / "depth_sweep.py")


def _render(path: Path, layers: int) -> Path:
    import zarr

    first = (
        (66 - layers) // 2
    )  # a centred render holds these layers of the 66-layer frame (render_frame.py)
    data = np.zeros((layers, 4, 5), np.uint8)
    for i in range(layers):
        data[i] = first + i  # each layer carries its 66-frame number
    zarr.open(str(path), mode="w").create_dataset("0", data=data, chunks=(layers, 4, 5))
    return path


def _curves(e2e=None, dense=None):
    flat = {d: 0.80 for d in ds.SHIFTS}
    return {"e2e": {**flat, **(e2e or {})}, "dense2s3": {**flat, **(dense or {})}}


SHARES = {"e2e": 0.83, "dense2s3": 0.83}


def test_shift_zero_is_finding_124s_planes_and_a_shift_moves_every_plane(tmp_path):
    assert ds.shifted_layers(0) == ds.f124.LAYERS
    render = _render(tmp_path / "w_66.zarr", 66)
    ds.planes_cmd(render, tmp_path / "p.npy", 2)
    planes = np.load(tmp_path / "p.npy")
    assert [int(p[0, 0]) for p in planes] == list(range(43, 27, -1))


def test_a_shift_outside_the_render_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ds.shifted_layers(25)  # layer 66 is past the frame
    thin = _render(
        tmp_path / "w_18.zarr", 18
    )  # layers 24 to 41: the band reads' render
    ds.planes_cmd(thin, tmp_path / "zero.npy", 0)
    with pytest.raises(SystemExit, match="not in a 18-layer render"):
        ds.planes_cmd(thin, tmp_path / "out.npy", 1)


def test_the_best_shift_breaks_ties_toward_zero_then_outward():
    assert ds.best_shift(_curves()) == 0
    assert ds.best_shift(_curves({2: 0.81, -2: 0.81})) == 2
    assert ds.best_shift(_curves({-1: 0.83}, {-1: 0.82})) == -1
    missing = _curves()
    missing["e2e"][4] = None
    assert ds.best_shift(missing) is None


def test_a_shift_reads_better_only_when_both_arms_gain_the_line():
    v, d, gains = ds.verdict(_curves({2: 0.82}, {2: 0.82}), SHARES, True)
    assert (v, d, gains) == (
        "DEPTH_SHIFT_READS_BETTER",
        2,
        {"e2e": 0.02, "dense2s3": 0.02},
    )  # exactly at the line
    v, d, gains = ds.verdict(_curves({2: 0.85}, {2: 0.819}), SHARES, True)
    assert v == "DEPTH_SHIFT_WITHIN_MARGIN" and d == 2 and gains["dense2s3"] == 0.019
    assert (
        ds.verdict(_curves({1: 0.79}, {1: 0.79}), SHARES, True)[0] == "DEPTH_ZERO_BEST"
    )


def test_the_failure_branch_gives_no_verdict_even_with_a_clear_gain():
    clear = _curves({2: 0.9}, {2: 0.9})
    assert ds.verdict(clear, SHARES, False) == (
        "DOES_NOT_RUN",
        None,
        None,
    )  # finding 124 not reproduced
    assert (
        ds.verdict(clear, {"e2e": 0.83, "dense2s3": 0.49}, True)[0] == "DOES_NOT_RUN"
    )  # too few cells
    assert ds.verdict(None, SHARES, True)[0] == "DOES_NOT_RUN"


def test_a_partial_sweep_is_refused():
    one_arm = {"e2e": _curves()["e2e"]}
    assert ds.verdict(one_arm, SHARES, True)[0] == "DOES_NOT_RUN"
    short = _curves()
    del short["dense2s3"][8]
    assert ds.verdict(short, SHARES, True)[0] == "DOES_NOT_RUN"
    unscored = _curves()
    unscored["dense2s3"][-8] = None
    assert ds.verdict(unscored, SHARES, True)[0] == "DOES_NOT_RUN"


def test_half_widths_are_the_nearest_shift_at_half_of_zero_on_each_side():
    curve = {d: 0.8 for d in ds.SHIFTS}
    curve.update({-4: 0.41, -6: 0.40, -8: 0.1, 4: 0.5, 6: 0.3, 8: 0.2})
    assert ds.half_widths(curve) == {"inward": 6, "outward": 6}
    assert ds.half_widths({d: 0.8 for d in ds.SHIFTS}) == {
        "inward": None,
        "outward": None,
    }
    assert (
        ds.shift_dir(-2) == "d-2"
        and ds.shift_dir(0) == "d+0"
        and ds.shift_dir(4) == "d+4"
    )
