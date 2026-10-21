"""Diagnose whether post-processing (threshold + small-component removal) can
move the real model's skel_dist toward the prize gate (<= 2.0), separately from
training changes.

Loads best_model.pt with its own recorded recipe and complete weights
(``load_tool_checkpoint``), scores the loop's validation protocol on
config.json's validation inputs as ``reevaluate_best_model.py`` does, then
sweeps binarization threshold x despeckle min-component-size over the
ink-containing patches and reports the villa topology metrics for each
combination.

The baseline row is the loop's own measurement: the centerline_dice-optimal
threshold (``select_topology_threshold``), no post-processing, skel_dist and
centerline_dice on every 10th patch and cc_diff on all of them. The Dice-optimal
threshold, which the loop scored topology at until 2026-06-10, is swept too.

Predictions are cached (``--cache``) under a key of the checkpoint's sha256,
the protocol and the validation inputs' fingerprint, so a promoted model or
other validation data is scored afresh rather than read from an older run.

Usage:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/diagnose_topology_postproc.py
"""

import argparse
import hashlib
import os
import sys
import tempfile

import numpy as np
import torch
from scipy import ndimage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts", "training"))

from train import (
    ExperimentConfig,
    build_validation_dataset,
    collect_validation_predictions,
    compute_cc_diff,
    compute_centerline_dice,
    compute_official_dice,
    compute_skeleton_dist,
    ink_containing,
    select_topology_threshold,
)

from scripts.reevaluate_best_model import RECORDED_INPUT_SETTINGS
from scripts.training.promotion import (
    save_checkpoint_atomic,
    validation_inputs_fingerprint,
    validation_protocol,
)
from vesuvius_autoresearch.core.checkpoint_tools import (
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)

DEFAULT_CACHE = os.path.join(tempfile.gettempdir(), "topo_postproc_preds.pt")
MIN_SIZES = (1, 16, 64)
FIXED_THRESHOLDS = (0.5, 0.65)
SKEL_DIST_GATE = 2.0


def despeckle(mask: np.ndarray, min_size: int) -> np.ndarray:
    if min_size <= 1:
        return mask
    lbl, k = ndimage.label(mask)
    if k == 0:
        return mask
    sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, k + 1))
    keep = 1 + np.where(sizes >= min_size)[0]
    return np.isin(lbl, keep)


def topo_metrics(probs, targets, threshold, min_size, subset_step=10):
    """The loop's per-patch topology metrics over ink-containing patches, after
    thresholding at ``threshold`` and removing components under ``min_size``
    pixels: cc_diff on every patch, skel_dist and centerline_dice on every
    ``subset_step``-th, as train.py and reevaluate_best_model.py measure them.

    A measurement that is not finite (despeckling can empty a prediction) is
    counted in ``n_undefined`` and left out of the means, not raised."""
    skel, cd, cc, dice = [], [], [], []
    undefined = 0
    for i in range(len(probs)):
        gt = (targets[i] > 0.5).numpy().astype(bool)
        pred = (probs[i] > threshold).numpy().astype(bool)
        pred = np.stack(
            [despeckle(pred[b, 0], min_size)[None] for b in range(pred.shape[0])]
        )
        dice.append(
            compute_official_dice(
                targets[i], torch.from_numpy(pred.astype(np.float32)), threshold=0.5
            )
        )
        for b in range(gt.shape[0]):
            cc.append(compute_cc_diff(gt[b, 0], pred[b, 0]))
        if i % subset_step == 0:
            gt3, pred3 = np.squeeze(gt), np.squeeze(pred)
            if gt3.ndim == 2:
                gt3 = gt3[None]
            if pred3.ndim == 2:
                pred3 = pred3[None]
            sd = compute_skeleton_dist(gt3, pred3)
            c = compute_centerline_dice(gt3, pred3, tolerance_radius=3.0)[
                "centerline_dice"
            ]
            for value, kept in ((sd, skel), (c, cd)):
                if np.isfinite(value):
                    kept.append(float(value))
                else:
                    undefined += 1
    return {
        "dice": float(np.mean(dice)) if dice else float("nan"),
        "skel_dist": float(np.mean(skel)) if skel else float("nan"),
        "centerline_dice": float(np.mean(cd)) if cd else float("nan"),
        "cc_diff": float(np.mean(cc)) if cc else float("nan"),
        "n_skel": len(skel),
        "n_undefined": undefined,
    }


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cached(path, key):
    """The cached predictions when they were made under ``key``, else None."""
    if not os.path.exists(path):
        return None
    try:
        blob = torch.load(path, map_location="cpu", weights_only=True)
    except Exception as exc:
        print(f"ignoring unreadable prediction cache {path}: {exc}")
        return None
    if not isinstance(blob, dict) or blob.get("key") != key:
        print(
            f"ignoring {path}: its predictions are of another checkpoint or "
            "validation sample"
        )
        return None
    return blob["probs"], blob["targets"]


