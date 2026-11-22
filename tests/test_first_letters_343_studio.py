"""Finding 127: Studio on PHerc. 343's published text place. The frame, the verdict table, the leave-one-out lines,
the letter boxes, and the comparison on a synthetic render whose Studio map is the reference plus noise."""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "repro/first_letters/pherc343"
REGISTRATION = ROOT / "docs/preregistration/2026-11-20_first_letters_343_studio.md"


def _load():
    spec = importlib.util.spec_from_file_location(
        "studio_343_under_test", HERE / "studio_343.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


s3 = _load()


def _sidecar(row0, row1, col0, col1, flip_ud=True, flip_lr=True, letters=()):
    return {
        "area": {
            "raw_render_px": {"row0": row0, "row1": row1, "col0": col0, "col1": col1}
        },
        "orientation": {"flip_ud": flip_ud, "flip_lr": flip_lr},
        "letters": {
            "letters_area_px": [
                {"id": i + 1, "box": list(b)} for i, b in enumerate(letters)
            ]
        },
    }


def _strokes(h, w, seed, n=60):
    """Short strokes at random places: no period, so a 64-pixel slide lands off them."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w))
    for _ in range(n):
        y, x = rng.integers(0, h - 6), rng.integers(0, w - 14)
        if rng.random() < 0.5:
            out[y : y + 3, x : x + 14] = 1.0
        else:
            out[y : y + 12, x : x + 3] = 1.0
    return out


def test_the_reading_frame_is_the_area_mirrored_as_the_sidecar_says():
    raw = np.arange(6 * 8).reshape(6, 8)
    out = s3.to_reading(raw, _sidecar(1, 5, 2, 7))
    assert out.shape == (4, 5)
    assert out[0, 0] == raw[4, 6] and out[-1, -1] == raw[1, 2]
    same = s3.to_reading(raw, _sidecar(1, 5, 2, 7, False, False))
    assert same[0, 0] == raw[1, 2]


@pytest.mark.parametrize(
    ("r", "wrong", "slid", "share", "expected"),
    [
        (0.41, 0.2, 0.2, 0.6, "STUDIO_343_AGREES"),
        (0.409, 0.1, 0.1, 0.6, "STUDIO_343_PARTLY"),
        (0.5, 0.26, 0.1, 0.6, "STUDIO_343_FAR"),  # not twice the other side
        (
            0.5,
            -0.3,
            0.1,
            0.6,
            "STUDIO_343_FAR",
        ),  # the control's size counts, not its sign
        (0.19, 0.0, 0.0, 0.6, "STUDIO_343_FAR"),
        (0.9, 0.0, 0.0, 0.49, "DOES_NOT_RUN"),
        (None, 0.0, 0.0, 0.6, "DOES_NOT_RUN"),
    ],
)
def test_the_verdict_table(r, wrong, slid, share, expected):
    numbers = {
        "r": r,
        "control_wrong_side": wrong,
        "control_slid": {"largest_absolute": slid},
    }
    assert s3.verdict(numbers, share) == expected


def test_the_line_is_the_lowest_member_against_the_rest_as_registered():
    text = " ".join(REGISTRATION.read_text().split())
    assert s3.AGREES == round(min(s3.REGISTERED_LEAVE_ONE_OUT.values()), 2) == 0.41
    assert s3.PARTLY == 0.20 and s3.RATIO == 2.0
    for name, label in (("dnative", "dense_native"), ("hecate", "Hecate"), ("ink9-42", "ink_9um seed 42"),
                        ("ink9-43", "ink_9um seed 43")):  # fmt: skip
        assert f"| {label} | {s3.REGISTERED_LEAVE_ONE_OUT[name]:.4f} |" in text
    assert "layers 41 down to 26, unflipped" in text
    assert "8954ae31" in text and "8954ae31" in (HERE / "run_studio_343.sh").read_text()


def test_leave_one_out_is_high_for_readers_of_one_text_and_low_slid():
    rng = np.random.default_rng(0)
    truth = _strokes(256, 384, seed=2, n=400)
    cells = np.ones(truth.shape, bool)
    models = {k: truth + rng.normal(0, 0.3, truth.shape) for k in s3.MODELS}
    out = s3.leave_one_out(models, cells)
    assert set(out) == set(s3.MODELS)
    for v in out.values():
        assert v["r"] > 0.5 and v["control_slid_largest_absolute"] < v["r"] / 2


def test_letter_boxes_count_studio_ink_inside_each_box():
    studio = np.zeros((40, 60))
    studio[5:15, 5:15] = 0.9  # box 1 inked
    u = np.zeros((40, 60))
    u[5:15, 5:10] = 1.0
    valid = np.ones((40, 60), bool)
    out = s3.letter_boxes(
        {
            "letters_area_px": [
                {"id": 1, "box": [5, 5, 15, 15]},
                {"id": 2, "box": [30, 20, 40, 30]},
            ]
        },
        studio,
        u,
        valid,
    )
    assert (
        out["boxes_scored"] == 2
        and out["boxes_where_studio_is_above_its_area_share"] == 1
    )
    assert (
        out["boxes"][0]["studio_ink_share"] == 1.0
        and out["boxes"][0]["u_drawn_share"] == 0.5
    )
    assert out["boxes"][1]["studio_ink_share"] == 0.0


def _synthetic(tmp_path):
    import argparse

    import cv2
    import tifffile
    import zarr

    rng = np.random.default_rng(1)
    h, w = 240, 400
    row0, row1, col0, col1 = 8, 232, 12, 388
    truth = _strokes(h, w, seed=3, n=80)
    render = np.full((66, h, w), 100, np.uint8)
    render[:, :4, :] = 0  # invalid rows outside the area
    zarr.open(str(tmp_path / "r.zarr"), mode="w").create_dataset(
        "0", data=render, chunks=(66, h, w)
    )
    sidecar = _sidecar(row0, row1, col0, col1, letters=[(20, 10, 40, 30)])
    (tmp_path / "side.json").write_text(json.dumps(sidecar))
    u = s3.to_reading(truth, sidecar)
    cv2.imwrite(
        str(tmp_path / "u.png"), np.round(np.clip(u, 0, 1) * 255).astype(np.uint8)
    )
    np.save(
        tmp_path / "f.npy",
        (0.8 * truth + rng.normal(0, 0.1, truth.shape)).astype(np.float32),
    )
    np.save(tmp_path / "rv.npy", rng.uniform(0, 1, truth.shape).astype(np.float32))
    maps = tmp_path / "maps"
    maps.mkdir()
    name = "concat"
    for model, suffix in s3.MODELS.items():
        noisy = np.clip(
            64 + 128 * (truth + rng.normal(0, 0.3, truth.shape)), 0, 255
        ).astype(np.uint8)
        if suffix.endswith(".png"):
            cv2.imwrite(
                str(maps / f"{name}{suffix}"), cv2.resize(noisy, (w // 2, h // 2))
            )
        else:
            tifffile.imwrite(maps / f"{name}{suffix}", noisy)
    return argparse.Namespace(
        out=tmp_path / "out.json", render=tmp_path / "r.zarr", sidecar=tmp_path / "side.json",
        ink_png=tmp_path / "u.png", studio=tmp_path / "f.npy", studio_reversed=tmp_path / "rv.npy",
        maps=maps, render_name=name, image=tmp_path / "img.png",
    )  # fmt: skip


def test_the_comparison_agrees_for_the_right_side_and_not_the_other(tmp_path):
    import cv2

    args = _synthetic(tmp_path)
    result = s3.compare(args)
    assert result["finding"] == 127 and result["layers"] == list(range(41, 25, -1))
    assert result["area_shape"] == [224, 376] and result["cell_share"] == 1.0
    reg = result["registered"]
    assert reg["r"] > 0.8 and abs(reg["control_wrong_side"]) < 0.2
    assert result["verdict"] == "STUDIO_343_AGREES"
    d = result["described"]
    assert d["studio_reversed_planes"]["r"] == reg["control_wrong_side"]
    assert set(d["leave_one_out"]) == set(s3.MODELS)
    assert d["letters"]["boxes_scored"] == 1
    image = cv2.imread(str(args.image), cv2.IMREAD_GRAYSCALE)
    assert image.shape == (2 * 224 + 12, 376)
    assert (tmp_path / "img_reversed.png").exists()


def test_a_studio_map_of_the_wrong_shape_does_not_run(tmp_path):
    args = _synthetic(tmp_path)
    np.save(args.studio, np.zeros((10, 10), np.float32))
    with pytest.raises(SystemExit, match="the render"):
        s3.compare(args)


def test_the_cli_measures_once(tmp_path):
    args = _synthetic(tmp_path)
    argv = ["compare", str(args.out), "--render", str(args.render), "--sidecar", str(args.sidecar),
            "--ink-png", str(args.ink_png), "--studio", str(args.studio), "--studio-reversed",
            str(args.studio_reversed), "--maps", str(args.maps), "--render-name", "concat"]  # fmt: skip
    assert s3.main(argv) == 0
    assert json.loads(args.out.read_text())["verdict"] == "STUDIO_343_AGREES"
    assert s3.main(argv) == 2


def test_the_run_script_runs_the_registered_steps_in_order_and_uploads_nothing():
    path = HERE / "run_studio_343.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
        assert word not in text
    steps = re.findall(r"^step (\w+)", text, flags=re.M)
    assert steps == ["check", "reference", "planes", "infer", "compare"]
    e2e = (ROOT / "repro/first_letters/pherc0211_control/run_studio_e2e.sh").read_text()
    for sha in ("W_SHA", "CODE_SHA"):
        mine = re.search(rf"^{sha}=(\w+)", text, flags=re.M).group(1)
        assert mine == re.search(rf"^{sha}=(\w+)", e2e, flags=re.M).group(1)
    assert (
        "--stride 64" in text and "--blend hann" in text and "--batch-size 32" in text
    )
    assert "--write-components" in text and "--reverse" in text
