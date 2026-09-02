"""Check whether any file the spiral render path RUNS differs between two villa refs.

The bump discipline this project learned from a 153-commit jump was "no path our
code reads may move". That is the weaker question. The stronger one is "no file
our code RUNS has changed", and the difference is not academic: bumping to
908aa7f06 moved nothing, passed the path check, and still changed `lasagna/fit.py`
-- the FLATTEN step, which decides the mesh geometry a render is scored on. A
silent change there moves `total_fg_pixels` without touching the scorer at all,
which is the hardest kind of drift to notice from a result.

Renders are built by `repro/spiral_render/setup_workdir.sh`, which extracts
`spiral-fitting`, `lasagna` and `vesuvius/src` from a villa checkout. Everything
executable under those trees is in scope; this script diffs them by blob hash
between two refs and exits nonzero if any differ, so it can gate a pin bump.

Usage:
    check_villa_render_path.py                      # render source vs submodule HEAD
    check_villa_render_path.py 5479453a 908aa7f06
    check_villa_render_path.py --repo path/to/villa OLD NEW
"""

import argparse
import subprocess
import sys
from pathlib import Path

# What setup_workdir.sh extracts. Everything a render can execute lives here.
EXTRACTED_TREES = ("spiral-fitting", "lasagna", "vesuvius/src")

# Files known to be on the hot path, called out by name so a change to one of
# them is reported first rather than buried in a long list.
HOT_PATH = (
    "spiral-fitting/render_ink.py",
    "spiral-fitting/get_ink_metrics.py",
    "spiral-fitting/tifxyz.py",
    "lasagna/fit.py",
)

# The tree renders are actually built from; NOT this repo's villa submodule.
# They have diverged. See repro/spiral_render/setup_workdir.sh.
RENDER_SOURCE_REF = "5479453a"


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if out.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def blobs(repo: Path, ref: str, tree: str) -> dict[str, str]:
    """path -> blob hash for every file under `tree` at `ref`."""
    listing = git(repo, "ls-tree", "-r", f"{ref}:{tree}")
    found = {}
    for line in listing.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 3 and parts[1] == "blob":
            found[f"{tree}/{path}"] = parts[2]
    return found


def compare(repo: Path, old: str, new: str) -> tuple[list[str], list[str], list[str]]:
    """Returns (changed, added, removed) paths across the extracted trees."""
    before, after = {}, {}
    for tree in EXTRACTED_TREES:
        before.update(blobs(repo, old, tree))
        after.update(blobs(repo, new, tree))
    changed = sorted(p for p in before.keys() & after.keys() if before[p] != after[p])
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    return changed, added, removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", nargs="?", default=RENDER_SOURCE_REF)
    ap.add_argument("new", nargs="?", default="HEAD")
    ap.add_argument("--repo", default=None, help="villa checkout (default: ./villa)")
    args = ap.parse_args()

    repo = (
        Path(args.repo)
        if args.repo
        else Path(__file__).resolve().parent.parent / "villa"
    )
    if not repo.exists():
        raise SystemExit(f"no villa checkout at {repo}")

    changed, added, removed = compare(repo, args.old, args.new)
    print(f"villa render path: {args.old} -> {args.new}")
    print(f"  trees compared: {', '.join(EXTRACTED_TREES)}")

    hot = [p for p in changed if p in HOT_PATH]
    other = [p for p in changed if p not in HOT_PATH]

    if hot:
        print(f"\n  HOT PATH CHANGED ({len(hot)}):")
        for p in hot:
            print(f"    {p}")
    if other:
        print(f"\n  other executable files changed ({len(other)}):")
        for p in other[:20]:
            print(f"    {p}")
        if len(other) > 20:
            print(f"    ... and {len(other) - 20} more")
    if removed:
        print(f"\n  REMOVED ({len(removed)}):")
        for p in removed[:20]:
            print(f"    {p}")
    if added:
        print(f"\n  added ({len(added)}): {len(added)} file(s)")

    if changed or removed:
        print(
            "\nVERDICT: the render path DIFFERS between these refs. Work dirs built "
            "from them are not interchangeable, and arms measured across the two are "
            "not comparable without an explicit equivalence check."
        )
        return 1
    print(
        "\nVERDICT: render path identical. Work dirs from either ref are interchangeable."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
