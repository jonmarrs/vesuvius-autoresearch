"""scripts/training_crop_coverage.py: the crops each pipeline trains on, drawn by
the pipelines' own code, and the report's numbers where train.py quotes them."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import zarr
from PIL import Image

from scripts import training_crop_coverage as coverage_script
from vesuvius_autoresearch.core import vesuvius_loader

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "reports" / "training_crop_coverage.json"


@pytest.fixture
def fragment(tmp_path, monkeypatch):
    """A 33-slice fragment (the loop's band [1,27) with its 4-slice margins),
    ink in the middle, read from its directory as the loop reads Fr47."""
    monkeypatch.setattr(vesuvius_loader, "DEFAULT_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "frag").mkdir()
    volume = zarr.open(
        str(tmp_path / "frag" / "surface_volume.zarr"),
        mode="w",
        shape=(33, 384, 384),
        chunks=(33, 128, 128),
        dtype="u1",
    )
    volume[:] = 90
    labels = np.zeros((384, 384), np.uint8)
    labels[128:256, 128:256] = 255
    Image.fromarray(labels).save(tmp_path / "frag" / "inklabels.png")
    Image.fromarray(np.full((384, 384), 255, np.uint8)).save(
        tmp_path / "frag" / "mask.png"
    )
    return "frag"


def test_the_loop_crops_are_the_datasets_own_reads(fragment):
    dataset = coverage_script.training_dataset(fragment)
    fixed = coverage_script.loop_crops(dataset, None)
    assert len(fixed) == len(dataset) > 1
    # The draw is the dataset's: the same crops on every call without a seed
    # (the seed counts as 0), others with one, all inside the volume and band.
    assert np.array_equal(fixed, coverage_script.loop_crops(dataset, None))
    assert np.array_equal(fixed, coverage_script.loop_crops(dataset, 0))
    assert not np.array_equal(fixed, coverage_script.loop_crops(dataset, 977))
    z, y, x = fixed.T
    assert z.min() >= 0 and z.max() <= 31 - 24
    assert y.min() >= 0 and y.max() <= 384 - 64
    assert x.min() >= 0 and x.max() <= 384 - 64
    # The recording volume stood in only while the crops were drawn.
    assert not isinstance(dataset.volume, coverage_script.CropRecorder)


def test_the_detector_subtiles_are_its_own_tiling():
    """Ink only in [0,64)^2 of a 512 px fragment: the 256 px tiles at stride 32
    that hold it start at 0 or 32 on each axis; 4 tiles of 16 subtiles each."""
    labels = np.zeros((512, 512), np.float32)
    labels[:64, :64] = 1.0
    mask = np.full((512, 512), 255, np.uint8)
    subtiles = coverage_script.detector_subtiles(labels, mask)
    assert len(subtiles) == 64
    starts = sorted({a + k for a in (0, 32) for k in (0, 64, 128, 192)})
    assert set(subtiles) == {(y, x) for y in starts for x in starts}


def test_coverage_counts_pixels_inside_any_crop():
    labels = np.zeros((8, 8), np.float32)
    labels[0, :4] = 1.0
    mask = np.ones((8, 8), np.uint8)
    result = coverage_script.coverage([(0, 0), (0, 1)], 2, labels, mask)
    assert result == {"mask_pixels": round(6 / 64, 4), "ink_pixels": 0.75}


def test_the_report_backs_the_figure_train_py_quotes():
    report = json.loads(REPORT.read_text())
    loop = report["loop"]
    assert report["fragment"] == coverage_script.FRAGMENT
    assert loop["entries"] == 7345
    assert loop["run_seeds"] == coverage_script.RUN_SEEDS
    fixed = loop["without_seed_every_run"]["ink_pixels"]
    source = (REPO / "scripts" / "training" / "train.py").read_text()
    assert f"held {fixed * 100:.1f}% of its labelled ink pixels" in source
    cumulative = [c["ink_pixels"] for c in loop["with_run_seeds_cumulative"]]
    assert cumulative[0] == loop["one_run"]["ink_pixels"]
    assert cumulative == sorted(cumulative) and cumulative[3] > 0.99 > fixed
    assert report["detector"]["every_epoch"]["ink_pixels"] == 1.0
