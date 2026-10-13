"""Which slices of the loop's fragments the model is shown, and where their ink contrast lies.

Read-only. For each labelled fragment named in config.json it records:

* the zarr's depth, and which original surface-volume layer each zarr slice is (by
  matching a 512 px crop against the layer TIFFs the zarr was built from, and against
  the detector's `layers/` stack, which the detector indexes 17-42);
* per slice, the ROC AUC of intensity (5x5 px box mean) for ink against non-ink
  pixels inside the mask: a crude, model-free trace of where ink contrast lies;
* for protocol v2 (no band), the share of the possible validation and training window
  positions that contain a given slice, from the loader's draw (read = num_layers +
  2 * DEPTH_MARGIN slices starting at z0 in 0..depth - read; validation's window is
  the read's middle num_layers; training's starts at an offset 0..2 * DEPTH_MARGIN - 1).

Usage:
    uv run python scripts/ink_depth_profile.py --out reports/ink_depth_profile.json
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np
import zarr
from PIL import Image
from scipy.ndimage import uniform_filter
from scipy.stats import rankdata

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

from scripts.training.config import ExperimentConfig  # noqa: E402
from vesuvius_autoresearch.core.inference_constants import DEPTH_MARGIN  # noqa: E402
from vesuvius_autoresearch.detector.config import DetectorConfig  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SAMPLES = 100_000
STRIP = 512
CROP = 512


def auc(pos, neg):
    ranks = rankdata(np.concatenate([pos, neg]))
    return (ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (
        len(pos) * len(neg)
    )


def fragment_dir(uri):
    return os.path.dirname(os.path.join(_REPO, uri))


def level0(uri):
    z = zarr.open(os.path.join(_REPO, uri), "r")
    return z["0"] if isinstance(z, zarr.Group) else z


def layer_mapping(z, frag_dir, frag):
    """Best-matching zarr slice for a few layer TIFFs, by mean absolute difference."""
    _, h, w = z.shape
    ys, xs = slice(h // 2, h // 2 + CROP), slice(w // 2, w // 2 + CROP)
    stack = np.asarray(z[:, ys, xs]).astype(np.int16)
    sources = [
        (os.path.join(frag_dir, "surface_volume"), (16, 17, 32, 48)),
        (os.path.join(_REPO, DetectorConfig.data_root, frag, "layers"), (17, 30, 42)),
    ]
    rows = []
    for folder, layers in sources:
        for layer in layers:
            path = os.path.join(folder, f"{layer}.tif")
            if not os.path.exists(path):
                continue
            img = np.asarray(Image.open(path))[ys, xs]
            if img.dtype == np.uint16:
                img = img >> 8
            err = np.abs(stack - img.astype(np.int16)).mean(axis=(1, 2))
            order = np.argsort(err)
            rows.append(
                {
                    "tif": os.path.relpath(path, _REPO),
                    "layer": layer,
                    "best_zarr_slice": int(order[0]),
                    "mean_abs_diff": round(float(err[order[0]]), 3),
                    "next_best_diff": round(float(err[order[1]]), 3),
                }
            )
    return rows


def contrast_by_slice(z, frag_dir, rng):
    depth, h, w = z.shape
    label = np.asarray(Image.open(os.path.join(frag_dir, "inklabels.png"))) > 0
    mask = np.asarray(Image.open(os.path.join(frag_dir, "mask.png"))) > 0
    if label.shape != (h, w) or mask.shape != (h, w):
        raise ValueError(f"label {label.shape} / mask {mask.shape} vs volume {z.shape}")
    ink = np.flatnonzero(label & mask)
    background = np.flatnonzero(~label & mask)
    values = {}
    for name, pool in (("ink", ink), ("background", background)):
        idx = np.sort(rng.choice(pool, min(SAMPLES, len(pool)), replace=False))
        ys, xs = np.divmod(idx, w)
        out = np.empty((depth, len(idx)), np.float32)
        for y0 in range(0, h, STRIP):
            sel = (ys >= y0) & (ys < y0 + STRIP)
            if not sel.any():
                continue
            lo, hi = max(0, y0 - 2), min(h, y0 + STRIP + 2)
            block = uniform_filter(
                np.asarray(z[:, lo:hi, :]).astype(np.float32),
                size=(1, 5, 5),
                mode="nearest",
            )
            out[:, sel] = block[:, ys[sel] - lo, xs[sel]]
        values[name] = out
    per_slice = [
        {
            "zarr_slice": k,
            "auc": round(float(auc(values["ink"][k], values["background"][k])), 4),
            "mean_ink": round(float(values["ink"][k].mean()), 2),
            "mean_background": round(float(values["background"][k].mean()), 2),
        }
        for k in range(depth)
    ]
    return {
        "ink_prevalence_in_mask": round(len(ink) / int(mask.sum()), 4),
        "sampled_pixels": [len(values["ink"][0]), len(values["background"][0])],
        "per_slice": per_slice,
    }


def window_coverage(depth, num_layers, slices, band):
    """Shares of protocol v2's possible window positions containing each slice,
    and how much of each window lies inside ``band`` ([start, end) zarr slices)."""
    read = num_layers + 2 * DEPTH_MARGIN
    starts = range(0, depth - read + 1)
    val = [(z0 + DEPTH_MARGIN, z0 + DEPTH_MARGIN + num_layers) for z0 in starts]
    train = [
        (z0 + o, z0 + o + num_layers) for z0 in starts for o in range(2 * DEPTH_MARGIN)
    ]

    def share(windows, k):
        return [sum(lo <= k < hi for lo, hi in windows), len(windows)]

    def inside(windows):
        overlap = [min(hi, band[1]) - max(lo, band[0]) for lo, hi in windows]
        return {
            "entirely_inside": [sum(o == num_layers for o in overlap), len(windows)],
            "min_slices_inside": min(overlap),
        }

    return {
        "read_slices": read,
        "z0_values": [starts.start, starts.stop - 1],
        "validation_windows": [list(val[0]), list(val[-1])],
        "validation_contains": {str(k): share(val, k) for k in slices},
        "training_contains": {str(k): share(train, k) for k in slices},
        "validation_in_detector_band": inside(val),
        "training_in_detector_band": inside(train),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    args = p.parse_args()
    config = ExperimentConfig.load(os.path.join(_REPO, "config.json"))
    det = DetectorConfig()
    rng = np.random.default_rng(0)
    result = {
        "git_commit": subprocess.check_output(
            ["git", "-C", _REPO, "rev-parse", "HEAD"], text=True
        ).strip(),
        "config_depth_band": config.depth_band,
        "num_layers": config.num_layers,
        "depth_margin": DEPTH_MARGIN,
        "detector_layers": [det.start_idx, det.end_idx],
        "fragments": {},
    }
    for uri in [*config.uris, config.val_uri]:
        frag_dir = fragment_dir(uri)
        frag = os.path.basename(frag_dir)
        z = level0(uri)
        print(f"{frag}: {z.shape}", flush=True)
        entry = {"uri": uri, "shape": list(z.shape)}
        entry["layer_mapping"] = layer_mapping(z, frag_dir, frag)
        entry |= contrast_by_slice(z, frag_dir, rng)
        auc_dev = [abs(s["auc"] - 0.5) for s in entry["per_slice"]]
        entry["strongest_contrast_slice"] = int(np.argmax(auc_dev))
        entry["brightest_slice"] = int(
            np.argmax(
                [s["mean_ink"] + s["mean_background"] for s in entry["per_slice"]]
            )
        )
        offsets = {m["layer"] - m["best_zarr_slice"] for m in entry["layer_mapping"]}
        if len(offsets) != 1:
            raise ValueError(
                f"{frag}: layer TIFFs disagree on the zarr offset {offsets}"
            )
        offset = offsets.pop()
        entry["zarr_slice_0_is_layer"] = offset
        band = [det.start_idx - offset, det.end_idx - offset]
        entry["detector_band_in_zarr_slices"] = band
        entry["coverage"] = window_coverage(
            z.shape[0],
            config.num_layers,
            sorted({16, entry["strongest_contrast_slice"], entry["brightest_slice"]}),
            band,
        )
        result["fragments"][frag] = entry
    with open(args.out, "w") as f:
        json.dump(result, f, indent=1)
        f.write("\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
