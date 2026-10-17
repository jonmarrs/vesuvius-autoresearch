"""Finding 86's option "add ink-free patches back", measured: the loop's 400-patch
validation draw with its 303 ink-free patches kept.

Read-only, CPU only, one thread. The same 400 catalogue entries the loop draws
(protocol from config.json, seed 42); the loop keeps only the 97 that contain
ink. Here every patch counts. Scored, pooled over pixels with the detector's
metric contract:

- the loop's incumbent, best_model.pt, through the loop's input path (the read
  window's middle num_layers slices, its checkpoint's input settings); on the
  97 ink-containing patches it must reproduce the loop's own probabilities;
- the TimeSformer detector on each patch's own window (layers 17-42, /255);
- calling every pixel ink.

Pre-registered reading (committed before the first run): if the detector's
val_f1 margin over the all-ink F1 exceeds +0.03 (train.F1_NOISE_TOLERANCE until 2026-10-17) and
the incumbent's does not, keeping ink-free patches lets the loop's F1 tell a
model of the detector's quality from the incumbent; otherwise that option alone
does not fix the metric. AUC and AP lift are reported beside it.

    CUDA_VISIBLE_DEVICES= UV_NO_SYNC=1 uv run python scripts/detector_on_full_v2_sample.py \
        --out reports/detector_on_full_v2_sample.json [--detector PATH]
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
from torch.utils.data import default_collate  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "scripts", "training"))

from train import DEPTH_MARGIN, ExperimentConfig  # noqa: E402

from scripts.detector_on_loop_sample import (  # noqa: E402
    DETECTOR,
    ZARR_SLICE_0_LAYER,
    card,
    check_origins,
    detector_windows,
    loop_incumbent,
    patch_origin,
    sha256,
)
from scripts.training.promotion import (  # noqa: E402
    INK_ONLY_PROTOCOL,
    validation_indices,
    validation_protocol,
)
from vesuvius_autoresearch.core.checkpoint_tools import (  # noqa: E402
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)
from vesuvius_autoresearch.detector.config import DetectorConfig  # noqa: E402
from vesuvius_autoresearch.detector.model import DetectorModel  # noqa: E402

BATCH = 4


def main(out_path, detector):
    torch.set_num_threads(1)  # the loop's data pipeline needs the other cores
    config = ExperimentConfig.load("config.json")
    dataset, kept_probs, _, diag, chk = loop_incumbent(config)
    model, settings, _ = load_tool_checkpoint("best_model.pt", torch.device("cpu"))
    model.eval()

    indices = validation_indices(len(dataset))
    probs, targets, coords, has_ink = [], [], [], []
    with torch.no_grad():
        for s in range(0, len(indices), BATCH):
            chunk = [int(i) for i in indices[s : s + BATCH]]
            x_raw, target, _fiber = default_collate([dataset[i] for i in chunk])
            x = x_raw[:, :, DEPTH_MARGIN : DEPTH_MARGIN + config.num_layers]
            p = ink_probabilities(model, validate_batch(x, settings)).float()
            if target.dim() == 3:
                target = target.unsqueeze(1)
            for j, i in enumerate(chunk):
                probs.append(p[j : j + 1])
                targets.append(target[j : j + 1].float())
                coords.append(patch_origin(dataset, i))
                has_ink.append(float(target[j].float().sum()) >= 1.0)
    kept = [p for p, ink in zip(probs, has_ink, strict=True) if ink]
    if len(kept) != len(kept_probs) or not all(
        torch.allclose(a, b, atol=1e-5) for a, b in zip(kept, kept_probs, strict=True)
    ):
        raise RuntimeError(
            "the ink-containing patches do not reproduce the loop's scores"
        )
    check_origins(config.val_uri, coords, targets)

    cfg = DetectorConfig()
    det = DetectorModel.load_from_checkpoint(
        detector, cfg=cfg, pred_shape=(1, 1), weights_only=False, map_location="cpu"
    ).eval()
    start = cfg.start_idx - ZARR_SLICE_0_LAYER
    volume = zarr.open(config.val_uri, "r")
    volume = volume["0"] if isinstance(volume, zarr.Group) else volume
    det_maps = detector_windows(
        det, volume, slice(start, start + cfg.in_chans), coords, cfg.size
    )

    labels = (torch.cat(targets).numpy().ravel() > 0.5).astype(np.uint8)
    prevalence = float(labels.mean())
    floor = 2 * prevalence / (1 + prevalence)
    cards = {
        "loop_incumbent": card(torch.cat(probs).numpy().ravel(), labels),
        "detector_single_window": card(np.stack(det_maps).ravel(), labels),
        "constant_all_ink": card(np.ones(labels.shape, np.float32), labels),
    }
    result = {
        "protocol": validation_protocol(config.depth_band, base=INK_ONLY_PROTOCOL),
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_REPO
        ).stdout.strip(),
        "best_model_sha256": sha256("best_model.pt"),
        "best_model_val_protocol": chk.get("val_protocol"),
        "detector_checkpoint": DETECTOR,
        "detector_sha256": sha256(detector),
        "patches": len(indices),
        "patches_with_ink": int(sum(has_ink)),
        "loop_usable_patches": diag["usable_patches"],
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
