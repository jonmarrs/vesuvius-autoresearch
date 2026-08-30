"""Run the six released PHerc.1667 ablation checkpoints over one segment region.

Inference only, and deliberately separate from scoring: this step is expensive and
its output is a fixed artifact, while the scoring in
`scripts/score_ink_ablation.py` is cheap and will be re-run under three alignments.
Keeping them apart means an alignment question cannot quietly become a reason to
re-run inference with different settings.

MUST RUN IN THE ISOLATED VENV (see repro/ink_ablation/README.md):
  transformers must be 4.57.6, the version in the checkpoints' config.json. On 5.x
  the weights load and then from_pretrained dies in _finalize_model_loading, and
  installing transformers into this repository's venv conflicts with its pinned
  safetensors 0.7.0.

INPUT CONTRACT, from the model cards: (B, 1, 62, 256, 256), z-score normalised per
tile, returning (B, 1, 64, 64) logits. The prediction is therefore 4x downsampled
from the input tile, so a 4096 region yields a 1024 map.

Run:
    <ink_ablation>/.venv/bin/python scripts/run_ink_ablation.py \
        --region <region_full.npy> --models <dir> --out <preds.npz>
"""

import argparse
import os
import time

import numpy as np
import torch

DEPTH = 62
TILE = 256
OUT_TILE = 64


def load_member(path):
    from transformers import AutoModel

    m = AutoModel.from_pretrained(path, trust_remote_code=True).eval()
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--models", required=True, help="dir holding it0..it5")
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--members", default="0,1,2,3,4,5")
    args = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    vol = np.load(args.region, mmap_mode="r")
    d = vol.shape[0]
    lo = d // 2 - DEPTH // 2
    size = vol.shape[1]
    ntile = size // TILE
    print(
        f"region {vol.shape}, depth window [{lo},{lo + DEPTH}), {ntile}x{ntile} tiles, device {dev}",
        flush=True,
    )

    # Tiles are prepared once and reused across members, so every member sees
    # byte-identical input. Anything else would confound the comparison.
    tiles = np.empty((ntile * ntile, DEPTH, TILE, TILE), np.float32)
    k = 0
    for ty in range(ntile):
        for tx in range(ntile):
            t = np.asarray(
                vol[
                    lo : lo + DEPTH,
                    ty * TILE : (ty + 1) * TILE,
                    tx * TILE : (tx + 1) * TILE,
                ],
                dtype=np.float32,
            )
            tiles[k] = (t - t.mean()) / max(t.std(), 1e-6)
            k += 1
    print(f"prepared {k} tiles ({tiles.nbytes / 2**30:.2f} GiB)", flush=True)

    out = {}
    for mi in [int(x) for x in args.members.split(",")]:
        path = os.path.join(args.models, f"it{mi}")
        model = load_member(path).to(dev)
        preds = np.empty((ntile * ntile, OUT_TILE, OUT_TILE), np.float32)
        t0 = time.time()
        with torch.no_grad():
            for s in range(0, tiles.shape[0], args.batch):
                x = torch.from_numpy(tiles[s : s + args.batch])[:, None].to(dev)
                y = model(x)
                y = (
                    y.logits
                    if hasattr(y, "logits")
                    else (y[0] if isinstance(y, (tuple, list)) else y)
                )
                preds[s : s + args.batch] = (
                    torch.sigmoid(torch.as_tensor(y)).squeeze(1).float().cpu().numpy()
                )
        # reassemble tiles into one map
        m = np.empty((ntile * OUT_TILE, ntile * OUT_TILE), np.float32)
        k = 0
        for ty in range(ntile):
            for tx in range(ntile):
                m[
                    ty * OUT_TILE : (ty + 1) * OUT_TILE,
                    tx * OUT_TILE : (tx + 1) * OUT_TILE,
                ] = preds[k]
                k += 1
        out[f"it{mi}"] = m
        print(
            f"  it{mi}: {time.time() - t0:.0f}s  mean {m.mean():.4f}  "
            f"above0.5 {(m > 0.5).mean():.4f}  max {m.max():.4f}",
            flush=True,
        )
        del model
        torch.cuda.empty_cache()

    np.savez_compressed(args.out, **out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
