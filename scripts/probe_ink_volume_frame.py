"""Which coordinate frame is a spiral fit's mesh in, relative to the ink volume?

Why this exists. `render_ink.py` assumes the fitted mesh coordinates are already
in the ink volume's level-0 frame. It exposes `--scale` and `--group-idx`, which
choose the pyramid level and the pixels-per-voxel, but nothing that says "the
mesh is in a different frame". When the assumption is wrong the render still
exits 0 and writes a strip that is entirely black, reported only as `p95=0.0` in
passing. That is a silent failure, so it is worth a direct check before trusting
any rendered ink.

For the published data as of 2026-08-30 the assumption IS wrong:

    spiral_datasets/PHercParis4/lasagna_inputs/las_008_*  level 0 = [18946, 8174, 8174]   (9.6 um)
    representations/predictions/ink-3d/...v3-78k-fullsup  level 0 = [75784, 32693, 32693] (2.4 um)

exactly 4x, so a fit run on the published lasagna inputs produces meshes that
must be scaled by 4 to index the published ink volume. vc_render_tifxyz has
`--scale-segmentation` for this; render_ink.py does not pass it, so it has to be
injected through `--vc-render-bin` pointing at a wrapper.

This probe samples the ink volume at the mesh's vertices under each candidate
scale and reports which one lands on data. A correct scale reads mostly nonzero;
a wrong one reads all zeros while staying in bounds, which is why "in bounds" is
not evidence of anything on its own.
"""

import argparse
import os

import numpy as np

DEFAULT_INK = (
    "https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/"
    "predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh_dir", help="a single tifxyz mesh folder (x/y/z.tif)")
    ap.add_argument("--ink-url", default=DEFAULT_INK)
    ap.add_argument("--scales", type=float, nargs="+", default=[1, 2, 4, 8])
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import fsspec
    import tifffile
    import zarr

    a0 = zarr.open(fsspec.get_mapper(args.ink_url), mode="r")["0"]
    print(f"ink volume level 0: {a0.shape} {a0.dtype}")

    xyz = [tifffile.imread(os.path.join(args.mesh_dir, f"{c}.tif")) for c in "xyz"]
    ok = np.ones(xyz[0].shape, bool)
    for t in xyz:
        ok &= t > -0.5  # -1 marks an unmapped grid cell
    X, Y, Z = (t[ok] for t in xyz)
    if X.size == 0:
        raise SystemExit(f"no valid vertices in {args.mesh_dir}")
    rng = np.random.default_rng(args.seed)
    idx = rng.choice(X.size, min(args.samples * 2, X.size), replace=False)
    X, Y, Z = X[idx], Y[idx], Z[idx]
    print(
        f"{X.size} sampled vertices; raw ranges "
        f"x {X.min():.0f}..{X.max():.0f}  y {Y.min():.0f}..{Y.max():.0f}  "
        f"z {Z.min():.0f}..{Z.max():.0f}\n"
    )

    print(
        f"{'scale':>6}{'in bounds':>12}{'sampled':>9}{'nonzero':>10}{'mean':>9}{'max':>6}"
    )
    for s in args.scales:
        zz = np.round(Z * s).astype(np.int64)
        yy = np.round(Y * s).astype(np.int64)
        xx = np.round(X * s).astype(np.int64)
        inb = (
            (zz >= 0)
            & (zz < a0.shape[0])
            & (yy >= 0)
            & (yy < a0.shape[1])
            & (xx >= 0)
            & (xx < a0.shape[2])
        )
        take = np.flatnonzero(inb)[: args.samples]
        if take.size == 0:
            print(f"{s:>6g}{inb.mean() * 100:>11.1f}%{0:>9}{'':>10}{'':>9}{'':>6}")
            continue
        vals = np.array([int(a0[int(zz[i]), int(yy[i]), int(xx[i])]) for i in take])
        print(
            f"{s:>6g}{inb.mean() * 100:>11.1f}%{vals.size:>9}"
            f"{np.mean(vals > 0) * 100:>9.1f}%{vals.mean():>9.2f}{vals.max():>6}"
        )


if __name__ == "__main__":
    main()
