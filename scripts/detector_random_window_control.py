"""Control for detector_on_loop_sample: does the same detector pipeline read ink
on windows drawn across the whole fragment?

On the loop's validation sample (ink-containing patches, ink prevalence ~0.58)
the detector scored AUC 0.58-0.61, against 0.709 over the whole of Fr143. This
scores the same model through the same window reader (scripts/
detector_on_loop_sample.detector_windows) on random stride-32 windows that lie
inside the fragment mask, ink or not.

Pre-registered reading (committed before the first run):
  single-window AUC >= 0.65: the pipeline reads ink, so the low numbers on the
      loop's sample come from that sample;
  single-window AUC < 0.60: the pipeline is suspect and the loop-sample result
      cannot be used.
It also reports, on these windows, the detector's val_f1 against calling every
pixel ink, as a preview of a sample that keeps ink-free patches.

    CUDA_VISIBLE_DEVICES= UV_NO_SYNC=1 uv run python scripts/detector_random_window_control.py \
        --out reports/detector_random_window_control.json [--detector PATH]
"""

import argparse
import json
import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # before torch: never touch the loop's GPU

import numpy as np  # noqa: E402
import torch  # noqa: E402
import zarr  # noqa: E402
from PIL import Image  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

from scripts.detector_on_loop_sample import (  # noqa: E402
    DETECTOR,
    ZARR_SLICE_0_LAYER,
    card,
    detector_windows,
    sha256,
)
from scripts.training.config import ExperimentConfig  # noqa: E402
from vesuvius_autoresearch.detector.config import DetectorConfig  # noqa: E402
from vesuvius_autoresearch.detector.model import DetectorModel  # noqa: E402

WINDOWS = 400
SEED = 0

Image.MAX_IMAGE_PIXELS = None


def main(out_path, detector):
    torch.set_num_threads(1)  # the loop's data pipeline needs the other cores
    config = ExperimentConfig.load("config.json")
    cfg = DetectorConfig()
    model = DetectorModel.load_from_checkpoint(
        detector, cfg=cfg, pred_shape=(1, 1), weights_only=False, map_location="cpu"
    ).eval()
    start = cfg.start_idx - ZARR_SLICE_0_LAYER
    layers = slice(start, start + cfg.in_chans)
    volume = zarr.open(config.val_uri, "r")
    volume = volume["0"] if isinstance(volume, zarr.Group) else volume
    frag_dir = os.path.dirname(config.val_uri)
    mask = np.asarray(Image.open(os.path.join(frag_dir, "mask.png"))) > 0
    ink = np.asarray(Image.open(os.path.join(frag_dir, "inklabels.png"))) > 0
    size, stride = cfg.size, cfg.stride

    # Every stride-32 window wholly inside the mask, as detector/infer.py tiles.
    h, w = mask.shape
    padded = np.pad(mask.astype(np.int32), ((1, 0), (1, 0)))
    integral = padded.cumsum(0, dtype=np.int32).cumsum(1, dtype=np.int32)
    ys = np.arange(0, h - size + 1, stride)
    xs = np.arange(0, w - size + 1, stride)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    inside = (
        integral[yy + size, xx + size]
        - integral[yy, xx + size]
        - integral[yy + size, xx]
        + integral[yy, xx]
    ) == size * size
    candidates = np.stack([yy[inside], xx[inside]], axis=1)
    pick = np.random.default_rng(SEED).choice(len(candidates), WINDOWS, replace=False)
    origins = [tuple(int(v) for v in candidates[i]) for i in sorted(pick)]

    probs = detector_windows(model, volume, layers, origins, size)
    labels = np.stack([ink[y : y + size, x : x + size] for y, x in origins])
    labels = labels.astype(np.uint8).ravel()
    prevalence = float(labels.mean())
    cards = {
        "detector_single_window": card(np.stack(probs).ravel(), labels),
        "constant_all_ink": card(np.ones(labels.shape, np.float32), labels),
    }
    floor = 2 * prevalence / (1 + prevalence)
    result = {
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_REPO
        ).stdout.strip(),
        "detector_checkpoint": DETECTOR,
        "detector_sha256": sha256(detector),
        "validation_uri": config.val_uri,
        "candidate_windows": int(len(candidates)),
        "windows": WINDOWS,
        "seed": SEED,
        "windows_with_ink": int(
            sum(ink[y : y + size, x : x + size].any() for y, x in origins)
        ),
        "n_pixels": int(labels.size),
        "ink_prevalence": prevalence,
        "all_ink_f1": floor,
        "cards": cards,
        "margins_over_all_ink": {k: v["val_f1"] - floor for k, v in cards.items()},
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="JSON path to write")
    parser.add_argument("--detector", default=DETECTOR, help="detector checkpoint")
    args = parser.parse_args()
    main(args.out, args.detector)
