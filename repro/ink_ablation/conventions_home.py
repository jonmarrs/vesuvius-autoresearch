"""Which documented input convention reproduces the published prediction?

The card documents three and they disagree. This measures all three, plus the
one we settled on, against the published canon prediction on the models' OWN
scroll (PHerc 1667 w011), where these checkpoints demonstrably read text. Home
scroll on purpose: a disagreement there cannot be blamed on cross-scroll transfer.
"""

import fsspec
import numpy as np
import torch
import zarr
from transformers import AutoModel

URL = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1667/segments/"
    "20260108140509-w011_20260108140509268_flatboi/surface-volumes/"
    "2.399um-0.22m-78keV-volume-20251217075048.zarr"
)
a = zarr.open(fsspec.get_mapper(URL), mode="r")["0"]
lo, N = a.shape[0] // 2 - 31, 2048
Y0, X0 = a.shape[1] // 2, a.shape[2] // 2
print(f"level0 {a.shape}  window {N}^2 at y={Y0} x={X0}", flush=True)
blk = np.asarray(a[lo : lo + 62, Y0 : Y0 + N, X0 : X0 + N])

CONV = {
    "docstring: z-score per tile": lambda t: (t - t.mean()) / (t.std() + 1e-6),
    "card prose: clip(0,200) then Normalize(mean=0,std=1) == identity": lambda t: (
        np.clip(t, 0, 200)
    ),
    "card snippet: raw uint8, no normalisation": lambda t: t,
    "what we use: clip(0,200)/255": lambda t: np.clip(t, 0, 200) / 255.0,
}
print("\npublished canon on this segment fires above 0.5 at 2.82%\n")
print(f"{'convention':<62}{'it5 above0.5':>14}{'mean':>9}")
for name, f in CONV.items():
    m = AutoModel.from_pretrained("it5", trust_remote_code=True).eval().cuda()
    out = np.empty((N // 4, N // 4), np.float32)
    with torch.no_grad():
        for ty in range(N // 256):
            for tx in range(N // 256):
                t = blk[:, ty * 256 : (ty + 1) * 256, tx * 256 : (tx + 1) * 256].astype(
                    np.float32
                )
                o = m(torch.from_numpy(f(t).astype(np.float32))[None, None].cuda())
                o = o.logits if hasattr(o, "logits") else o
                out[ty * 64 : (ty + 1) * 64, tx * 64 : (tx + 1) * 64] = (
                    torch.sigmoid(torch.as_tensor(o)).float().cpu().numpy()
                )
    print(f"{name:<62}{(out > 0.5).mean() * 100:>13.2f}%{out.mean():>9.4f}", flush=True)
    del m
    torch.cuda.empty_cache()
