"""Did the injection create a second winding, or just destroy satisfaction?

WHY THIS EXISTS. The injection pilot returned near-zero recall at every arm.
That has two explanations demanding opposite responses: the detector cannot see
planted switches, or the injection never plants one. Reporting the first without
excluding the second would have been a false negative about the detector, and
"the injection must be broken" is exactly the story one tells after a
disappointing number. This measures it instead.

WHAT IT MEASURES, on the same patches, before and after injection:

  * a coordinate sanity check, so a silent no-op in the dataclass reconstruction
    cannot masquerade as a detector failure;
  * satisfied-quad count, which falls if displaced geometry fails the band test
    rather than landing on a neighbouring wrap;
  * mean winding count and mean minority fraction, which rise if the injection
    actually manufactures the two-winding condition the detector looks for.

THE VERDICT IT PRODUCED (2026-08-29, `reports/sheet_switch_injection_pilot_void.md`):
displacement applied correctly (16.087 against dr 16.173), satisfied quads
collapsing 293 -> 126 -> 90 at k = 0, 1, 2, and mean winding count almost flat at
0.950 -> 1.017 -> 1.167. The injected half becomes UNSATISFIED rather than
satisfied on another winding, so it leaves the statistic instead of registering
in it. The injection does not model a sheet switch, and the pilot is void.

Run in the SPIRAL-FITTING venv (it imports villa's fit code):
    FIT_SPIRAL_PATCH_LOAD_WORKERS=1 CUDA_VISIBLE_DEVICES=0 \
    uv run python <repo>/scripts/diagnose_injection_validity.py \
        --run <run_dir> --dataset <spiral_s1> --flags <flags.json>
"""

import argparse
import json
import os
import sys

import numpy as np

SPIRAL = os.environ.get(
    "SPIRAL_SRC", "/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting"
)
sys.path.insert(0, SPIRAL)
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    ),
)


def _verdict(moved, dr):
    """A floor could not see an overshoot.

    The first version read `moved > 0.5 * dr`, written to catch a silent no-op,
    and so it printed OK on a 5.6x error (91 voxels where dr was 16). The
    displacement must land in a BAND around the expected magnitude, not merely
    above a floor. The band is wide because the scan-to-spiral transform carries
    a scale, so the scan-space magnitude is not expected to equal dr exactly.
    """
    if moved < 0.1 * dr:
        return "NO-OP, everything below is meaningless"
    if moved > 10.0 * dr:
        return f"OVERSHOOT {moved / dr:.1f}x dr, suspect the coordinate construction"
    return f"in band ({moved / dr:.2f}x dr)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--flags", required=True)
    ap.add_argument("--n-sample", type=int, default=60)
    ap.add_argument("--space", choices=("spiral", "scan"), default="spiral")
    ap.add_argument("--z-begin", type=int, default=13056)
    ap.add_argument("--z-end", type=int, default=18432)
    args = ap.parse_args()

    import fit_spiral as fs
    import torch
    from checkpoint_io import load_checkpoint_cpu
    from find_inconsistent_windings import build_fit_inputs, build_transform
    from fit_session import conventional_input_paths, load_scroll_spec
    from inject_sheet_switches import displace_half, displace_half_spiral
    from satisfaction_metrics import get_patch_satisfied_areas

    ckpt = load_checkpoint_cpu(os.path.join(args.run, "checkpoint_fitted.ckpt"))
    cfg, _s, _p, mz0, mz1 = build_fit_inputs(
        ckpt,
        os.path.join(args.dataset, "verified_patches"),
        (),
        args.z_begin,
        args.z_end,
        os.path.join(args.dataset, "umbilicus.json"),
        None,
    )
    spec = load_scroll_spec(args.dataset)
    ctx = fs.FitContext(
        cfg, scroll=spec, paths=conventional_input_paths(args.dataset, spec)
    )
    ctx.load_host_inputs()
    patches, ids = ctx.verified_patches, list(ctx.verified_patches)
    transform, dr_t = build_transform(ckpt, cfg, ctx, mz0, mz1)
    dr = float(dr_t.detach())
    umb = ctx.umbilicus_z_to_yx()

    flagged = set(json.load(open(args.flags))["flagged"])
    clean = [p for p in ids if p not in flagged]
    rng = np.random.default_rng(20260829)
    chosen = set(
        rng.choice(clean, min(args.n_sample, len(clean)), replace=False).tolist()
    )

    dev = None
    for cand in (getattr(transform, "_z", None), getattr(transform, "_yx", None), dr_t):
        if hasattr(cand, "device"):
            dev = cand.device
            break

    def disp(pt, k):
        return (
            displace_half_spiral(pt, transform, dr, k, torch, dev)
            if args.space == "spiral"
            else displace_half(pt, umb, dr, k, torch)
        )

    p0 = next(iter(chosen))
    before = patches[p0].zyxs.clone()
    moved = (disp(patches[p0], 1.0).zyxs - before).abs().max().item()
    print(
        f"sanity: max |zyx| change at k=1: {moved:.3f}  (dr={dr:.3f})"
        f"   {_verdict(moved, dr)}"
    )

    def summarise(plist, label):
        out = get_patch_satisfied_areas(
            transform, dr_t, plist, args.z_begin, args.z_end
        )
        W = {
            p: (a.numpy() if hasattr(a, "numpy") else a)
            for p, a in zip(ids, out[5], strict=False)
        }
        S = {
            p: (m.numpy() if hasattr(m, "numpy") else m)
            for p, m in zip(ids, out[3], strict=False)
        }
        nsat, nwind, minor = [], [], []
        for p in chosen:
            a, m = W[p], S[p]
            if a is None or m is None or a.shape != m.shape:
                continue
            v = a[(a >= 0) & m]
            nsat.append(int(v.size))
            if v.size:
                _, c = np.unique(v, return_counts=True)
                nwind.append(len(c))
                minor.append(1 - c.max() / v.size)
            else:
                nwind.append(0)
                minor.append(0.0)
        print(
            f"  {label:20} satisfied quads median {np.median(nsat):8.0f}   "
            f"mean #windings {np.mean(nwind):.3f}   mean minority frac {np.mean(minor):.4f}"
        )

    summarise([patches[p] for p in ids], "baseline")
    for k in (1.0, 2.0):
        plist = []
        for p in ids:
            if p in chosen:
                n = disp(patches[p], k)
                plist.append(n if n is not None else patches[p])
            else:
                plist.append(patches[p])
        summarise(plist, f"injected k={k}")


if __name__ == "__main__":
    main()
