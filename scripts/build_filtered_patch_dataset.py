"""Build a filtered spiral dataset as a symlink farm.

Registered in docs/preregistration/2026-09-03_patch_bootstrap.md. Selects patches
either by the reference fit's per-patch satisfied `fraction` (BOOTSTRAP) or
uniformly at random to the same total area (RANDOM control).

The control is the point. Filtering by satisfaction also removes ~24% of patch
area, so a filtered fit could differ from baseline through having LESS evidence
rather than better evidence. Only BOOTSTRAP vs RANDOM separates those.

Symlinks, not copies: the source dataset is 51 GB.
"""

import argparse
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.patch_dataset_artifacts import (
    MANIFEST,
    dataset_links,
    number,
    publish_dataset,
    reference_patches,
)


def load_fractions(satisfied_json):
    return reference_patches(satisfied_json)[1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="original dataset dir")
    ap.add_argument(
        "--satisfied", required=True, help="reference fit's satisfied_fitted.json"
    )
    ap.add_argument("--out", required=True, help="filtered dataset dir to create")
    ap.add_argument("--mode", choices=("bootstrap", "random"), required=True)
    ap.add_argument("--threshold", type=float, default=0.90)
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for --mode random")
    args = ap.parse_args(argv)
    try:
        return build(args)
    except (OSError, ValueError, TypeError, OverflowError, RuntimeError) as exc:
        print(f"Patch dataset preparation failed: {exc}", file=sys.stderr)
        return 1


def build(args):
    number(args.threshold, "threshold", upper=1)
    reference, frac = reference_patches(args.satisfied)
    links = dataset_links(args.source, frac)

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
    publish_dataset(
        links,
        args.out,
        keep,
        {
            "mode": args.mode,
            "threshold": args.threshold,
            "seed": args.seed,
            "reference": reference.provenance(),
            "scored_patches": len(frac),
            "total_reference_area": tot_area,
            "selected_area": kept_area,
            "bootstrap_target_area": sum(frac[i][1] for i in keep_boot),
            "selected_count": len(keep),
            "bootstrap_count": len(keep_boot),
            "matching_basis": "total_area; random uses the original seeded greedy draw",
        },
        inputs=(reference.path,),
        verify=reference.verify,
    )

    print(f"mode={args.mode} threshold={args.threshold} seed={args.seed}")
    print(f"  scored patches      {len(frac)}")
    print(f"  kept                {len(keep)} ({100 * len(keep) / len(frac):.1f}%)")
    print(f"  kept area           {100 * kept_area / tot_area:.1f}% of total")
    print(f"  bootstrap count     {len(keep_boot)}  (random matches area, not count)")
    print(f"  wrote               {args.out}")
    print(f"  selection record    {Path(args.out) / MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
