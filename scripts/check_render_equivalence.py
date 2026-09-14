"""Would a render built from ref B differ from one built from ref A?

The villa monitor answers a narrower question -- has the hot path changed -- and
answers it correctly. This answers the one that follows: **does that change reach
our renders**. On 2026-09-14 those had different answers, and the gap between them
was four manual commands. This is those four commands.

The procedure, in the order that makes each step cheap:

1. **Tree objects** for the three paths `setup_workdir.sh` extracts. Identical
   hashes mean a byte-identical archive -- stronger than an empty diff, which a
   path filter can produce by omission. Most upstream moves stop here.
2. **Render entry points.** If `render_ink.py` and `get_ink_metrics.py` are
   themselves unchanged, the change can only reach a render through a module they
   import.
3. **Import trace.** Which changed modules do the entry points actually import?
   A change to a module nothing imports cannot affect the output.
4. What is left is the set a human must read. The script does not guess whether
   those changes matter; it reduces 43 files to the two or three that could.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

EXTRACTED = ("spiral-fitting", "lasagna", "vesuvius/src")
ENTRY_POINTS = ("spiral-fitting/render_ink.py", "spiral-fitting/get_ink_metrics.py")

# Paths that are PIPELINE STAGES rather than libraries the entry points import.
# `lasagna` is the flatten: run_render.sh invokes it as its own step, so nothing
# in ENTRY_POINTS imports it and the import trace below cannot see it. Treating
# it as import-traced reported RENDER-INERT for a commit titled "lasagna flatten
# memory" that rewrote 571 lines of it -- a false INTERCHANGEABLE, which is the
# failure this tool exists to prevent. Any non-test change here is a suspect.
STAGE_PATHS = ("lasagna",)


def git(repo: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def tree(repo: str, ref: str, path: str) -> str:
    return git(repo, "rev-parse", f"{ref}:{path}")


def changed_files(repo: str, a: str, b: str, path: str) -> list[str]:
    out = git(repo, "diff", "--name-only", a, b, "--", path)
    return [f for f in out.splitlines() if f]


def imports_of(repo: str, ref: str, path: str) -> set[str]:
    """Module names imported by a file, top-level only."""
    src = git(repo, "show", f"{ref}:{path}")
    mods = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", src, re.M):
        mods.add(m.group(1).split(".")[0])
    return mods


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo", default=str(Path(__file__).resolve().parent.parent / "villa")
    )
    ap.add_argument(
        "--from-ref", default="HEAD", help="the ref our corpus was rendered with"
    )
    ap.add_argument("--to-ref", default="origin/main", help="the candidate ref")
    args = ap.parse_args()

    a, b = args.from_ref, args.to_ref
    sa, sb = (
        git(args.repo, "rev-parse", "--short=9", a),
        git(args.repo, "rev-parse", "--short=9", b),
    )
    if not sa or not sb:
        raise SystemExit(f"cannot resolve {a} or {b} in {args.repo}")
    print(f"comparing {sa} -> {sb}\n")

    # 1. tree objects
    differing = [p for p in EXTRACTED if tree(args.repo, a, p) != tree(args.repo, b, p)]
    for p in EXTRACTED:
        same = p not in differing
        print(f"  {p:<16}{'identical' if same else 'DIFFERS'}")
    if not differing:
        print(
            "\nVERDICT: INTERCHANGEABLE — every extracted path is the same tree object,"
        )
        print("so the archive is byte-identical. No render can differ.")
        return 0

    # 2. entry points
    moved = [f for f in ENTRY_POINTS if tree(args.repo, a, f) != tree(args.repo, b, f)]
    print(f"\nrender entry points changed: {', '.join(moved) if moved else 'none'}")
    if moved:
        print("\nVERDICT: RENDERS MAY DIFFER — an entry point itself changed. Read:")
        for f in moved:
            print(f"    git diff {sa} {sb} -- {f}")
        return 0

    # 3. import trace
    imported = set()
    for f in ENTRY_POINTS:
        imported |= imports_of(args.repo, b, f)
    changed = [f for p in differing for f in changed_files(args.repo, a, b, p)]
    non_test = [
        f
        for f in changed
        if "/tests/" not in f and not Path(f).name.startswith("test_")
    ]
    suspects = [f for f in non_test if Path(f).stem in imported]
    # A change inside a pipeline stage counts whether or not anything imports it.
    stage_hits = [
        f for f in non_test if any(f.startswith(s + "/") for s in STAGE_PATHS)
    ]
    for f in stage_hits:
        if f not in suspects:
            suspects.append(f)

    print(
        f"changed files in the differing paths: {len(changed)} "
        f"({len(non_test)} excluding tests)"
    )
    print(
        f"of those, imported by an entry point or inside a pipeline stage: "
        f"{', '.join(suspects) if suspects else 'NONE'}"
    )

    if not suspects:
        print(
            "\nVERDICT: RENDER-INERT — entry points unchanged, nothing changed that they"
        )
        print("import, and no pipeline stage changed.")
        return 0

    print("\nVERDICT: NEEDS A HUMAN — these modules changed AND are imported:")
    for f in suspects:
        print(f"    git diff {sa} {sb} -- {f}")
    print("\nCheck whether the change alters behaviour for inputs we actually have.")
    print("A validation-only change that our data passes is inert in practice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
