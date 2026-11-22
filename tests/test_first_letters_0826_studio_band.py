"""Finding 125: the orientation rule on windings whose way is known, the per-winding summary, and the driver."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"


def _load():
    spec = importlib.util.spec_from_file_location(
        "studio_band_under_test", BAND / "studio_band.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sb = _load()


def _ring(path: Path, radius: float, reverse: bool = False) -> Path:
    """A cylinder of nodes round (500, 600), 20 voxels apart in z; `reverse` runs it the other way round."""
    import tifffile

    theta = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    if reverse:
        theta = theta[::-1]
    z = np.arange(6) * 20.0 + 8000
    tt, zz = np.meshgrid(theta, z)
    path.mkdir(parents=True)
    for axis, values in (
        ("x", 500 + radius * np.cos(tt)),
        ("y", 600 + radius * np.sin(tt)),
        ("z", zz),
    ):
        tifffile.imwrite(path / f"{axis}.tif", values.astype(np.float32))
    return path


def test_a_winding_run_the_other_way_round_gets_the_other_render(tmp_path):
    a = _ring(tmp_path / "w010.tifxyz", 100.0)
    b = _ring(tmp_path / "w011.tifxyz", 130.0, reverse=True)
    result = sb.orientation([a, b])
    assert result["centre_xyz"][:2] == [500.0, 600.0]
    shares = {
        n: e["share_of_normals_pointing_inward"] for n, e in result["windings"].items()
    }
    assert {round(v) for v in shares.values()} == {
        0,
        1,
    }  # one all inward, the other all outward
    renders = {n: e["render"] for n, e in result["windings"].items()}
    assert sorted(renders.values()) == ["flip", "keep"]
    assert (
        renders[min(shares, key=shares.get)] == "keep"
    )  # mostly outward: as the winner's PHerc. 211 surface


def test_the_summary_writes_an_image_a_contact_sheet_and_tile_numbers(tmp_path):
    import cv2
    import zarr

    maps = tmp_path / "maps"
    renders = tmp_path / "renders"
    maps.mkdir()
    prob = np.zeros((800, 1200), np.float32)
    prob[100:300, 100:500] = 0.9  # ink in the first tile row
    np.save(maps / "w020.npy", prob)
    layer = np.zeros((66, 800, 1200), np.uint8)
    layer[33, :, :1000] = 100  # rendered over the left 1,000 columns
    zarr.open(str(renders / "w020_66.zarr"), mode="w").create_dataset(
        "0", data=layer, chunks=(66, 800, 1200)
    )
    summary = sb.summarise(tmp_path / "out", maps, renders)["windings"]["w020"]
    assert summary["rendered_pixels"] == 800 * 1000
    assert summary["ink_share"] == round(200 * 400 / (800 * 1000), 4)
    # tiles of 380: two rows of two whole tiles inside the rendered 1,000 columns (the third column of tiles is cut)
    assert summary["tiles_scored"] == 4
    first = [t for t in summary["tiles"] if t["row"] == 0 and t["col"] == 0][0]
    assert first["ink_share"] == round(200 * 280 / 380**2, 4)
    image = cv2.imread(str(tmp_path / "out" / "images" / "w020.png"), 0)
    assert image.shape == prob.shape and image[200, 200] == 230
    assert (tmp_path / "out" / "contact_sheet.png").exists()
    assert json.loads((tmp_path / "out" / "summary.json").read_text())[
        "contact_sheet_order"
    ] == ["w020"]


def test_the_lines_are_the_registrations():
    assert (sb.TILE, sb.INK) == (380, 0.5)
    text = (
        ROOT / "docs/preregistration/2026-11-20_first_letters_0826_studio_band.md"
    ).read_text()
    assert (
        "flip a winding when more than half of its normals point toward the band's centre"
        in text
    )
    assert "our layers 41 down to 26" in text


def test_the_driver_reads_every_winding_and_keeps_going_past_a_failure():
    path = BAND / "run_studio_band.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl -T", "--upload-file", "rsync "):
        assert word not in text
    order = [
        "stage snap",
        "for_each flatten",
        "stage orient",
        "for_each render",
        "for_each studio",
        "stage summarise",
    ]
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)
    assert (
        "W_SHA=96b326286e38de99047f7cab36170c53749a18d5f43e5fde0c7c20f2980b0e90" in text
    )
    assert "--stride 64 --blend hann" in text and "--batch-size 32" in text
    assert (
        "grep -E '^w[0-9]+$'" in text
    )  # raw windings only: villa's _spliced twins are skipped
    assert 'LIVE=("${kept[@]}")' in text
