"""Population statistics over every instance-label mask, before spending on CT.

See reports/scan_quality_reachability.md. Masks are 0.84 MB against 34 MB with
CT, so the whole 80-cube population costs less than two cubes of volume. A
12-cube sample put the contact-fraction maximum at 1.10%; the population maximum
is 3.166%.

Spread here is spread in GEOMETRY, not scan quality: the CT-level outcome that
was the actual target is saturated at ~0.999 in every cube.
"""

import json
import os

import nrrd
import numpy as np

D = "/home/jon/openclaw-workspace/Neo-VM/data/scroll1_cubes/masks"
out = []
for i, f in enumerate(sorted(os.listdir(D))):
    m, _ = nrrd.read(os.path.join(D, f))
    ids = np.unique(m)
    ids = ids[ids > 0]
    L = m > 0
    bnd = np.zeros_like(L)
    surf = np.zeros_like(L)
    for ax in (0, 1, 2):
        a = np.take(m, range(0, m.shape[ax] - 1), axis=ax)
        b = np.take(m, range(1, m.shape[ax]), axis=ax)
        d = (a != b) & (a > 0) & (b > 0)
        sl = [slice(None)] * 3
        sl[ax] = slice(0, m.shape[ax] - 1)
        bnd[tuple(sl)] |= d
        la = np.take(L, range(0, L.shape[ax] - 1), axis=ax)
        lb = np.take(L, range(1, L.shape[ax]), axis=ax)
        surf[tuple(sl)] |= la ^ lb
    out.append(
        {
            "cube": f[:-10],
            "sheets": int(len(ids)),
            "lab_pct": float(100 * L.mean()),
            "contact_pct": float(100 * bnd.sum() / max(L.sum(), 1)),
            "thickness": float(L.sum() / max(surf.sum(), 1)),
        }
    )
    if (i + 1) % 20 == 0:
        print(f"  {i + 1}/80", flush=True)
json.dump(
    out,
    open("/home/jon/openclaw-workspace/Neo-VM/data/scroll1_cubes/mask_stats.json", "w"),
)
print("wrote mask_stats.json")
