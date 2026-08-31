"""Does the monotone ladder reproduce on a SECOND segment?

CORROBORATION, NOT VALIDATION. There is exactly one Scroll 1 target with human
ground truth that ScrollGT will score against: 20231210121321. The other two are
marked non-scoring for a data reason that applies to any model (local placement
error ~102 level-2 px, about 1.9x the analysis window). So a second segment cannot
be validated against human labels.

Instead this scores the six members against the PUBLISHED CANON PREDICTION on a
different segment, 20231012184424. Agreement with canon is not correctness: canon
is a model. But the CLAIM under test is an ORDERING (does more pseudo-label
density produce output closer to a good model?), and an ordering reproducing
against a different reference on a different segment is meaningful corroboration.
"""

import fsspec
import numpy as np
import torch
import zarr
from PIL import Image
from transformers import AutoModel

Image.MAX_IMAGE_PIXELS = None

SEG = "20231012184424"
URL = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/"
    f"{SEG}/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr"
)
canon = np.array(Image.open(f"canon_{SEG}.jpg").convert("L")).astype(np.float32) / 255.0
a = zarr.open(fsspec.get_mapper(URL), mode="r")["0"]
lo = a.shape[0] // 2 - 31
# a 4096^2 level-0 window well inside the segment -> 1024^2 preds -> 512^2 at ds8
Y0, X0, N = a.shape[1] // 2, a.shape[2] // 2, 4096
print(f"level0 {a.shape}, window y={Y0} x={X0} size={N}", flush=True)
blk = np.asarray(a[lo : lo + 62, Y0 : Y0 + N, X0 : X0 + N])
ref = canon[Y0 // 8 : Y0 // 8 + N // 8, X0 // 8 : X0 // 8 + N // 8].ravel()
print(f"canon window {N // 8}^2, mean {ref.mean():.4f}", flush=True)


def auc(s, y):
    y = y.astype(bool)
    n1 = int(y.sum())
    n0 = y.size - n1
    if n1 < 10 or n0 < 10:
        return float("nan")
    o = np.argsort(s, kind="mergesort")
    r = np.empty(s.size, np.float64)
    r[o] = np.arange(1, s.size + 1)
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


ybin = ref > 0.5
print(f"\ncanon-positive fraction in window: {ybin.mean():.4f}\n")
print(f"{'member':<8}{'AUC vs canon':>14}{'spearman':>11}{'above0.5':>11}")
for i in range(6):
    m = (
        AutoModel.from_pretrained(
            f"/home/jon/openclaw-workspace/Neo-VM/data/ink_ablation/it{i}",
            trust_remote_code=True,
        )
        .eval()
        .cuda()
    )
    out = np.empty((N // 4, N // 4), np.float32)
    with torch.no_grad():
        for ty in range(N // 256):
            for tx in range(N // 256):
                t = (
                    np.clip(
                        blk[
                            :, ty * 256 : (ty + 1) * 256, tx * 256 : (tx + 1) * 256
                        ].astype(np.float32),
                        0,
                        200,
                    )
                    / 255.0
                )
                o = m(torch.from_numpy(t)[None, None].cuda())
                o = o.logits if hasattr(o, "logits") else o
                out[ty * 64 : (ty + 1) * 64, tx * 64 : (tx + 1) * 64] = (
                    torch.sigmoid(torch.as_tensor(o)).float().cpu().numpy()
                )
    p2 = out.reshape(N // 8, 2, N // 8, 2).mean(axis=(1, 3)).ravel()  # -> ds8 frame
    ar = np.argsort(np.argsort(p2)).astype(np.float64)
    br = np.argsort(np.argsort(ref)).astype(np.float64)
    print(
        f"it{i:<7}{auc(p2, ybin):>14.4f}{np.corrcoef(ar, br)[0, 1]:>11.4f}{(p2 > 0.5).mean():>11.4f}",
        flush=True,
    )
    del m
    torch.cuda.empty_cache()
