"""Control: does the ladder ordering survive a correspondence-destroying null?

The threat to the corroboration is that more-trained members may simply emit
smoother, more ink-textured output that agrees better with ANY structured
ink-like reference. If so the ordering is about generic texture, not about
reading THIS segment. So score the same six prediction maps against references
that keep canon's texture statistics but destroy its correspondence to the
pixels underneath:

  canon_rot180 / canon_flipLR / canon_transpose  -- same map, wrong alignment
  canon_other                                    -- canon on a DIFFERENT segment

The ladder must appear against `canon_true` and vanish against all four nulls.
"""

import json
import os

import fsspec
import numpy as np
import torch
import zarr
from PIL import Image
from transformers import AutoModel

Image.MAX_IMAGE_PIXELS = None

SEG, OTHER = "20231012184424", "20230702185753"
URL = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/"
    f"{SEG}/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr"
)
N = 4096
a = zarr.open(fsspec.get_mapper(URL), mode="r")["0"]
lo, Y0, X0 = a.shape[0] // 2 - 31, a.shape[1] // 2, a.shape[2] // 2

if not os.path.exists("preds_segB.npz"):
    blk = np.asarray(a[lo : lo + 62, Y0 : Y0 + N, X0 : X0 + N])
    preds = {}
    for i in range(6):
        m = (
            AutoModel.from_pretrained(f"{os.getcwd()}/it{i}", trust_remote_code=True)
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
        preds[f"it{i}"] = out.reshape(N // 8, 2, N // 8, 2).mean(
            axis=(1, 3)
        )  # -> ds8 frame
        print(f"predicted it{i}", flush=True)
        del m
        torch.cuda.empty_cache()
    np.savez_compressed("preds_segB.npz", **preds)
P = dict(np.load("preds_segB.npz"))
print(f"loaded 6 prediction maps, {next(iter(P.values())).shape}\n", flush=True)

M = N // 8
c = np.array(Image.open(f"canon_{SEG}.jpg").convert("L")).astype(np.float32) / 255.0
w = c[Y0 // 8 : Y0 // 8 + M, X0 // 8 : X0 // 8 + M]
co = np.array(Image.open(f"canon_{OTHER}.jpg").convert("L")).astype(np.float32) / 255.0
oy, ox = co.shape[0] // 2, co.shape[1] // 2
refs = {
    "canon_true": w,
    "canon_rot180": w[::-1, ::-1],
    "canon_flipLR": w[:, ::-1],
    "canon_transpose": w.T,
    "canon_other": co[oy : oy + M, ox : ox + M],
}


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


def spear(rk):  # ladder-ness: rank corr of member AUC against training-tile count
    T = {
        "it1": 3396,
        "it2": 8970,
        "it3": 15286,
        "it0": 20075,
        "it4": 24773,
        "it5": 33061,
    }
    ks = list(T)
    x = np.argsort(np.argsort([T[k] for k in ks])).astype(float)
    y = np.argsort(np.argsort([rk[k] for k in ks])).astype(float)
    return float(np.corrcoef(x, y)[0, 1])


print(
    f"{'reference':<16}{'pos%':>7}"
    + "".join(f"{k:>9}" for k in ["it1", "it2", "it3", "it0", "it4", "it5"])
    + f"{'ladder rho':>12}"
)
res = {}
for name, r in refs.items():
    yb = (r > 0.5).ravel()
    sc = {k: auc(P[k].ravel(), yb) for k in P}
    res[name] = sc
    print(
        f"{name:<16}{yb.mean() * 100:>6.2f}%"
        + "".join(f"{sc[k]:>9.4f}" for k in ["it1", "it2", "it3", "it0", "it4", "it5"])
        + f"{spear(sc):>12.4f}",
        flush=True,
    )
json.dump(res, open("ladder_null_control.json", "w"), indent=2)
