"""Can the loop's promotion metric reward a model that reads ink?

Read-only, CPU only (the loop holds the GPU). Scores, on the loop's own
validation sample (protocol from config.json, seed 42, ink-containing patches,
pooled pixels, the detector's metric contract):

- the loop's incumbent, best_model.pt, exactly as the loop scores it;
- the project's TimeSformer detector (models/detector/detector_epoch=7.ckpt,
  held-out pixel AUC 0.709 on the whole of Fr143), on each patch's own 64 px
  window and its own 26 layers (17-42, zarr slices 1-26), /255 as trained;
- the same detector with its normal tiled inference (stride-32 windows that lie
  inside the fragment mask, uniform average) restricted to each patch;
- calling every pixel ink (F1 = 2p/(1+p) at every threshold).

Pre-registered reading (committed before the first run): the primary number is
the detector's single-window val_f1 margin over the sample's all-ink F1.
  margin > +0.03 (train.F1_NOISE_TOLERANCE until 2026-10-17): the metric can reward a model that
      reads ink, and the loop's promotion bar is reachable by a model this good;
  |margin| <= 0.01: F1 on this sample cannot tell such a model from a constant;
  otherwise: weak, reported as such.
Caveat: the detector's epoch was chosen by AUC on Fr143, the loop's validation
fragment, so its scores here lean optimistic.

    CUDA_VISIBLE_DEVICES= UV_NO_SYNC=1 uv run python scripts/detector_on_loop_sample.py \
        --out reports/detector_on_loop_sample.json [--detector PATH]
"""

import argparse
import hashlib
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
sys.path.insert(0, os.path.join(_REPO, "scripts", "training"))

from train import (  # noqa: E402
    ExperimentConfig,
    build_validation_dataset,
    collect_validation_predictions,
)

from scripts.reevaluate_best_model import RECORDED_INPUT_SETTINGS  # noqa: E402
from scripts.training.promotion import (  # noqa: E402
    INK_ONLY_PROTOCOL,
    validation_indices,
    validation_label_path,
    validation_protocol,
)
from vesuvius_autoresearch.core.checkpoint_tools import (  # noqa: E402
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)
from vesuvius_autoresearch.detector.config import DetectorConfig  # noqa: E402
from vesuvius_autoresearch.detector.metrics import segmentation_metrics  # noqa: E402
from vesuvius_autoresearch.detector.model import DetectorModel  # noqa: E402

DETECTOR = "models/detector/detector_epoch=7.ckpt"
ZARR_SLICE_0_LAYER = 16  # reports/ink_depth_profile.json (finding 87)
KEYS = (
    "val_f1",
    "best_threshold",
    "precision",
    "recall",
    "pred_positive_rate",
    "average_precision",
    "ap_prevalence_lift",
    "roc_auc",
)

Image.MAX_IMAGE_PIXELS = None


def card(probs, labels):
    m = segmentation_metrics(probs, labels, np.ones_like(labels, dtype=bool))
    return {k: float(m.get(k, float("nan"))) for k in KEYS}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def loop_incumbent(config):
    """The loop's own scoring of best_model.pt (as scripts/reevaluate_best_model.py)."""
    model, settings, chk = load_tool_checkpoint("best_model.pt", torch.device("cpu"))
    for name, value in settings.items():
        setattr(config, name, value)
    stored = chk.get("config", {})
    for name in RECORDED_INPUT_SETTINGS:
        if name in stored:
            setattr(config, name, stored[name])
    dataset = build_validation_dataset(config)
    torch.manual_seed(42)
    probs, targets, diag = collect_validation_predictions(
        model,
        dataset,
        config.num_layers,
        torch.device("cpu"),
        batch_size=config.batch_size,
        amp_enabled=False,
        probabilities=lambda net, x: ink_probabilities(
            net, validate_batch(x, settings)
        ),
        protocol=validation_protocol(config.depth_band, base=INK_ONLY_PROTOCOL),
    )
    if not diag["complete"]:
        raise RuntimeError("incomplete validation sample; nothing computed")
    return dataset, probs, targets, diag, chk


def patch_origin(dataset, idx):
    """Where dataset[idx] reads in the plane: valid_coords[idx] moved by the
    loader's per-patch jitter (VesuviusLabeledDataset.__getitem__), which
    validation leaves on.

    Finding 88 first read the detector at valid_coords itself, a median 16 px
    and up to half a patch away from the targets it was scored against
    (corrected 2026-10-14). check_origins verifies the result on the labels.
    """
    y0, x0 = (int(v) for v in dataset.valid_coords[idx])
    if not getattr(dataset, "jitter", True):
        return y0, x0
    rng = np.random.RandomState(idx + (dataset.seed or 0))
    size = dataset.patch_size
    half = size // 2
    y = max(0, min(dataset.shape[1] - size, y0 + rng.randint(-half, half + 1)))
    x = max(0, min(dataset.shape[2] - size, x0 + rng.randint(-half, half + 1)))
    return y, x


