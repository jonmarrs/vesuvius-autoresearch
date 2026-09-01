"""Generate confidence-filtered pseudo-labels for a fragment region using a
trained checkpoint. Output is a 3-value PNG (0=bg, 255=ink, 128=uncertain/ignore)
consumed as inklabels.png by a region fragment dir; the 128 band is down-weighted
to zero in train.py's confidence-weighted ink loss.
"""

import argparse
import os
import sys

import numpy as np
import torch
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))


def prob_to_pseudo_png(prob, region, tau_high=0.65, tau_low=0.15):
    """Map a [H,W] probability map + boolean region mask to a uint8 pseudo-label:
    255 (ink) where prob>tau_high, 0 (bg) where prob<tau_low, else 128 (ignore).
    Pixels outside `region` are always 128 (ignore)."""
    out = np.full(prob.shape, 128, dtype=np.uint8)
    out[(prob > tau_high) & region] = 255
    out[(prob < tau_low) & region] = 0
    return out


def _infer_region(checkpoint, frag_dir, region_mask_path, device, tau_high, tau_low):
    from train import ExperimentConfig, load_shape_compatible_state

    from scripts.measure_ink_auc import _volume_uri
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    chk = torch.load(checkpoint, map_location="cpu", weights_only=False)
    s = chk.get("config", {})
    ps, nl = s.get("patch_size", 64), s.get("num_layers", 16)
    config = ExperimentConfig.load("config.json")
    model = build_inference_model(
        architecture=s.get("architecture", "resenc_unet"),
        patch_size=ps,
        num_layers=nl,
        base_feat=s.get("base_feat", 64),
        num_blocks=s.get("num_blocks", 16),
        num_heads=s.get("num_heads", 8),
        dropout=s.get("dropout", 0.0),
        use_ridges=s.get("use_ridges", config.use_ridges),
        multi_task_heads=s.get("multi_task_heads", False),
    ).to(device)
    load_shape_compatible_state(model, chk["model_state_dict"], checkpoint)
    model.eval()

    ds = VesuviusLabeledDataset(
        _volume_uri(frag_dir),
        os.path.join(frag_dir, "inklabels.png"),
        region_mask_path,
        ps,
        nl + 8,
        seed=7,
        cache_dir=config.cache_dir,
        use_ridges=s.get("use_ridges", config.use_ridges),
        ridge_sigma=getattr(config, "ridge_sigma", 2.0),
        use_lasagna=False,
        require_ink=False,
        jitter=False,
    )
    H, W = ds.shape[1], ds.shape[2]
    prob_sum = np.zeros((H, W), dtype=np.float32)
    prob_cnt = np.zeros((H, W), dtype=np.float32)
    with torch.no_grad():
        for i in range(len(ds)):
            x_raw, _, _ = ds[i]
            y0, x0 = ds.valid_coords[i]
            x = x_raw[:, 4 : 4 + nl].unsqueeze(0).to(device)
            out = model(x)
            out = out[0] if isinstance(out, tuple) else out
            p = torch.sigmoid(out).squeeze().float().cpu().numpy()
            prob_sum[y0 : y0 + ps, x0 : x0 + ps] += p
            prob_cnt[y0 : y0 + ps, x0 : x0 + ps] += 1.0
    prob = np.divide(
        prob_sum, prob_cnt, out=np.zeros_like(prob_sum), where=prob_cnt > 0
    )
    region = (np.array(Image.open(region_mask_path).convert("L")) > 127) & (
        prob_cnt > 0
    )
    return prob_to_pseudo_png(prob, region, tau_high, tau_low)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--fragment", required=True, help="fragment dir (volume + labels)")
    ap.add_argument("--region-mask", required=True)
    ap.add_argument("--out", required=True, help="output pseudo-label PNG")
    ap.add_argument("--tau-high", type=float, default=0.65)
    ap.add_argument("--tau-low", type=float, default=0.15)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    out = _infer_region(
        args.checkpoint,
        args.fragment,
        args.region_mask,
        torch.device(args.device),
        args.tau_high,
        args.tau_low,
    )
    frac_ink = float((out == 255).mean())
    frac_ign = float((out == 128).mean())
    if frac_ink < 1e-4 or frac_ink > 0.99:
        raise SystemExit(
            f"Degenerate pseudo-labels (ink frac={frac_ink:.4f}); aborting. "
            f"Adjust tau or check the checkpoint."
        )
    Image.fromarray(out).save(args.out)
    print(f"wrote {args.out}: ink={frac_ink:.3f} ignore={frac_ign:.3f}")


if __name__ == "__main__":
    main()
