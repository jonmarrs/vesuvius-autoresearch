"""Run the six released PHerc.1667 ablation checkpoints over one segment region.

PREPROCESSING IS THE WHOLE STORY HERE. The model card documents three mutually
inconsistent conventions and only one of them works:

  * `modeling_inkdetection.py` docstring: "intensity already z-score normalised";
  * the full-segment inference snippet: raw uint8 cast to float;
  * Quick start: "roughly [0, 1] ... clipped raw uint8 layers to [0, 200]".

The first two saturate the model, at 67 to 99% of pixels above 0.5. Only
`clip(x, 0, 200) / 255` matches the published prediction for the same segment,
which fires on 2.82% of pixels. See `reports/ink_ablation_scale_bug.md`.

LEVEL 0, NOT LEVEL 2. The checkpoints operate on 2.4 um data, which is pyramid
level 0 (level 2 is [2.4, 9.6, 9.6], four times coarser laterally). ScrollGT's
target is *defined* at level 2 because that is where its ground truth was
registered; inheriting that level for model input was the original error.
Level-0 input means the 4x-downsampled output lands at exactly the ground
truth's own resolution.

STREAMED, because the region is 16384^2 x 62 at level 0, about 16 GiB. Row-blocks
are fetched, tiled, run, and discarded.

MUST RUN IN THE ISOLATED VENV, transformers pinned to 4.57.6. See
repro/ink_ablation/README.md.
"""

import argparse
import time

import fsspec
import numpy as np
import torch
import zarr

DEPTH, TILE, OUT_TILE = 62, 256, 64
CLIP_HI, SCALE = 200.0, 255.0  # the only convention that reproduces published output


def prep(block):
    """The documented Quick-start convention, and the only one that works."""
    return np.clip(block.astype(np.float32), 0.0, CLIP_HI) / SCALE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--y0", type=int, required=True, help="level-0 row origin")
    ap.add_argument("--x0", type=int, required=True, help="level-0 col origin")
    ap.add_argument("--size", type=int, default=16384, help="level-0 extent")
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    from transformers import AutoModel

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    a = zarr.open(fsspec.get_mapper(args.url), mode="r")["0"]
    d = a.shape[0]
    lo = d // 2 - DEPTH // 2
    n = args.size // TILE
    print(
        f"level0 {a.shape}, depth [{lo},{lo + DEPTH}), {n}x{n} tiles, device {dev}",
        flush=True,
    )

    models = {}
    for i in range(6):
        models[f"it{i}"] = (
            AutoModel.from_pretrained(f"{args.models}/it{i}", trust_remote_code=True)
            .eval()
            .to(dev)
        )
    print("six members loaded", flush=True)

    out = {k: np.zeros((n * OUT_TILE, n * OUT_TILE), np.float32) for k in models}
    t0 = time.time()
    for by in range(n):
        y = args.y0 + by * TILE
        block = np.asarray(
            a[lo : lo + DEPTH, y : y + TILE, args.x0 : args.x0 + args.size]
        )
        tiles = np.stack(
            [prep(block[:, :, bx * TILE : (bx + 1) * TILE]) for bx in range(n)]
        )
        x_all = torch.from_numpy(tiles)[:, None]
        for k, m in models.items():
            preds = np.empty((n, OUT_TILE, OUT_TILE), np.float32)
            with torch.no_grad():
                for s in range(0, n, args.batch):
                    xb = x_all[s : s + args.batch].to(dev)
                    o = m(xb)
                    o = o.logits if hasattr(o, "logits") else o
                    preds[s : s + args.batch] = (
                        torch.sigmoid(torch.as_tensor(o))
                        .squeeze(1)
                        .float()
                        .cpu()
                        .numpy()
                    )
            for bx in range(n):
                out[k][
                    by * OUT_TILE : (by + 1) * OUT_TILE,
                    bx * OUT_TILE : (bx + 1) * OUT_TILE,
                ] = preds[bx]
        if (by + 1) % 8 == 0 or by == n - 1:
            el = time.time() - t0
            print(
                f"  row-block {by + 1}/{n}  elapsed {el / 60:.1f}m  "
                f"eta {el / (by + 1) * (n - by - 1) / 60:.1f}m",
                flush=True,
            )

    for k, v in out.items():
        print(
            f"  {k}: mean {v.mean():.4f}  above0.5 {(v > 0.5).mean():.4f}  max {v.max():.4f}"
        )
    np.savez_compressed(args.out, **out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