def check_origins(val_uri, origins, targets):
    """Every target must be the label image at its origin, or the detector's
    windows are not the patches it is scored on."""
    labels = np.asarray(Image.open(validation_label_path(val_uri)))
    labels = labels > (127 if labels.max() > 1 else 0)
    for (y, x), target in zip(origins, targets, strict=True):
        target = torch.as_tensor(target).float().numpy()
        size = target.shape[-1]
        window = labels[y : y + size, x : x + size]
        if not np.array_equal(window, target.reshape(window.shape) > 0.5):
            raise RuntimeError(f"the labels at {(y, x)} are not that patch's target")


def usable_coordinates(dataset):
    """(y, x) of the sample's ink-containing patches, in collect order, with targets."""
    coords, targets = [], []
    for i in validation_indices(len(dataset)):
        target = dataset[int(i)][1]
        if float(torch.as_tensor(target).float().sum()) < 1.0:
            continue
        coords.append(patch_origin(dataset, int(i)))
        targets.append(
            torch.as_tensor(target).float().reshape(1, 1, *target.shape[-2:])
        )
    return coords, targets


def detector_windows(model, volume, layers, origins, size, batch=32):
    """Probability maps (size x size) for windows at origins, /255 as in training.

    ``volume`` is the zarr array, read lazily; ``layers`` its slice range."""
    out = []
    with torch.no_grad():
        for s in range(0, len(origins), batch):
            chunk = origins[s : s + batch]
            x = (
                np.stack(
                    [
                        np.asarray(volume[layers, y : y + size, x0 : x0 + size])
                        for y, x0 in chunk
                    ]
                ).astype(np.float32)
                / 255.0
            )
            logits = model(torch.from_numpy(x)[:, None])
            ups = F.interpolate(
                logits, size=(size, size), mode="bilinear", align_corners=False
            )
            out.extend(torch.sigmoid(ups)[:, 0].numpy())
    return out


def tiled(model, volume, layers, mask, y, x, size, stride):
    """The detector's normal inference (infer.py) restricted to one patch."""
    pred = np.zeros((size, size), np.float32)
    count = np.zeros((size, size), np.float32)
    h, w = mask.shape
    origins = [
        (wy, wx)
        for wy in range(max(0, (y - size + 1) // stride * stride), y + size, stride)
        for wx in range(max(0, (x - size + 1) // stride * stride), x + size, stride)
        if wy % stride == 0
        and wx % stride == 0
        and wy + size <= h
        and wx + size <= w
        and wy + size > y
        and wx + size > x
        and mask[wy : wy + size, wx : wx + size].all()
    ]
    probs = detector_windows(model, volume, layers, origins, size)
    for (wy, wx), prob in zip(origins, probs, strict=True):
        ys, xs = max(wy, y), max(wx, x)
        ye, xe = min(wy + size, y + size), min(wx + size, x + size)
        pred[ys - y : ye - y, xs - x : xe - x] += prob[
            ys - wy : ye - wy, xs - wx : xe - wx
        ]
        count[ys - y : ye - y, xs - x : xe - x] += 1.0
    covered = count > 0
    return np.divide(pred, count, out=np.zeros_like(pred), where=covered), covered


def main(out_path, detector):
    # One thread: on this 4-core host the loop's data pipeline needs the rest.
    torch.set_num_threads(1)
    config = ExperimentConfig.load("config.json")
    dataset, loop_probs, loop_targets, diag, chk = loop_incumbent(config)
    coords, targets = usable_coordinates(dataset)
    if len(coords) != len(loop_targets) or not all(
        torch.equal(a, b) for a, b in zip(targets, loop_targets, strict=True)
    ):
        raise RuntimeError("patch coordinates do not reproduce the loop's targets")
    check_origins(config.val_uri, coords, targets)

    cfg = DetectorConfig()
    model = DetectorModel.load_from_checkpoint(
        detector, cfg=cfg, pred_shape=(1, 1), weights_only=False, map_location="cpu"
    ).eval()
    start = cfg.start_idx - ZARR_SLICE_0_LAYER
    layers = slice(start, start + cfg.in_chans)  # zarr slices 1-26 = layers 17-42
    volume = zarr.open(config.val_uri, "r")
    volume = volume["0"] if isinstance(volume, zarr.Group) else volume
    frag_dir = os.path.dirname(config.val_uri)
    mask = np.asarray(Image.open(os.path.join(frag_dir, "mask.png"))) > 0

    single = detector_windows(model, volume, layers, coords, cfg.size)
    tiled_maps = [
        tiled(model, volume, layers, mask, y, x, cfg.size, cfg.stride)
        for y, x in coords
    ]

    labels = (torch.cat(targets).numpy().ravel() > 0.5).astype(np.uint8)
    prevalence = float(labels.mean())
    floor = 2 * prevalence / (1 + prevalence)
    cards = {
        "loop_incumbent": card(torch.cat(loop_probs).float().numpy().ravel(), labels),
        "detector_single_window": card(np.stack(single).ravel(), labels),
        "detector_tiled": card(np.stack([m for m, _ in tiled_maps]).ravel(), labels),
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
        "detector_layers": [cfg.start_idx, cfg.end_idx],
        "requested_patches": diag["requested_patches"],
        "usable_patches": len(coords),
        "n_pixels": int(labels.size),
        "ink_prevalence": prevalence,
        "all_ink_f1": floor,
        "tiled_uncovered_pixels": int(sum((~c).sum() for _, c in tiled_maps)),
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
