# repro/ink_segformer/eval_held_out.py
"""Infer + evaluate a held-out fragment with a trained checkpoint, render the ink PNG.

Task 8 Step 3 runner. Example:
  PYTHONPATH=. .venv/bin/python repro/ink_segformer/eval_held_out.py \
    --ckpt repro/ink_segformer/runs/model_val1.pt \
    --data-root "$PWD/local_data/kaggle_ink/train" --val 1 --z-start 0 --z-count 33
"""

import argparse
import json
import os
import sys

import torch

_R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _R)

from repro.ink_segformer.config import ReproConfig
from repro.ink_segformer.evaluate import evaluate_fragment, save_ink_png
from repro.ink_segformer.infer import predict_fragment
from repro.ink_segformer.model import InkSegformer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="repro/ink_segformer/runs/model_val1.pt")
    ap.add_argument("--data-root", default=ReproConfig.data_root)
    ap.add_argument("--val", type=int, default=1, help="held-out fragment id")
    ap.add_argument("--z-start", type=int, default=ReproConfig.z_start)
    ap.add_argument("--z-count", type=int, default=ReproConfig.z_count)
    ap.add_argument("--out", default="repro/ink_segformer/runs/ink_frag{val}.png")
    ap.add_argument("--no-tta", action="store_true")
    args = ap.parse_args()

    cfg = ReproConfig()
    cfg.data_root = args.data_root
    cfg.z_start = args.z_start
    cfg.z_count = args.z_count
    dev = torch.device("cuda")

    ck = torch.load(args.ckpt, map_location="cpu")
    m = InkSegformer(cfg.stem_channels, cfg.encoder, encoder_weights=None).to(dev)
    m.load_state_dict(ck["model"])
    m.eval()

    frag = os.path.join(cfg.data_root, str(args.val))
    prob = predict_fragment(m, frag, cfg, dev, tta=not args.no_tta)
    r = evaluate_fragment(prob, frag + "/inklabels.png", frag + "/mask.png")
    print(f"HELD-OUT FRAGMENT {args.val}:", json.dumps(r))
    print(f"  (train-loop val_auc at save = {ck.get('val_auc')})")

    out = args.out.format(val=args.val)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    save_ink_png(prob, out, r["threshold"])
    print(f"rendered {out} (+ thresholded)")


if __name__ == "__main__":
    main()
