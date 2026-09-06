"""Reclaim fit checkpoints that no committed artifact refers to.

A finished spiral fit leaves `checkpoint_fitted.ckpt` at ~2.1 GB, which is **91%
of the arm's footprint**, while the analysis reads an 837-byte
`satisfaction_metrics_fitted.json`. The 281 MB of meshes beside it are what a
re-render needs; the checkpoint only matters if you intend to resume the fit or
introspect it offline. On 2026-09-06, 24 of 25 checkpoints here (48.3 GB) were
referenced by nothing.

**The one that was referenced is the whole reason this is a script.** Two live
reports work from `baseline01/checkpoint_fitted.ckpt`
(`sheet_switch_baseline_signal.md` runs offline from it; `spiral_baseline_fit_*`
names it). An earlier session asserted checkpoints were stale, was told to clear
them, checked first, and found every one cited — so "these are surely disposable"
is a claim this project has already got wrong once.

So the reference check is not advisory here: this greps the repo for each
checkpoint's arm directory name and **refuses to delete any arm that is
mentioned**, rather than leaving that to the operator's memory. Dry-run is the
default.
"""

import argparse
import os
import subprocess
import sys

CKPT = "checkpoint_fitted.ckpt"
# Where a committed reference to an arm would live. Logs are deliberately
# excluded: a training log mentioning an arm is not a dependency on its
# checkpoint, and including them would protect everything forever.
SEARCH_SUBDIRS = ("reports", "docs", "scripts", "repro", "tests")


def find_checkpoints(spiral_out):
    out = []
    for entry in sorted(os.listdir(spiral_out)):
        p = os.path.join(spiral_out, entry, CKPT)
        if os.path.isfile(p):
            out.append((entry, p, os.path.getsize(p)))
    return out


def is_referenced(repo, arm_dir):
    """True if any committed artifact names this arm directory.

    Matches the directory name, which is what reports actually cite (e.g.
    `..._baseline01/checkpoint_fitted.ckpt`), and also the short tag after
    `-patch_`, since some reports refer to an arm by tag alone.
    """
    needles = [arm_dir]
    if "-patch_" in arm_dir:
        needles.append(arm_dir.split("-patch_", 1)[1])
    for needle in needles:
        dirs = [os.path.join(repo, d) for d in SEARCH_SUBDIRS]
        dirs = [d for d in dirs if os.path.isdir(d)]
        if not dirs:
            continue
        r = subprocess.run(
            ["grep", "-rlF", needle, *dirs],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and r.stdout.strip():
            return True, needle
    return False, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spiral-out", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument(
        "--delete",
        action="store_true",
        help="actually remove; without this the run is a dry run",
    )
    args = ap.parse_args()

    ckpts = find_checkpoints(args.spiral_out)
    if not ckpts:
        print(f"no {CKPT} under {args.spiral_out}")
        return 0

    keep, drop = [], []
    for arm, path, size in ckpts:
        ref, needle = is_referenced(args.repo, arm)
        (keep if ref else drop).append((arm, path, size, needle))

    print(f"{len(ckpts)} checkpoint(s), {sum(c[2] for c in ckpts) / 2**30:.1f} GB\n")
    if keep:
        print("REFERENCED -- will not be touched:")
        for arm, _, size, needle in keep:
            print(f"  {size / 2**30:5.1f} GB  {arm}   (matched {needle!r})")
    if drop:
        print("\nunreferenced:")
        for arm, _, size, _ in drop:
            print(f"  {size / 2**30:5.1f} GB  {arm}")
    print(f"\nreclaimable: {sum(d[2] for d in drop) / 2**30:.1f} GB")

    if not args.delete:
        print("\nDRY RUN. Re-run with --delete to remove the unreferenced ones.")
        return 0

    n = 0
    for arm, path, _, _ in drop:
        if os.path.basename(path) != CKPT or not os.path.isfile(path):
            print(f"  REFUSED (unexpected path): {path}")
            continue
        os.remove(path)
        n += 1
    print(f"\ndeleted {n} checkpoint(s); kept {len(keep)} referenced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
