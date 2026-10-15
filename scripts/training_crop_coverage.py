"""Which labelled pixels of a training volume the training crops ever contain.

The loop: every catalogue entry is drawn by VesuviusLabeledDataset.__getitem__
itself, built as train.py builds the training dataset, with a volume that
records the crop instead of reading CT. Built without a seed (before
2026-10-15), entry i had the same crop in every run; with the run's sampling
seed, each run draws its own. The detector: the 64 px subtiles of
detector/data.py's _tiles_for_fragment, with an image that returns each
subtile's origin instead of its pixels.

CPU only, reads the labels and mask; the CT is not read. Run from the
repository root: the fragment path is relative, as in the loop's config, and
names the cached catalogue the loop reads.

    python scripts/training_crop_coverage.py --out reports/training_crop_coverage.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vesuvius_autoresearch.core.inference_constants import DEPTH_MARGIN  # noqa: E402
from vesuvius_autoresearch.core.vesuvius_loader import (  # noqa: E402
    VesuviusLabeledDataset,
)
from vesuvius_autoresearch.detector import data as detector_data  # noqa: E402
from vesuvius_autoresearch.detector.config import DetectorConfig  # noqa: E402

FRAGMENT = "local_data/PHercParis2Fr47"
# Per-run seeds for the cumulative coverage: drawn once, as train.py draws a
# run's sampling seed (31 bits), from a fixed generator so the report repeats.
RUN_SEEDS = [
    int(s) for s in np.random.default_rng(20261015).integers(0, 2**31 - 1, size=8)
]


class CropRecorder:
    """Stands in for the CT volume: records each (z0, y0, x0) read."""

    def __init__(self, shape):
        self.shape = shape
        self.uri = "crop-recorder"
        self.reads: list[tuple[int, int, int]] = []

    def __getitem__(self, key):
        z, y, x = key
        self.reads.append((z.start, y.start, x.start))
        return torch.zeros(
            (z.stop - z.start, y.stop - y.start, x.stop - x.start), dtype=torch.uint8
        )


def training_dataset(fragment: str, patch_size=64, num_layers=16, depth_band=(1, 27)):
    """The labeled training dataset as train.py's get_dataloader builds it."""
    return VesuviusLabeledDataset(
        os.path.join(fragment, "surface_volume.zarr"),
        os.path.join(fragment, "inklabels.png"),
        os.path.join(fragment, "mask.png"),
        patch_size,
        num_layers + 2 * DEPTH_MARGIN,
        depth_band=list(depth_band),
        depth_margin=DEPTH_MARGIN,
    )


def loop_crops(dataset, seed) -> np.ndarray:
    """Each entry's (z0, y0, x0) as dataset.__getitem__ draws it for ``seed``."""
    recorder = CropRecorder(dataset.shape)
    volume, dataset.volume, dataset.seed = dataset.volume, recorder, seed
    try:
        for idx in range(len(dataset)):
            dataset[idx]
    finally:
        dataset.volume = volume
    if len(recorder.reads) != len(dataset):
        raise RuntimeError("an entry's crop was not recorded")
    return np.array(recorder.reads, dtype=np.int64)


class SubtileOrigins:
    """Stands in for the detector's layer stack: a subtile is its origin."""

    def __init__(self, shape):
        self.shape = shape

    def __getitem__(self, key):
        return (key[0].start, key[1].start)


def detector_subtiles(labels, frag_mask, cfg=None) -> list[tuple[int, int]]:
    """The training subtiles' origins (with repeats, as an epoch draws them)."""
    cfg = cfg or DetectorConfig()
    ts = cfg.tile_size
    pad = [(0, ts - labels.shape[0] % ts), (0, ts - labels.shape[1] % ts)]
    padded_mask = np.pad(frag_mask, pad, constant_values=0)
    stand_in = SubtileOrigins(padded_mask.shape)

    def read(cfg, fragment_id):  # read_image_mask's return, without the CT
        return stand_in, labels, padded_mask

    original, detector_data.read_image_mask = detector_data.read_image_mask, read
    try:
        origins, _, _, _ = detector_data._tiles_for_fragment(cfg, "fragment", False)
    finally:
        detector_data.read_image_mask = original
    return origins


def coverage(origins, size, labels, mask) -> dict:
    """Share of mask and ink pixels inside at least one size x size crop."""
    covered = np.zeros(labels.shape, dtype=bool)
    for y, x in origins:
        covered[y : y + size, x : x + size] = True
    ink = labels >= 0.5
    return {
        "mask_pixels": round(float(covered[mask > 0].mean()), 4),
        "ink_pixels": round(float(covered[ink].mean()), 4),
    }


def ink_share(origins, size, labels) -> float:
    """Mean label over the crops: the ink share of the pixels trained on."""
    return round(
        float(np.mean([labels[y : y + size, x : x + size].mean() for y, x in origins])),
        4,
    )


def measure(fragment: str) -> dict:
    dataset = training_dataset(fragment)
    labels, mask, size = dataset.labels, dataset.mask, dataset.patch_size
    fixed = loop_crops(dataset, None)
    lateral = [(int(y), int(x)) for _, y, x in fixed]
    runs, cumulative = [], []
    for seed in RUN_SEEDS:
        crops = loop_crops(dataset, seed)
        runs.append([(int(y), int(x)) for _, y, x in crops])
        cumulative.append(
            {"runs": len(runs), **coverage(sum(runs, []), size, labels, mask)}
        )
    subtiles = detector_subtiles(labels, mask)
    return {
        "fragment": fragment,
        "loop": {
            "entries": len(dataset),
            "depth_band": [1, 27],
            "read_depth_starts": sorted({int(z) for z, _, _ in fixed}),
            "ink_share": ink_share(lateral, size, labels),
            "entries_without_ink": round(
                float(
                    np.mean(
                        [
                            labels[y : y + size, x : x + size].max() == 0
                            for y, x in lateral
                        ]
                    )
                ),
                4,
            ),
            "without_seed_every_run": coverage(lateral, size, labels, mask),
            "run_seeds": RUN_SEEDS,
            "one_run": coverage(runs[0], size, labels, mask),
            "with_run_seeds_cumulative": cumulative,
        },
        "detector": {
            "subtiles_per_epoch": len(subtiles),
            "distinct_subtiles": len(set(subtiles)),
            "ink_share": ink_share(subtiles, DetectorConfig().size, labels),
            "every_epoch": coverage(set(subtiles), DetectorConfig().size, labels, mask),
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fragment", default=FRAGMENT)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = measure(args.fragment)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)
        f.write("\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
