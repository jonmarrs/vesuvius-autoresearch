"""Does the detector read ink from slices the loop's model never sees?

The TimeSformer detector reads 26 slices (zarr 1-26, its band); the loop's
model reads 16. With depth_band [1, 27] and a 4-slice margin, the loop reads
24 slices from zarr z0 in 0-7 and keeps the middle 16: zarr [4, 20) to
[11, 27), that is, the detector's channels [3, 19) to [10, 26). Channels 0-2
are never in the loop's window. Finding 87 left this difference untested.

Read-only, CPU only, one thread. On control B's 400 random stride-32 windows
of Fr143 (seed 0, reproduced from reports/detector_random_window_control.json,
else the run aborts), the detector is scored with all 26 channels and with
only a 16-channel window kept, at the loop's lowest (3), middle (7) and
highest (10) offsets. The other 10 channels are filled from the kept 16:
  reflect (primary): mirrored about the window's ends, so the fill is real
      texture from the same location;
  edge (sensitivity): the window's end slices repeated.

Pre-registered (committed before the first run). drop = full AUC - windowed
AUC, reflect fill, per offset:
  every drop <= 0.02: the detector does not need the slices outside any window
      the loop reads; the 26-vs-16 difference does not explain the loop's gap
      to the detector;
  every drop >= 0.05: every window the loop reads loses ink signal the
      detector uses; the 26-vs-16 difference is a candidate cause, worth a
      loop test of num_layers (an owner decision);
  otherwise: it depends on the window's position; reported per offset.
Caveats: a fill is input the detector never saw in training, so a drop
overstates the information lost; a small drop is the strong result. A large
drop shows what this detector uses, not what a model trained on 16 slices
could learn. Also reported, not read: the edge-fill drops, and val_f1 and AP
lift for every variant.

    CUDA_VISIBLE_DEVICES= UV_NO_SYNC=1 uv run python scripts/detector_depth_ablation.py \
        --out reports/detector_depth_ablation.json
"""

import argparse
import json
import os
import subprocess
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # before torch: never touch the loop's GPU

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
import zarr  # noqa: E402
from PIL import Image  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

from scripts.detector_on_loop_sample import (  # noqa: E402
    DETECTOR,
    ZARR_SLICE_0_LAYER,
    card,
    sha256,
)
from scripts.detector_random_window_control import SEED, WINDOWS  # noqa: E402
from scripts.training.config import ExperimentConfig  # noqa: E402
from vesuvius_autoresearch.detector.config import DetectorConfig  # noqa: E402
from vesuvius_autoresearch.detector.model import DetectorModel  # noqa: E402

CONTROL = "reports/detector_random_window_control.json"
KEPT = 16  # config.json num_layers
OFFSETS = (3, 7, 10)  # the loop's lowest, middle and highest window
FILLS = ("reflect", "edge")
BATCH = 32
REPRODUCE = 1e-6

Image.MAX_IMAGE_PIXELS = None


def random_windows(mask, size, stride, seed, count):
    """Control B's draw: stride-aligned windows wholly inside the mask."""
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
    pick = np.random.default_rng(seed).choice(len(candidates), count, replace=False)
    return [tuple(int(v) for v in candidates[i]) for i in sorted(pick)], len(candidates)


def windowed(x, offset, fill):
    """Keep channels [offset, offset + KEPT) of x (N, C, H, W); fill the rest."""
    kept = x[:, offset : offset + KEPT]
    pad = ((0, 0), (offset, x.shape[1] - KEPT - offset), (0, 0), (0, 0))
    return np.pad(kept, pad, mode=fill)


def variants(channels):
    yield "full", None, None
    for fill in FILLS:
        for offset in OFFSETS:
            if offset + KEPT > channels:
                raise ValueError(f"offset {offset} runs past {channels} channels")
            yield f"{fill}_{offset}", offset, fill


def main(out_path, detector):
    torch.set_num_threads(1)  # the loop's data pipeline needs the other cores
    control = json.load(open(CONTROL))
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
    size = cfg.size

    origins, n_candidates = random_windows(mask, size, cfg.stride, SEED, WINDOWS)
    with_ink = int(sum(ink[y : y + size, x : x + size].any() for y, x in origins))
    if (n_candidates, with_ink) != (
        control["candidate_windows"],
        control["windows_with_ink"],
    ):
        raise RuntimeError("the window draw does not reproduce control B's")

    names = [name for name, _, _ in variants(cfg.in_chans)]
    probs = {name: [] for name in names}
    with torch.no_grad():
        for s in range(0, len(origins), BATCH):
            chunk = origins[s : s + BATCH]
            x = (
                np.stack(
                    [
                        np.asarray(volume[layers, y : y + size, x0 : x0 + size])
                        for y, x0 in chunk
                    ]
                ).astype(np.float32)
                / 255.0
            )
            for name, offset, fill in variants(cfg.in_chans):
                xv = x if offset is None else windowed(x, offset, fill)
                logits = model(torch.from_numpy(np.ascontiguousarray(xv))[:, None])
                ups = F.interpolate(
                    logits, size=(size, size), mode="bilinear", align_corners=False
                )
                probs[name].extend(torch.sigmoid(ups)[:, 0].numpy())
            print(f"{s + len(chunk)}/{len(origins)} windows", flush=True)

    labels = np.stack([ink[y : y + size, x : x + size] for y, x in origins])
    labels = labels.astype(np.uint8).ravel()
    cards = {name: card(np.stack(probs[name]).ravel(), labels) for name in names}
    want = control["cards"]["detector_single_window"]
    for key in ("val_f1", "roc_auc", "ap_prevalence_lift"):
        if abs(cards["full"][key] - want[key]) > REPRODUCE:
            raise RuntimeError(f"the full-depth {key} does not reproduce control B")

    full_auc = cards["full"]["roc_auc"]
    drops = {
        name: full_auc - cards[name]["roc_auc"] for name in names if name != "full"
    }
    primary = [drops[f"reflect_{o}"] for o in OFFSETS]
    if all(d <= 0.02 for d in primary):
        reading = "no drop: depth outside the loop's window does not explain its gap"
    elif all(d >= 0.05 for d in primary):
        reading = "drop at every offset: 26 vs 16 slices is a candidate cause"
    else:
        reading = "depends on the window's position"
    result = {
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=_REPO
        ).stdout.strip(),
        "detector_checkpoint": DETECTOR,
        "detector_sha256": sha256(detector),
        "validation_uri": config.val_uri,
        "windows": len(origins),
        "seed": SEED,
        "kept_channels": KEPT,
        "offsets": list(OFFSETS),
        "n_pixels": int(labels.size),
        "ink_prevalence": float(labels.mean()),
        "cards": cards,
        "auc_drops": drops,
        "reading": reading,
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({k: result[k] for k in ("auc_drops", "reading")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="JSON path to write")
    parser.add_argument("--detector", default=DETECTOR, help="detector checkpoint")
    args = parser.parse_args()
    main(args.out, args.detector)
