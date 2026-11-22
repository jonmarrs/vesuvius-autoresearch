"""Finding 129, amendment 1: the band read renders the 18 layers it reads (24 to 41 of the 66), not all 66.

The renderer places layer k of an n-layer render at (k - (n - 1) / 2) along the normal, so an 18-layer render holds
layers 24 to 41 of the 66-layer one; on three of PHerc. 0826's windings they were byte-identical."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
BAND = ROOT / "repro/first_letters/eligible_band"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


se = _load(
    "studio_e2e_thin", ROOT / "repro/first_letters/pherc0211_control/studio_e2e.py"
)
sb = _load("studio_band_thin", BAND / "studio_band.py")


def _render(path: Path, n: int, shape=(8, 12)) -> Path:
    """A centred n-layer render whose every pixel of each layer holds that layer's index in the 66-layer frame."""
    import zarr

    first = (66 - n) // 2
    data = np.stack([np.full(shape, first + i, np.uint8) for i in range(n)])
    zarr.open(str(path), mode="w").create_dataset("0", data=data, chunks=(n, *shape))
    return path


@pytest.mark.parametrize(
    ("n", "k", "index"),
    [(66, 33, 33), (18, 24, 0), (18, 33, 9), (18, 41, 17), (20, 41, 18)],
)
def test_a_layer_of_the_66_layer_frame_is_found_in_a_centred_render(n, k, index):
    assert se.frame_index(n, k) == index


@pytest.mark.parametrize(
    ("n", "k"), [(16, 41), (16, 24), (18, 23), (18, 42), (17, 33), (68, 33), (0, 33)]
)
def test_a_layer_outside_the_render_or_an_uncentred_count_is_refused(n, k):
    with pytest.raises(ValueError):
        se.frame_index(n, k)


def test_studios_planes_from_18_layers_are_those_from_66(tmp_path):
    se.planes_cmd(_render(tmp_path / "a_66.zarr", 66), tmp_path / "a.npy")
    se.planes_cmd(_render(tmp_path / "b_18.zarr", 18), tmp_path / "b.npy")
    a, b = np.load(tmp_path / "a.npy"), np.load(tmp_path / "b.npy")
    assert np.array_equal(a, b) and a[:, 0, 0].tolist() == list(range(41, 25, -1))
    with pytest.raises(SystemExit):
        se.planes_cmd(_render(tmp_path / "c_16.zarr", 16), tmp_path / "c.npy")


def test_the_summary_finds_the_surface_layer_in_an_18_layer_render(tmp_path):
    import zarr

    maps, renders = tmp_path / "maps", tmp_path / "renders"
    maps.mkdir()
    np.save(maps / "w020.npy", np.full((400, 400), 0.9, np.float32))
    data = np.zeros((18, 400, 400), np.uint8)
    data[9, :, :200] = 100  # layer 33 of the 66: rendered over the left 200 columns
    data[8, :, :] = 100  # layer 32: everywhere, and not the surface layer
    zarr.open(str(renders / "w020_18.zarr"), mode="w").create_dataset(
        "0", data=data, chunks=(18, 400, 400)
    )
    summary = sb.summarise(tmp_path / "out", maps, renders)["windings"]["w020"]
    assert summary["rendered_pixels"] == 400 * 200


def test_the_summary_refuses_two_renders_of_one_winding(tmp_path):
    maps, renders = tmp_path / "maps", tmp_path / "renders"
    maps.mkdir()
    np.save(maps / "w020.npy", np.zeros((8, 12), np.float32))
    _render(renders / "w020_18.zarr", 18)
    _render(renders / "w020_66.zarr", 66)
    with pytest.raises(SystemExit):
        sb.summarise(tmp_path / "out", maps, renders)


@pytest.mark.parametrize("bad", ["17", "16", "68", "x", "0"])
def test_the_render_refuses_a_layer_count_that_does_not_hold_studios_layers(
    tmp_path, bad
):
    env = {"PATH": "/usr/bin:/bin", "FL_ROOT": str(tmp_path), "RENDER_SLICES": bad}
    done = subprocess.run(["bash", str(BAND / "run_render.sh"), "arm", "w001"], env=env, capture_output=True,
                          text=True)  # fmt: skip
    assert done.returncode == 2 and "RENDER_SLICES" in done.stderr


def test_the_render_names_its_output_by_its_layer_count_and_defaults_to_66():
    text = (BAND / "run_render.sh").read_text()
    assert "SLICES=${RENDER_SLICES:-66}" in text
    assert "OUT=$R/work/render_$ARM/${W}_${SLICES}.zarr" in text
    assert '--num-slices "$SLICES" --slice-step 1' in text


def test_the_band_read_renders_and_reads_18_layers():
    text = (BAND / "run_studio_band.sh").read_text()
    assert "SLICES=18" in text
    render = text[
        text.index("render_one() {") : text.index("\n}\n", text.index("render_one() {"))
    ]
    assert render.count('RENDER_SLICES="$SLICES" bash "$HERE/run_render.sh"') == 2
    assert '"$R/work/render_$ARM/${1}_${SLICES}.zarr"' in text
    assert "_66.zarr" not in text


def test_finding_129_registers_the_change_before_its_data():
    reg = (
        ROOT / "docs/preregistration/2026-11-20_first_letters_0813_band_read.md"
    ).read_text()
    amendment = reg[reg.index("## Amendment 1") :]
    assert "before any input of PHerc. 0813 has been downloaded" in amendment
    assert "`RENDER_SLICES`" in amendment and "18 layers" in amendment
    assert "Time is not claimed" in amendment