def predictions(model, settings, config, device, cache, key, protocol):
    """The protocol sample's per-patch probabilities and targets: from ``cache``
    when it holds this key's, else scored and cached."""
    hit = _cached(cache, key)
    if hit is not None:
        print(f"loaded cached predictions: {len(hit[0])} patches")
        return hit
    val_ds = build_validation_dataset(config)

    def probabilities(net, x):
        return ink_probabilities(net, validate_batch(x, settings))

    torch.manual_seed(42)
    probs, targets, diag = collect_validation_predictions(
        model,
        val_ds,
        config.num_layers,
        device,
        batch_size=config.batch_size,
        amp_enabled=device.type == "cuda",
        probabilities=probabilities,
        protocol=protocol,
    )
    if not diag["complete"]:
        raise SystemExit(
            f"{diag['batch_errors']} validation batches failed; the protocol's "
            "sample is incomplete, so nothing was measured or cached"
        )
    save_checkpoint_atomic({"key": key, "probs": probs, "targets": targets}, cache)
    return probs, targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--checkpoint", default="best_model.pt")
    parser.add_argument("--cache", default=DEFAULT_CACHE)
    parser.add_argument(
        "--unwarped",
        action="store_true",
        help="score a checkpoint that records use_lasagna: true unwarped, as "
        "reevaluate_best_model.py --unwarped does",
    )
    args = parser.parse_args(argv)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device: {device}")
    # The validation inputs are the loop's current ones; the model and what it
    # sees are the checkpoint's own.
    config = (
        ExperimentConfig.load("config.json")
        if os.path.exists("config.json")
        else ExperimentConfig()
    )
    checkpoint_sha256 = _file_sha256(args.checkpoint)
    model, settings, chk = load_tool_checkpoint(args.checkpoint, device)
    for name, value in settings.items():
        setattr(config, name, value)
    stored = chk.get("config", {})
    for name in RECORDED_INPUT_SETTINGS:
        if name in stored:
            setattr(config, name, stored[name])
    if args.unwarped and config.use_lasagna:
        config.use_lasagna = False
        print("  recorded use_lasagna: true; scoring unwarped (--unwarped)")
    print(
        f"stored arch={settings['architecture']} val_f1={chk.get('val_f1')} "
        f"avg_skel_dist={chk.get('avg_skel_dist')}"
    )

    protocol = validation_protocol(config.depth_band)
    key = {
        "checkpoint_sha256": checkpoint_sha256,
        "protocol": protocol,
        "inputs_sha256": validation_inputs_fingerprint(
            config.val_uri, config.depth_band
        ),
        "use_lasagna": bool(config.use_lasagna),
    }
    probs, targets = predictions(
        model, settings, config, device, args.cache, key, protocol
    )
    ink_probs, ink_targets = ink_containing(probs, targets)
    print(f"scored patches: {len(probs)}, ink-containing: {len(ink_probs)}")
    if not ink_probs:
        raise SystemExit("no ink-containing validation patches to measure")

    probs_cat = torch.cat(ink_probs)
    targets_cat = torch.cat(ink_targets)
    best_dice, dice_thr = 0.0, 0.5
    for t in np.linspace(0.01, 0.8, 40):
        d = compute_official_dice(targets_cat, probs_cat, threshold=t)
        if d > best_dice:
            best_dice, dice_thr = d, float(t)
    topo_thr, topo_cd = select_topology_threshold(ink_probs, ink_targets)
    print(f"Dice-optimal threshold = {dice_thr:.3f} (dice={best_dice:.4f})")
    print(f"topology threshold     = {topo_thr:.3f} (centerline_dice={topo_cd:.4f})\n")

    thresholds = []
    for t in (topo_thr, dice_thr, *FIXED_THRESHOLDS):
        if all(abs(t - u) > 1e-9 for u in thresholds):
            thresholds.append(t)
    print(
        f"{'thresh':>7} {'minsz':>6} {'dice':>7} {'skel_dist':>10} {'cl_dice':>8} "
        f"{'cc_diff':>8} {'undef':>6}"
    )
    print("-" * 59)
    baseline = None
    for thr in thresholds:
        for ms in MIN_SIZES:
            m = topo_metrics(ink_probs, ink_targets, thr, ms)
            is_baseline = thr == topo_thr and ms == 1
            if is_baseline:
                baseline = m
            tag = "  <- the loop's measurement" if is_baseline else ""
            print(
                f"{thr:7.3f} {ms:6d} {m['dice']:7.4f} {m['skel_dist']:10.3f} "
                f"{m['centerline_dice']:8.4f} {m['cc_diff']:8.3f} "
                f"{m['n_undefined']:6d}{tag}"
            )
    print(
        f"\nBaseline (topology threshold {topo_thr:.3f}, no post-processing): "
        f"skel_dist={baseline['skel_dist']:.3f}, gate={SKEL_DIST_GATE}; "
        f"stored avg_skel_dist={chk.get('avg_skel_dist')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
