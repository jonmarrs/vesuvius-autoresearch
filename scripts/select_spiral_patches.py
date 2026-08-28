"""Which verified patches lie in the z-ROI we can actually fit on one 24 GB GPU?

WHY. `verified_patches/` holds 89,237 directories of 5 files each, with no
tarball, so fetching all of it over HTTP is not viable. The fit filters host
inputs by z anyway (`z_begin`/`z_end` are documented as affecting "host input
filtering"), so only patches intersecting the ROI matter.

COORDINATES. Patch bboxes are in a different space from the resident pool:
they reach z 18241 against a pool array of 9473 z. The factor is 2, established
two ways in `scripts/size_spiral_roi.py` and confirmed exactly by the upstream
fixture's `base_shape_zyx` [18946, 8174, 8174] being 2x the respool
`array_shape` [9473, 4087, 4087] on every axis. ROIs are given here in POOL
coordinates and converted once, so the ROI matches the VRAM sizing directly.

SELECTION IS INCLUSIVE. A patch is selected if its bbox z INTERSECTS the ROI,
not if it is contained. A patch straddling the boundary still contributes
geometry inside it, and dropping it would silently thin the fit at the ROI
edges, which is exactly where a fit is already weakest.

LIMITS. This selects on the bbox only. A bbox intersecting the ROI does not
guarantee the patch has surface inside it, so the count is an upper bound on
what the fit will actually use. Size estimates come from sampling real patch
directories, not from `area_vx2`, because the on-disk cost is dominated by the
grid dimensions rather than the traced area.

Run:
    uv run python scripts/select_spiral_patches.py [--pool-z0 6528 --pool-z1 9216]
"""

import argparse
import glob
import json
import os

PATCH_PER_POOL = 2  # patch coords are 2x pool coords; see module docstring
DATA = os.environ.get(
    "SPIRAL_DATA", "/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1"
)


def load_metas(meta_dir):
    out = []
    for path in glob.glob(os.path.join(meta_dir, "*.json")):
        try:
            doc = json.load(open(path))
            bbox = doc["bbox"]
        except (OSError, ValueError, KeyError):
            continue
        out.append(
            {
                "name": os.path.basename(path)[:-5],
                "z0": float(bbox[0][2]),
                "z1": float(bbox[1][2]),
                "area": float(doc.get("area_vx2", 0.0)),
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool-z0", type=int, default=6528)
    ap.add_argument("--pool-z1", type=int, default=9216)
    ap.add_argument("--out", default=os.path.join(DATA, "patches_in_roi.txt"))
    args = ap.parse_args()

    meta_dir = os.path.join(DATA, "metas")
    metas = load_metas(meta_dir)
    total_listed = sum(1 for _ in open(os.path.join(DATA, "patch_dirs.txt")))
    z0, z1 = args.pool_z0 * PATCH_PER_POOL, args.pool_z1 * PATCH_PER_POOL

    hit = [m for m in metas if m["z1"] >= z0 and m["z0"] <= z1]
    contained = [m for m in hit if m["z0"] >= z0 and m["z1"] <= z1]

    print(
        f"metas read      : {len(metas)} of {total_listed} listed"
        f"{'  (SWEEP INCOMPLETE)' if len(metas) < total_listed else ''}"
    )
    print(f"ROI, pool coords: z {args.pool_z0}-{args.pool_z1}")
    print(f"ROI, patch coords: z {z0}-{z1}  (x{PATCH_PER_POOL})\n")
    print(
        f"  intersecting ROI : {len(hit):6d}  ({len(hit) / max(len(metas), 1):5.1%} of metas read)"
    )
    print(
        f"  fully contained  : {len(contained):6d}   <- NOT the selection; shown for contrast"
    )
    print(
        f"  straddling edge  : {len(hit) - len(contained):6d}   included deliberately"
    )
    if metas:
        area_in = sum(m["area"] for m in hit)
        area_all = sum(m["area"] for m in metas)
        print(
            f"\n  traced area in ROI: {area_in / max(area_all, 1e-9):5.1%} of all area read"
        )

    if len(metas) < total_listed:
        print(
            "\nSweep incomplete: counts scale but are not final. Not writing the fetch list."
        )
        return
    with open(args.out, "w") as fh:
        for m in sorted(hit, key=lambda m: m["name"]):
            fh.write(m["name"] + "\n")
    print(f"\nwrote {len(hit)} names to {args.out}")


if __name__ == "__main__":
    main()
