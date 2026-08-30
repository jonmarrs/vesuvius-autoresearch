"""Recover per-quad winding indices from a finished spiral fit, offline.

WHY THIS EXISTS. `satisfaction_metrics.get_patch_satisfied_areas` computes
`target_winding_idx_per_patch`, an integer winding index per quad, on every run
and **never persists it**. It is the quantity a sheet-switch detector needs, so
it has to be recomputed from a checkpoint. This does that in about 8 seconds of
scoring on top of a ~130 s patch load, and caches the result so the detector
does not re-pay the load on every iteration.

NOTHING IS REIMPLEMENTED. The checkpoint, patches and spiral transform are
loaded through upstream's own entry points (`load_checkpoint_cpu`,
`build_fit_inputs`, `build_transform`), and scoring is upstream's own
`get_patch_satisfied_areas`.

THREE INTERFACE FACTS, each of which cost a run to discover:

  * `context.verified_patches` is a **dict** keyed by patch id, while
    `get_patch_satisfied_areas` wants a **list of patch objects**. Iterating the
    dict hands it id strings and it fails inside the atlas constructor.
  * input paths must be resolved with `load_scroll_spec` +
    `conventional_input_paths` on the DATASET ROOT. `find_inconsistent_windings`
    derives paths from `--patches-dir`, which does not locate `outer_shell`, and
    the load then fails on a winding-model requirement.
  * the parallel patch loader can die with a forkserver `ConnectionResetError`;
    `FIT_SPIRAL_PATCH_LOAD_WORKERS=1` avoids it.

SATISFIED MASKS ARE CACHED TOO, deliberately. A winding index is only meaningful
where the metric ACCEPTS the quad; in rejected regions the assigned target can be
arbitrary, so a disagreement there is weak evidence. The detector restricts to
satisfied quads and needs the masks to do it.

Run:
    FIT_SPIRAL_PATCH_LOAD_WORKERS=1 CUDA_VISIBLE_DEVICES=0 \
    uv run python scripts/extract_winding_indices.py \
        --run <run_dir> --dataset <spiral_s1> --out <cache.pkl>
"""

import argparse
import os
import pickle
import sys

import numpy as np

SPIRAL = os.environ.get(
    "SPIRAL_SRC", "/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--run", required=True, help="fit run directory (holds checkpoint_fitted.ckpt)"
    )
    ap.add_argument("--dataset", required=True, help="spiral dataset root")
    ap.add_argument("--out", required=True, help="destination .pkl")
    ap.add_argument("--z-begin", type=int, default=13056)
    ap.add_argument("--z-end", type=int, default=18432)
    args = ap.parse_args()

    sys.path.insert(0, SPIRAL)
    import fit_spiral as fs
    from checkpoint_io import load_checkpoint_cpu
    from find_inconsistent_windings import build_fit_inputs, build_transform
    from fit_session import conventional_input_paths, load_scroll_spec
    from satisfaction_metrics import get_patch_satisfied_areas

    ckpt_path = os.path.join(args.run, "checkpoint_fitted.ckpt")
    ckpt = load_checkpoint_cpu(ckpt_path)
    cfg, _scroll, _paths, mz0, mz1 = build_fit_inputs(
        ckpt,
        os.path.join(args.dataset, "verified_patches"),
        (),
        args.z_begin,
        args.z_end,
        os.path.join(args.dataset, "umbilicus.json"),
        None,
    )
    print(f"checkpoint z-range [{mz0}, {mz1})", flush=True)

    spec = load_scroll_spec(args.dataset)
    paths = conventional_input_paths(args.dataset, spec)
    context = fs.FitContext(cfg, scroll=spec, paths=paths)
    context.load_host_inputs()
    patches = context.verified_patches
    patch_ids = list(patches)
    print(f"patches: {len(patch_ids)}", flush=True)

    transform, dr = build_transform(ckpt, cfg, context, mz0, mz1)
    out = get_patch_satisfied_areas(
        transform, dr, [patches[k] for k in patch_ids], args.z_begin, args.z_end
    )
    widx, masks = out[5], out[3]

    def to_np(x, dtype):
        if x is None:
            return None
        x = x.numpy() if hasattr(x, "numpy") else np.asarray(x)
        return x.astype(dtype)

    payload = {
        "run": os.path.basename(os.path.normpath(args.run)),
        "dr": float(dr.detach()),
        "z": (args.z_begin, args.z_end),
        "patches": [
            (p, to_np(a, np.int32)) for p, a in zip(patch_ids, widx, strict=False)
        ],
        "satisfied": [
            (p, to_np(m, bool)) for p, m in zip(patch_ids, masks, strict=False)
        ],
    }
    with open(args.out, "wb") as fh:
        pickle.dump(payload, fh)
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 2**20:.0f} MiB)")


if __name__ == "__main__":
    main()
