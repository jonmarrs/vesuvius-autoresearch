"""Fetch the GT region from the 2.4um zarr. Chunks carry full depth, so a
[:, y0:y1, x0:x1] slice costs only the tiles it covers."""

import fsspec
import numpy as np
import zarr

URL = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/"
    "20231210121321/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr"
)
Y0, X0, SIZE = 4000, 2500, 4096  # exactly ScrollGT's target region, level 2
g = zarr.open(fsspec.get_mapper(URL), mode="r")
a = g["2"]
print("level2", a.shape, a.dtype, flush=True)
out = np.empty((a.shape[0], SIZE, SIZE), np.uint8)
step = 512
for y in range(0, SIZE, step):
    out[:, y : y + step, :] = a[:, Y0 + y : Y0 + y + step, X0 : X0 + SIZE]
    print(f"  rows {y + step}/{SIZE}", flush=True)
np.save("/home/jon/openclaw-workspace/Neo-VM/data/ink_ablation/region_full.npy", out)
print("saved", out.shape, out.dtype, f"{out.nbytes / 2**30:.2f} GiB")
