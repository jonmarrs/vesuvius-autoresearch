"""Build a filtered spiral dataset as a symlink farm.

Registered in docs/preregistration/2026-09-03_patch_bootstrap.md. Selects patches
either by the reference fit's per-patch satisfied `fraction` (BOOTSTRAP) or
uniformly at random to the same count (RANDOM control).

The control is the point. Filtering by satisfaction also removes ~24% of patch
area, so a filtered fit could differ from baseline through having LESS evidence
rather than better evidence. Only BOOTSTRAP vs RANDOM separates those.

Symlinks, not copies: the source dataset is 51 GB.
"""

import argparse
import json
import os
import random
import sys


def load_fractions(satisfied_json):
    with open(satisfied_json) as f:
        return {
            p["id"]: (p["fraction"], p["total_area"]) for p in json.load(f)["patches"]
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="original dataset dir")
    ap.add_argument(
        "--satisfied", required=True, help="reference fit's satisfied_fitted.json"
    )
    ap.add_argument("--out", required=True, help="filtered dataset dir to create")
    ap.add_argument("--mode", choices=("bootstrap", "random"), required=True)
    ap.add_argument("--threshold", type=float, default=0.90)
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for --mode random")
    args = ap.parse_args()

    src_patches = os.path.join(args.source, "verified_patches")
    if not os.path.isdir(src_patches):
        raise SystemExit(f"no verified_patches in {args.source}")
    on_disk = set(os.listdir(src_patches))
    frac = load_fractions(args.satisfied)

    missing = [i for i in frac if i not in on_disk]
    if missing:
        raise SystemExit(
            f"{len(missing)} scored patches absent from disk, e.g. {missing[:3]}"
        )

    keep_boot = sorted(i for i, (f, _) in frac.items() if f >= args.threshold)
    if args.mode == "bootstrap":
        keep = keep_boot
    else:
        # Match bootstrap on AREA, not patch count. The losses integrate over
        # surface area; patch count is an artefact of how traces were split. A
        # count-matched control left the arms 76.4% vs 70.0% of area, so part of
        # any difference would have been quantity rather than quality.
        target = sum(frac[i][1] for i in keep_boot)
        rng = random.Random(args.seed)
        pool = sorted(frac)
        rng.shuffle(pool)
        keep, acc = [], 0.0
        for pid in pool:
            if acc >= target:
                break
            keep.append(pid)
            acc += frac[pid][1]
        keep = sorted(keep)

    tot_area = sum(a for _, a in frac.values())
    kept_area = sum(frac[i][1] for i in keep)

    if os.path.exists(args.out):
        raise SystemExit(f"refusing to overwrite existing {args.out}")
    os.makedirs(os.path.join(args.out, "verified_patches"))
    for entry in os.listdir(args.source):
        if entry == "verified_patches":
            continue
        os.symlink(os.path.join(args.source, entry), os.path.join(args.out, entry))
    for pid in keep:
        os.symlink(
            os.path.join(src_patches, pid),
            os.path.join(args.out, "verified_patches", pid),
        )

    print(f"mode={args.mode} threshold={args.threshold} seed={args.seed}")
    print(f"  scored patches      {len(frac)}")
    print(f"  kept                {len(keep)} ({100 * len(keep) / len(frac):.1f}%)")
    print(f"  kept area           {100 * kept_area / tot_area:.1f}% of total")
    print(f"  bootstrap count     {len(keep_boot)}  <- random arm matches this")
    print(f"  wrote               {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
