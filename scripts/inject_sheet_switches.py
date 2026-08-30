"""Plant sheet switches of known location and magnitude, and see if the detector finds them.

PRE-REGISTERED in `docs/preregistration/2026-08-29_sheet_switch_detector.md`.
The detector was frozen before this ran; nothing here may change it.

WHAT IS INJECTED. A sheet switch is a PARTIAL displacement: part of a traced
surface jumps to a neighbouring wrap while the rest stays. So for a selected
patch, the valid vertices in a contiguous half (columns >= W/2) are moved
radially about the umbilicus by `k * dr`, and the other half is left alone. That
manufactures an internal discontinuity at a known place with a known magnitude.

A WHOLE-patch displacement is deliberately NOT injected: it is invisible to the
satisfaction metric by design, which @pmh47 established on villa#1621, and
nothing here disputes that.

ELIGIBILITY. Only patches the detector does NOT flag at baseline are injected, so
recall is measured on clean patches rather than on ones already firing.

ARMS. `k = 0` is the null control: injecting nothing must leave the flag set
unchanged, or the injection path itself perturbs geometry and the run is void.
`k in {0.5, 1.5}` are half-winding controls, which are grosser errors and must be
caught at least as often as the whole-winding arms, or the detector is
miscalibrated.

COST. Patch loading is ~130 s and dominates, so every arm is scored inside one
process: load once, re-score per arm at ~8 s.

Run (in the SPIRAL-FITTING venv; the extractor's environment note applies):
    FIT_SPIRAL_PATCH_LOAD_WORKERS=1 CUDA_VISIBLE_DEVICES=0 \
    uv run python <repo>/scripts/inject_sheet_switches.py \
        --run <baseline_run_dir> --dataset <spiral_s1> --flags <flags.json> \
        --out <results.json> [--n-inject 200] [--seeds 3]
"""

import argparse
import copy
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

K_ARMS = [0.0, 0.5, 1.0, 1.5, 2.0]  # frozen in the pre-registration


def displace_half(patch, umb_zyx_to_yx, dr, k, torch):
    """Move the valid vertices of one contiguous half radially by k*dr."""
    z = patch.zyxs.clone()
    h, w = z.shape[:2]
    valid = torch.any(z != -1, dim=-1)
    half = torch.zeros_like(valid)
    half[:, w // 2 :] = True
    sel = valid & half
    if not bool(sel.any()):
        return None
    idx = torch.stack(torch.where(sel), dim=-1)
    pts = z[sel]  # (n, 3) zyx
    cy, cx = umb_zyx_to_yx(pts[:, 0].cpu().numpy().astype(np.float64)).T
    dy = pts[:, 1].cpu().numpy().astype(np.float64) - cy
    dx = pts[:, 2].cpu().numpy().astype(np.float64) - cx
    r = np.hypot(dy, dx)
    r[r == 0] = 1.0
    scale = (r + k * dr) / r
    out = pts.clone()
    out[:, 1] = torch.tensor(cy + dy * scale, dtype=out.dtype)
    out[:, 2] = torch.tensor(cx + dx * scale, dtype=out.dtype)
    z[idx[:, 0], idx[:, 1]] = out
    new = copy.copy(patch)
    object.__setattr__(new, "zyxs", z) if hasattr(
        type(patch), "__dataclass_fields__"
    ) else None
    try:
        new.__post_init__()
    except Exception:
        pass
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument(
        "--flags", required=True, help="baseline flags json, to pick clean patches"
    )
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-inject", type=int, default=200)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--z-begin", type=int, default=13056)
    ap.add_argument("--z-end", type=int, default=18432)
    args = ap.parse_args()

    import fit_spiral as fs
    import torch
    from checkpoint_io import load_checkpoint_cpu
    from detect_sheet_switches import flag_patches
    from find_inconsistent_windings import build_fit_inputs, build_transform
    from fit_session import conventional_input_paths, load_scroll_spec
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
    context = fs.FitContext(
        cfg, scroll=spec, paths=conventional_input_paths(args.dataset, spec)
    )
    context.load_host_inputs()
    patches = context.verified_patches
    ids = list(patches)
    transform, dr_t = build_transform(ckpt, cfg, context, mz0, mz1)
    dr = float(dr_t.detach())
    umb = context.umbilicus_z_to_yx()
    print(f"patches {len(ids)}  dr {dr:.3f}", flush=True)

    baseline_flagged = set(json.load(open(args.flags))["flagged"])
    clean = [p for p in ids if p not in baseline_flagged]
    print(f"clean (unflagged at baseline) patches eligible: {len(clean)}", flush=True)

    def score(patch_list):
        out = get_patch_satisfied_areas(
            transform, dr_t, patch_list, args.z_begin, args.z_end
        )
        cache = {
            "patches": [
                (p, (a.numpy() if hasattr(a, "numpy") else a))
                for p, a in zip(ids, out[5], strict=False)
            ],
            "satisfied": [
                (p, (m.numpy() if hasattr(m, "numpy") else m))
                for p, m in zip(ids, out[3], strict=False)
            ],
        }
        return set(flag_patches(cache)[0])

    results = []
    for seed in range(args.seeds):
        rng = np.random.default_rng(20260829 + seed)
        chosen = set(
            rng.choice(clean, min(args.n_inject, len(clean)), replace=False).tolist()
        )
        for k in K_ARMS:
            plist, injected = [], []
            for p in ids:
                pt = patches[p]
                if p in chosen and k > 0:
                    new = displace_half(pt, umb, dr, k, torch)
                    if new is not None:
                        plist.append(new)
                        injected.append(p)
                        continue
                plist.append(pt)
            flagged = score(plist)
            inj = set(injected)
            recall = len(flagged & inj) / max(len(inj), 1)
            other = flagged - inj
            results.append(
                {
                    "seed": seed,
                    "k": k,
                    "n_injected": len(inj),
                    "recall": recall,
                    "flags_elsewhere": len(other),
                }
            )
            print(
                f"seed {seed}  k={k:<4}  injected {len(inj):4d}  "
                f"recall {recall:6.1%}  flags elsewhere {len(other)}",
                flush=True,
            )

    with open(args.out, "w") as fh:
        json.dump({"dr": dr, "arms": results, "n_inject": args.n_inject}, fh, indent=2)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
