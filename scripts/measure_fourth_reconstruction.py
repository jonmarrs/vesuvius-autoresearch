"""Reconstruction sensitivity: PHerc 0500P2 publishes at 2.215um-0.4m-111keV, a
third reconstruction on a non-home scroll. If it over-fires like Scroll 1's
2.4um, the models are reconstruction-sensitive rather than Scroll-1-specific.

Scroll and reconstruction cannot be separated directly: no other scroll ships
Scroll 1's 2.4um-0.22m-78keV, and Scroll 1 ships no 2.399um.
"""

import fsspec
import numpy as np
import torch
import zarr
from transformers import AutoModel

U = {
    "PHerc1667 w011 (home, 2.399um)": (
        "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1667/segments/"
        "20260108140509-w011_20260108140509268_flatboi/surface-volumes/2.399um-0.22m-78keV-volume-20251217075048.zarr"
    ),
    "PHerc0500P2 (2.215um/111keV)": (
        "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0500P2/segments/20250609204953-z_dbg_gen_00612/"
        "surface-volumes/2.215um-0.4m-111keV-volume-20250526151718.zarr"
    ),
}


def prep(t):
    return np.clip(t.astype(np.float32), 0, 200) / 255.0


m = (
    AutoModel.from_pretrained(
        "/home/jon/openclaw-workspace/Neo-VM/data/ink_ablation/it5",
        trust_remote_code=True,
    )
    .eval()
    .cuda()
)
for name, url in U.items():
    try:
        a = zarr.open(fsspec.get_mapper(url), mode="r")["0"]
    except Exception as e:
        print(f"  {name}: unavailable ({type(e).__name__})")
        continue
    lo = max(0, a.shape[0] // 2 - 31)
    H, W = a.shape[1], a.shape[2]
    rates = []
    for fy in (0.3, 0.45, 0.6):
        for fx in (0.35, 0.55):
            y, x = int(H * fy), int(W * fx)
            if y + 1024 > H or x + 1024 > W:
                continue
            blk = np.asarray(a[lo : lo + 62, y : y + 1024, x : x + 1024])
            if blk.shape[0] < 62:
                blk = np.pad(blk, ((0, 62 - blk.shape[0]), (0, 0), (0, 0)), mode="edge")
            ps = []
            with torch.no_grad():
                for yy in range(0, 1024, 256):
                    for xx in range(0, 1024, 256):
                        o = m(
                            torch.from_numpy(
                                prep(blk[:, yy : yy + 256, xx : xx + 256])
                            )[None, None].cuda()
                        )
                        o = o.logits if hasattr(o, "logits") else o
                        ps.append(
                            torch.sigmoid(torch.as_tensor(o))
                            .float()
                            .cpu()
                            .numpy()
                            .ravel()
                        )
            rates.append(float((np.concatenate(ps) > 0.5).mean()))
    if rates:
        print(
            f"  {name:<34} shape {str(a.shape):>22} median {np.median(rates):.4f} n={len(rates)}",
            flush=True,
        )
