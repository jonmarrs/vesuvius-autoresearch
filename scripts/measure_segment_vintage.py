"""Is the over-firing a property of Scroll 1, or of the 2023-era segmentation?

Three Scroll 1 segments, all rendered from the SAME 2.4um CT volume:
  20231210121321                          2023-era  (the one that over-fires, 3.3-7.4x)
  20230702185753                          2023-era
  20260602230115-20230702185753_v14       2026 RE-SEGMENTATION of the same sheet as above

The third is the control that separates vintage from sheet content: same sheet,
same scan, different segmentation.
"""

import fsspec
import numpy as np
import torch
import zarr
from transformers import AutoModel

B = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/"
    "%s/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr"
)
SEGS = {
    "20231210121321 (2023)": B % "20231210121321",
    "20230702185753 (2023)": B % "20230702185753",
    "..._v14 (2026 reseg)": B % "20260602230115-20230702185753_v14",
}
HOME = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1667/segments/"
    "20260108140509-w011_20260108140509268_flatboi/surface-volumes/"
    "2.399um-0.22m-78keV-volume-20251217075048.zarr"
)


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
for name, url in [("PHerc1667 w011 (home)", HOME)] + list(SEGS.items()):
    a = zarr.open(fsspec.get_mapper(url), mode="r")["0"]
    lo = a.shape[0] // 2 - 31
    H, W = a.shape[1], a.shape[2]
    rates = []
    for fy in (0.3, 0.45, 0.6):
        for fx in (0.35, 0.55):
            y, x = int(H * fy), int(W * fx)
            if y + 1024 > H or x + 1024 > W:
                continue
            blk = np.asarray(a[lo : lo + 62, y : y + 1024, x : x + 1024])
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
    print(
        f"  {name:<26} shape {str(a.shape):>22}  median {np.median(rates):.4f}  "
        f"n={len(rates)}  range {min(rates):.3f}-{max(rates):.3f}",
        flush=True,
    )
