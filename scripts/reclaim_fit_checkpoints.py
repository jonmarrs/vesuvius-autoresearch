"""Reclaim optimizer checkpoints from finished fits, keeping everything a
re-render or re-analysis needs.

2026-09-14: `/` reached 99% full with 14G free while a 3-arm study had two arms
still to render. Each arm costs ~5G persistently, so the chain was projected to
finish its last arm at ~3G -- below the 10G `preflight.sh` wants for a single arm.

A fit directory is ~4.3G, and it decomposes:

    checkpoint_fitted.ckpt   4.0G   optimizer state; needed only to RESUME a fit
    meshes/                  287M   needed to RE-RENDER the arm
    satisfied_fitted.json    6.2M   needed for patch-selection studies

So deleting whole fit directories to make room would destroy the meshes, which are
the expensive-to-recreate part (a fit is ~3 hours; a re-render reuses its meshes).
Deleting only the checkpoint frees 93% of the space and forecloses nothing except
resuming that particular fit -- which nothing in this project does; fits are always
run fresh from the dataset.

**Dry run by default.** Nothing is deleted without `--apply`.

Protected by default: every arm of the live consensus study, because a running
chain may still write to them and because `curbase_s2`/`s3` meshes are what a
clean triplet A would re-render from.

  ./.venv/bin/python scripts/reclaim_fit_checkpoints.py                # show plan
  ./.venv/bin/python scripts/reclaim_fit_checkpoints.py --apply        # do it
"""

import argparse
import sys
from pathlib import Path

SPIRAL_OUT = "/home/jon/openclaw-workspace/Neo-VM/spiral_out"
CKPT = "checkpoint_fitted.ckpt"
# The live study. Its fit dirs stay whole: the chain may still be writing, and a
# clean triplet A would re-render from s2/s3 meshes.
PROTECTED = tuple(f"curbase_s{i}" for i in range(1, 10)) + ("curbase_s1rr",)


def arm_of(fit_dir: Path) -> str:
    return (
        fit_dir.name.split("patch_", 1)[-1]
        if "patch_" in fit_dir.name
        else fit_dir.name
    )


def find(spiral_out: str) -> list[tuple[Path, str, int]]:
    out = []
    for c in sorted(Path(spiral_out).glob(f"*/{CKPT}")):
        try:
            out.append((c, arm_of(c.parent), c.stat().st_size))
        except OSError:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spiral-out", default=SPIRAL_OUT)
    ap.add_argument("--apply", action="store_true", help="actually delete")
    ap.add_argument(
        "--also", nargs="*", default=[], help="additionally allow these arms"
    )
    args = ap.parse_args()

    protected = set(PROTECTED) - set(args.also)
    rows = find(args.spiral_out)
    if not rows:
        print("no checkpoints found")
        return 0

    free_ck = [(p, a, s) for p, a, s in rows if a not in protected]
    kept = [(p, a, s) for p, a, s in rows if a in protected]

    print(f"{'arm':<22}{'size':>8}  action")
    for _, a, s in sorted(kept):
        print(f"{a:<22}{s / 2**30:>7.1f}G  KEEP (protected: live study)")
    for _, a, s in sorted(free_ck):
        print(f"{a:<22}{s / 2**30:>7.1f}G  reclaim")

    total = sum(s for _, _, s in free_ck) / 2**30
    print(
        f"\n{len(free_ck)} checkpoint(s), {total:.1f}G reclaimable; "
        f"{len(kept)} kept ({sum(s for _, _, s in kept) / 2**30:.1f}G)"
    )
    print("meshes/, satisfied_fitted.json and every outer_* directory are untouched.")

    if not args.apply:
        print("\nDRY RUN. Nothing deleted. Re-run with --apply to reclaim.")
        return 0

    freed = 0
    for path, arm, size in free_ck:
        # Re-check the sibling meshes survive: deleting a checkpoint must never be
        # the step that leaves an arm unrenderable.
        if not (path.parent / "meshes").is_dir():
            print(
                f"  SKIP {arm}: no meshes/ beside it; refusing to strip its last artifact"
            )
            continue
        try:
            path.unlink()
            freed += size
            print(f"  freed {size / 2**30:.1f}G  {arm}")
        except OSError as e:
            print(f"  FAILED {arm}: {e}")
    print(f"\nreclaimed {freed / 2**30:.1f}G")
    return 0


if __name__ == "__main__":
    sys.exit(main())
