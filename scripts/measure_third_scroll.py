"""Is the calibration shift specific to Scroll 1, or general to non-home scrolls?
Third scroll: PHerc 0139, which publishes a 2.399um surface volume."""

import fsspec
import numpy as np
import torch
import zarr
from transformers import AutoModel

U = {
    "PHerc1667 (home)": (
        "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1667/segments/"
        "20260108140509-w011_20260108140509268_flatboi/surface-volumes/2.399um-0.22m-78keV-volume-20251217075048.zarr"
    ),
    "PHerc0139 (third)": (
        "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0139/segments/"
        "20250108000000-w025_2025010863/surface-volumes/2.399um-0.22m-78keV-volume-20260102150214.zarr"
    ),
}


def prep(t):
    return np.clip(t.astype(np.float32), 0, 200) / 255.0


for mem in ("it3", "it5"):
    m = (
        AutoModel.from_pretrained(
            f"/home/jon/openclaw-workspace/Neo-VM/data/ink_ablation/{mem}",
            trust_remote_code=True,
        )
        .eval()
        .cuda()
    )
    print(f"\n=== {mem} ===", flush=True)
    med = {}
    for name, url in U.items():
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
        med[name] = float(np.median(rates))
        print(
            f"  {name:<20} median {med[name]:.4f}   n={len(rates)}  range {min(rates):.3f}-{max(rates):.3f}",
            flush=True,
        )
    h, t = med["PHerc1667 (home)"], med["PHerc0139 (third)"]
    print(f"  shift home -> PHerc0139: {t / max(h, 1e-9):.2f}x")
    del m
    torch.cuda.empty_cache()
