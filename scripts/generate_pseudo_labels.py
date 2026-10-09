"""Generate confidence-filtered pseudo-labels for a fragment region using a
trained checkpoint. Output is a 3-value PNG (0=bg, 255=ink, 128=uncertain/ignore)
consumed by training with confidence weighting. PNG 128 normalizes to 128/255,
giving residual weight 1/255, not exactly zero, in the existing loss.
"""

import argparse
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import torch
from PIL import Image

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))

from scripts.candidate_artifacts import separate_paths
from scripts.export_for_production import checkpoint_contract
from scripts.labeling.label_artifacts import new_output, publish_new_file
from scripts.pseudo_label_artifacts import (
    MAX_LABEL_PIXELS,
    fragment_inputs,
    pseudo_array,
    read_png,
)
from vesuvius_autoresearch.core.checkpoint_tools import (
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)


def prob_to_pseudo_png(prob, region, tau_high=0.65, tau_low=0.15):
    """Map a [H,W] probability map + boolean region mask to a uint8 pseudo-label:
    255 (ink) where prob>tau_high, 0 (bg) where prob<tau_low, else 128 (ignore).
    Pixels outside `region` are always 128 (ignore)."""
    if not np.isfinite([tau_low, tau_high]).all() or not 0 <= tau_low < tau_high <= 1:
        raise ValueError("thresholds must satisfy 0 <= tau_low < tau_high <= 1")
    prob, region = np.asarray(prob), np.asarray(region)
    if (
        prob.ndim != 2
        or prob.shape != region.shape
        or region.dtype != np.bool_
        or not np.isfinite(prob).all()
        or np.any((prob < 0) | (prob > 1))
    ):
        raise ValueError(
            "probability and boolean region maps must align and be finite in [0,1]"
        )
    out = np.full(prob.shape, 128, dtype=np.uint8)
    out[(prob > tau_high) & region] = 255
    out[(prob < tau_low) & region] = 0
    return out


def _infer_region(
    checkpoint,
    frag_dir,
    region_mask_path,
    device,
    tau_high,
    tau_low,
    cache_dir=None,
    max_pixels=MAX_LABEL_PIXELS,
):
    from scripts.measure_ink_auc import _volume_uri
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    # Validate thresholds before loading data, even if no patches are found.
    prob_to_pseudo_png(np.zeros((1, 1)), np.ones((1, 1), bool), tau_high, tau_low)
    model, s, saved = load_tool_checkpoint(checkpoint, device)
    checkpoint_contract(saved, verify_model=False)
    ps, nl = s["patch_size"], s["num_layers"]

    ds = VesuviusLabeledDataset(
        _volume_uri(frag_dir),
        None,  # Region-only sampling needs no ambient ground-truth labels.
        region_mask_path,
        ps,
        nl + 8,
        seed=7,
        cache_dir=cache_dir,
        use_ridges=s["use_ridges"],
        ridge_sigma=s["ridge_sigma"],
        use_lasagna=False,
        require_ink=False,
        jitter=False,
        strict_reads=True,
    )
    H, W = ds.shape[1], ds.shape[2]
    requested_region = read_png(
        region_mask_path, kind="binary", shape=(H, W), max_pixels=max_pixels
    )
    if requested_region.shape != (H, W) or not requested_region.any():
        raise ValueError(
            "region mask must match the volume and contain requested pixels"
        )
    prob_sum = np.zeros((H, W), dtype=np.float32)
    prob_cnt = np.zeros((H, W), dtype=np.float32)
    with torch.no_grad():
        for i in range(len(ds)):
            x_raw, _, _ = ds[i]
            y0, x0 = ds.valid_coords[i]
            if not (0 <= y0 <= H - ps and 0 <= x0 <= W - ps):
                raise ValueError("patch coordinates exceed the volume")
            x = validate_batch(x_raw.unsqueeze(0), s, buffered=True).to(device)
            p = ink_probabilities(model, x)[0, 0].cpu().numpy()
            prob_sum[y0 : y0 + ps, x0 : x0 + ps] += p
            prob_cnt[y0 : y0 + ps, x0 : x0 + ps] += 1.0
    prob = np.divide(
        prob_sum, prob_cnt, out=np.zeros_like(prob_sum), where=prob_cnt > 0
    )
    region = requested_region & (prob_cnt > 0)
    if not region.any():
        raise ValueError("no requested pixels received a prediction")
    return prob_to_pseudo_png(prob, region, tau_high, tau_low)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--fragment", required=True, help="fragment dir (volume + labels)")
    ap.add_argument("--region-mask", required=True)
    ap.add_argument("--out", required=True, help="output pseudo-label PNG")
    ap.add_argument("--tau-high", type=float, default=0.65)
    ap.add_argument("--tau-low", type=float, default=0.15)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--cache-dir")
    ap.add_argument("--max-pixels", type=int, default=MAX_LABEL_PIXELS)
    args = ap.parse_args(argv)

    destination = new_output(args.out, args.checkpoint, args.fragment, args.region_mask)
    if destination.suffix.lower() != ".png":
        raise ValueError("output must be a new .png file")
    prob_to_pseudo_png(
        np.zeros((1, 1)), np.ones((1, 1), bool), args.tau_high, args.tau_low
    )
    model, settings, saved = load_tool_checkpoint(args.checkpoint, "cpu")
    checkpoint_contract(saved, verify_model=False)
    del model, saved
    uri, _, _ = fragment_inputs(
        args.fragment, args.region_mask, settings, args.max_pixels
    )
    new_output(destination, uri)
    if args.cache_dir:
        cache = Path(args.cache_dir).resolve()
        for source in (
            args.fragment,
            uri,
            args.checkpoint,
            args.region_mask,
            destination,
        ):
            separate_paths(source, cache)
        cache.mkdir(parents=True, exist_ok=True)

    with (
        nullcontext(str(cache))
        if args.cache_dir
        else TemporaryDirectory(prefix="vesuvius-pseudo-") as cache_dir
    ):
        out = _infer_region(
            args.checkpoint,
            args.fragment,
            args.region_mask,
            torch.device(args.device),
            args.tau_high,
            args.tau_low,
            cache_dir=cache_dir,
            max_pixels=args.max_pixels,
        )
    pseudo_array(out)
    frac_ink = float((out == 255).mean())
    frac_ign = float((out == 128).mean())
    if frac_ink < 1e-4 or frac_ink > 0.99:
        raise SystemExit(
            f"Degenerate pseudo-labels (ink frac={frac_ink:.4f}); aborting. "
            f"Adjust tau or check the checkpoint."
        )
    with publish_new_file(
        destination, args.checkpoint, args.fragment, args.region_mask
    ) as staging:
        Image.fromarray(out).save(staging)
    print(f"wrote {args.out}: ink={frac_ink:.3f} ignore={frac_ign:.3f}")


if __name__ == "__main__":
    main()
