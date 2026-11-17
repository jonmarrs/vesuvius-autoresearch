"""Finding 118's comparison: the verdict table, the measurement on maps whose answer is known, and the alignment."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "repro/first_letters/pherc0211_control/compare.py"
    spec = importlib.util.spec_from_file_location("compare_0211_reader_control", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cmp = _load()
MODELS = cmp.analysis.MODELS


def _numbers(r, wrong, slid):
    return {
        "r": r,
        "control_wrong_side": wrong,
        "control_slid": {"largest_absolute": slid},
    }


def _strokes(shape, seed):
    """Sparse blobs a few cells across: no structure at the 16-cell slide."""
    rng = np.random.default_rng(seed)
    return ndimage.gaussian_filter((rng.random(shape) > 0.97).astype(float), 1.5)


def _texture(shape, seed):
    rng = np.random.default_rng(seed)
    return ndimage.gaussian_filter(rng.standard_normal(shape), 2.0)


def test_the_verdict_table():
    assert cmp.verdict(None, 0.9) == "DOES_NOT_RUN"
    assert cmp.verdict(_numbers(0.6, 0.0, 0.0), 0.49) == "DOES_NOT_RUN"
    assert cmp.verdict(_numbers(None, 0.0, 0.0), 0.9) == "DOES_NOT_RUN"
    assert cmp.verdict(_numbers(0.4, None, 0.0), 0.9) == "DOES_NOT_RUN"
    assert cmp.verdict(_numbers(0.30, 0.15, 0.15), 0.5) == "READER_AGREES"
    assert cmp.verdict(_numbers(0.29, 0.05, 0.05), 0.9) == "READER_PARTLY"
    assert cmp.verdict(_numbers(0.15, 0.075, 0.0), 0.9) == "READER_PARTLY"
    assert cmp.verdict(_numbers(0.149, 0.0, 0.0), 0.9) == "READER_DISAGREES"
    # a control counts by its size, whatever its sign, and each control must be cleared twice
    assert cmp.verdict(_numbers(0.6, -0.31, 0.0), 0.9) == "READER_DISAGREES"
    assert cmp.verdict(_numbers(0.6, 0.0, 0.31), 0.9) == "READER_DISAGREES"
    assert cmp.verdict(_numbers(0.2, 0.0, 0.11), 0.9) == "READER_DISAGREES"


def test_maps_with_the_same_strokes_agree_and_the_controls_do_not():
    shape = (120, 400)
    theirs = _strokes(shape, 1)
    rng = np.random.default_rng(7)
    ours = {m: theirs + 0.02 * rng.standard_normal(shape) for m in MODELS}
    blind = {m: _strokes(shape, 10 + k) for k, m in enumerate(MODELS)}
    cells = np.ones(shape, bool)
    out = cmp.measure(ours, blind, theirs, cells)
    assert out["r"] > 0.8
    assert abs(out["control_wrong_side"]) < 0.15
    assert out["control_slid"]["largest_absolute"] < 0.15
    assert cmp.verdict(out, 1.0) == "READER_AGREES"


def test_unrelated_maps_disagree():
    shape = (120, 400)
    theirs = _strokes(shape, 1)
    ours = {m: _strokes(shape, 20 + k) for k, m in enumerate(MODELS)}
    blind = {m: _strokes(shape, 30 + k) for k, m in enumerate(MODELS)}
    out = cmp.measure(ours, blind, theirs, np.ones(shape, bool))
    assert abs(out["r"]) < 0.1
    assert cmp.verdict(out, 1.0) == "READER_DISAGREES"


def test_the_reading_side_must_beat_the_other_side():
    """Our other side seeing the same strokes is the wrong-side control failing: not agreement."""
    shape = (120, 400)
    theirs = _strokes(shape, 1)
    ours = {m: theirs.copy() for m in MODELS}
    out = cmp.measure(ours, ours, theirs, np.ones(shape, bool))
    assert out["r"] > 0.99 and out["control_wrong_side"] > 0.99
    assert cmp.verdict(out, 1.0) == "READER_DISAGREES"


def test_best_shift_recovers_a_known_shift():
    ref = _texture((200, 300), 3)
    moving = np.roll(ref, (-3, 5), axis=(0, 1))
    mask = np.ones(ref.shape, bool)
    dr, dc, r = cmp.best_shift(ref, moving, mask, 16)
    assert (dr, dc) == (3, -5)
    assert r > 0.99


def test_alignment_picks_the_layer_that_is_the_winners_ct():
    ct = (_texture((100, 160), 4) * 40 + 128).clip(1, 255)
    layers = {
        k: (_texture((100, 160), 50 + k) * 40 + 128).clip(1, 255) for k in range(25, 30)
    }
    layers[27] = ct.copy()
    out = cmp.alignment(layers, ct)
    assert out["layer"] == 27
    assert out["shift_pixels"] == [0, 0] and out["aligned"]
    layers[27] = np.roll(ct, (0, 4), axis=(0, 1))
    out = cmp.alignment(layers, ct)
    assert out["layer"] == 27
    assert out["shift_pixels"] == [0, -4] and not out["aligned"]
    assert out["r_at_shift"] > 0.99


def test_roll_cells_moves_whole_cells_and_blanks_what_came_from_outside():
    image = np.arange(30.0).reshape(5, 6)
    moved = cmp.roll_cells(image, [4, -8])  # one cell down, two cells left
    assert np.isnan(moved[0]).all() and np.isnan(moved[:, -2:]).all()
    assert moved[1, 0] == image[0, 2]
    assert np.array_equal(cmp.roll_cells(image, [0, 0]), image)
    assert np.array_equal(
        cmp.roll_cells(image, [1, -1]), image
    )  # under half a cell: no move


# --- the whole comparison, from files ---------------------------------------------------------------


def _write_inputs(root: Path, other_side_same: bool = False) -> list[str]:
    """A flat mesh of 7 x 11 nodes, its render (levels 0 and 2), the recipe's maps at every depth and side, the
    winner's map, mask and CT. Our reading side carries the winner's strokes; the other side carries others."""
    import cv2
    import tifffile
    import zarr

    rows, cols = 7, 11
    r, c = np.mgrid[0:rows, 0:cols].astype(float)
    mesh = root / "v9" / "normalized-tifxyz"
    mesh.mkdir(parents=True)
    for name, values in (
        ("x", c * 20 + 2000),
        ("y", np.full_like(r, 3000.0)),
        ("z", r * 20 + 8000),
    ):
        tifffile.imwrite(mesh / f"{name}.tif", values.astype(np.float32))
    h, w = rows * 20, cols * 20
    ct = (_texture((h, w), 5) * 40 + 128).clip(1, 255).astype(np.uint8)
    render = zarr.open(str(root / "v9_66.zarr"), mode="w")
    render.create_dataset("0", data=np.repeat(ct[None], 66, axis=0), chunks=(66, h, w))
    render.create_dataset(
        "2",
        data=np.full((66, h // 4, w // 4), 90, np.uint8),
        chunks=(66, h // 4, w // 4),
    )
    strokes = _strokes((h // 4, w // 4), 1)
    other = _strokes((h // 4, w // 4), 2)
    pixels = np.kron(strokes, np.ones((4, 4)))
    other_pixels = pixels if other_side_same else np.kron(other, np.ones((4, 4)))
    maps = root / "maps"
    maps.mkdir()
    rng = np.random.default_rng(9)
    for d in cmp.DEPTHS:
        for tag, values in (("_reverse", pixels), ("", other_pixels)):
            p = values / values.max() * 0.5 + 0.25
            for model in MODELS:
                q = np.clip(p + 0.005 * rng.standard_normal(p.shape), 0, 1)
                if model == "hecate":
                    cv2.imwrite(
                        str(maps / f"v9_66__hecate__L66zc{32.5 + d:.2f}{tag}.png"),
                        np.round(q * 255).astype(np.uint8),
                    )
                else:
                    cv2.imwrite(
                        str(maps / f"v9_66__{model}__L66s{d + 25}{tag}.tif"),
                        np.clip(64 + 128 * q, 0, 255).astype(np.uint8),
                    )
    tifffile.imwrite(root / "studio.tif", (pixels / pixels.max()).astype(np.float32))
    cv2.imwrite(str(root / "mask.png"), np.full((h, w), 255, np.uint8))
    tifffile.imwrite(root / "ct.tif", ct)
    return [
        "--mesh", str(mesh), "--maps", str(maps), "--render", str(root / "v9_66.zarr"),
        "--studio", str(root / "studio.tif"), "--studio-mask", str(root / "mask.png"),
        "--winner-ct", str(root / "ct.tif"), "--image", str(root / "both.png"),
    ]  # fmt: skip


def test_the_other_side_is_read_at_the_depth_asked_for(tmp_path):
    """transfer_maps.side read the other side at depth +1 whatever depth it was given (found in finding 118's
    table of depths, where all six other-side numbers came out the same)."""
    args = dict(zip(*[iter(_write_inputs(tmp_path))] * 2, strict=False))
    mesh, maps, render = (Path(args[k]) for k in ("--mesh", "--maps", "--render"))
    deep = cmp.tm.side(mesh, maps, render, blind_too=True, depth=-2)
    registered = cmp.tm.side(mesh, maps, render, blind_too=True, depth=1)
    assert deep["blind_files"]["dnative"].endswith("__dnative__L66s23.tif")
    assert deep["blind_files"]["hecate"].endswith("__hecate__L66zc30.50.png")
    assert registered["blind_files"]["dnative"].endswith("__dnative__L66s26.tif")
    for model in MODELS:
        assert not np.array_equal(
            deep["blind_maps"][model], registered["blind_maps"][model]
        )


def test_the_script_agrees_on_matching_maps_and_writes_its_record(tmp_path):
    import json

    args = _write_inputs(tmp_path)
    out = tmp_path / "compare.json"
    assert cmp.main([str(out), *args]) == 0
    record = json.loads(out.read_text())
    assert record["alignment"]["aligned"] and record["shift_applied_pixels"] == [0, 0]
    assert record["cell_share"] >= 0.5
    assert record["registered"]["r"] > 0.8
    assert record["verdict"] == "READER_AGREES"
    assert set(record["described"]["by_depth_and_side"]) == {
        f"{d:+d}_{s}" for d in cmp.DEPTHS for s in ("reading", "other")
    }
    assert record["described"]["per_model_r"]["hecate"] > 0.5
    assert (tmp_path / "both.png").exists()
    # measured once
    assert cmp.main([str(out), *args]) == 2
    # a recheck writes a new record, says whether the registered numbers came out the same, and leaves the first
    first = out.read_bytes()
    again = tmp_path / "compare_recheck.json"
    assert cmp.main([str(again), *args, "--recheck", str(out)]) == 0
    assert json.loads(again.read_text())["registered_reproduces"] is True
    assert out.read_bytes() == first
    assert cmp.main([str(again), *args, "--recheck", str(out)]) == 2
    edited = json.loads(first)
    edited["registered"]["r"] = 0.1
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(edited))
    third = tmp_path / "compare_recheck2.json"
    assert cmp.main([str(third), *args, "--recheck", str(changed)]) == 0
    assert json.loads(third.read_text())["registered_reproduces"] is False


def test_the_script_refuses_agreement_when_both_sides_carry_the_strokes(tmp_path):
    import json

    args = _write_inputs(tmp_path, other_side_same=True)
    out = tmp_path / "compare.json"
    assert cmp.main([str(out), *args]) == 0
    assert json.loads(out.read_text())["verdict"] == "READER_DISAGREES"


# Added by the design review of 2026-11-17: the alignment at its edges, the overlap of a shift, and the high-pass.


def _ct(seed=4, shape=(100, 160)):
    return (_texture(shape, seed) * 40 + 128).clip(1, 255)


def test_a_shift_of_one_pixel_is_aligned_and_of_two_is_not():
    ct = _ct()
    for columns, aligned in ((1, True), (2, False)):
        out = cmp.alignment({27: np.roll(ct, (0, columns), axis=(0, 1))}, ct)
        assert out["shift_pixels"] == [0, -columns] and out["aligned"] is aligned


def test_the_alignment_searches_sixteen_pixels_each_way():
    ct = _ct()
    out = cmp.alignment({27: np.roll(ct, (16, 0), axis=(0, 1))}, ct)
    assert out["shift_pixels"] == [-16, 0] and out["r_at_shift"] > 0.99


def test_the_alignment_compares_only_pixels_with_ct_in_every_layer():
    ct = _ct()
    rng = np.random.default_rng(9)
    half = ct.copy()
    half[:, :80] = 0  # no CT in the left half of this layer
    noisy = (ct + 25 * rng.standard_normal(ct.shape)).clip(1, 255)
    out = cmp.alignment({30: half, 31: noisy}, ct)
    # over the right half alone, the layer that is the CT matches it exactly
    assert out["layer"] == 30 and out["r_at_zero_by_layer"]["30"] == 1.0


def test_a_shifted_r_leaves_out_what_slid_in_from_outside_the_mask():
    reference = _texture((50, 80), 5)
    mask = np.zeros(reference.shape, bool)
    mask[:, 10:70] = True
    moving = np.roll(reference, (0, -5), axis=(0, 1))
    moving[:, :10] = 1000.0  # outside the mask
    moving[:, 70:] = 1000.0
    assert cmp.shifted_r(reference, moving, mask, 0, 5) == pytest.approx(1.0)


def test_roll_cells_blanks_the_columns_a_rightward_move_brings_in():
    image = np.arange(30.0).reshape(5, 6)
    moved = cmp.roll_cells(image, [0, 8])  # two cells right
    assert np.isnan(moved[:, :2]).all() and not np.isnan(moved[:, 2:]).any()
    assert moved[0, 2] == image[0, 0]


def test_the_winners_map_loses_its_broad_background_before_it_is_compared():
    shape = (120, 160)
    strokes = _strokes(shape, 1)
    cells = np.ones(shape, bool)
    rows = np.indices(shape)[0]
    studio = (
        strokes + 20 * strokes.std() * rows / shape[0]
    )  # a slope across the whole map
    rng = np.random.default_rng(2)
    ours = {
        m: strokes + 0.1 * strokes.std() * rng.standard_normal(shape) for m in MODELS
    }
    blind = {m: _texture(shape, 20 + k) for k, m in enumerate(MODELS)}
    assert cmp.measure(ours, blind, studio, cells)["r"] > 0.8
