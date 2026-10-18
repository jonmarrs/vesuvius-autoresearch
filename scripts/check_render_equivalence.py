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

It exits 2 when it cannot answer: a directory that is not a repository of its
own (an uninitialised submodule, where git answers for this repository), a ref
or git call that fails, or a path at neither ref. Each of those used to read as
an empty tree or no imports, and so as INTERCHANGEABLE or RENDER-INERT.
"""

import argparse
import re
import sys
from pathlib import Path, PurePosixPath

# Resolved, so a symlinked launch under `python -I` still finds its sibling.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_villa_render_path import git, not_own_repository  # noqa: E402

EXTRACTED = ("spiral-fitting", "lasagna", "vesuvius/src")
ENTRY_POINTS = ("spiral-fitting/render_ink.py", "spiral-fitting/get_ink_metrics.py")

# Paths that are PIPELINE STAGES rather than libraries the entry points import.
# `lasagna` is the flatten: run_render.sh invokes it as its own step, so nothing
# in ENTRY_POINTS imports it and the import trace below cannot see it. Treating
# it as import-traced reported RENDER-INERT for a commit titled "lasagna flatten
# memory" that rewrote 571 lines of it -- a false INTERCHANGEABLE, which is the
# failure this tool exists to prevent. Any non-test change here is a suspect.
STAGE_PATHS = ("lasagna",)

# Libraries a pipeline stage imports from another extracted tree, which the
# entry points' import trace cannot see either: lasagna/fit.py imports atlas,
# whose vc3d_fiber_format_adapter puts vesuvius/src on sys.path and imports
# vc3d_fiber_format (run_render.sh says so too). A change to its __init__.py
# alone read RENDER-INERT (villa 757f70c01..b944a656c).
STAGE_LIBRARIES = ("vesuvius/src/vc3d_fiber_format",)

# Where the entry points' imports resolve a top-level name: their own directory,
# and vesuvius/src (an installed package's source).
IMPORT_ROOTS = ("spiral-fitting/", "vesuvius/src/")

# The modes of a file git archive extracts as itself: an entry point that is a
# link or a submodule would be compared as the link, not what it points to.
REGULAR_FILE_MODES = ("100644", "100755")

# Documentation cannot change a render. Excluding it is not a weakening: the
# guard is about executable content, and naming a .md file as a suspect makes
# a reader trust the genuine entries beside it less.
DOC_SUFFIXES = (".md", ".rst", ".txt")


def tree(repo: str, ref: str, path: str) -> tuple[str, str] | None:
    """The (mode, object) `path` names at `ref`, or None where it is absent
    there. Read from its parent tree's entry, so an absence and a failed git
    call (which exits) are not the same empty answer."""
    for entry in git(Path(repo), "ls-tree", "-z", "--full-tree", ref, "--", path).split(
        "\0"
    ):
        meta, _, name = entry.partition("\t")
        if name == path:
            mode, _, oid = meta.split()
            return mode, oid
    return None


def changed_files(repo: str, a: str, b: str, path: str) -> list[str]:
    # --no-renames: both sides of a move. Listed as a rename, tifxyz.py moved to
    # tifxyz_old.py showed only the new name, which nothing imports, and read
    # RENDER-INERT while render_ink.py's import of it broke. It also keeps the
    # listing to the trees, which a partial clone has.
    out = git(Path(repo), "diff", "--no-renames", "--name-only", "-z", a, b, "--", path)
    return [f for f in out.split("\0") if f]


def import_name(path: str) -> str | None:
    """The top-level name an import uses for `path`, or None outside the roots:
    spiral-fitting/tifxyz/__init__.py is `tifxyz`, as spiral-fitting/tifxyz.py is."""
    for root in IMPORT_ROOTS:
        if path.startswith(root):
            return PurePosixPath(path[len(root) :]).parts[0].removesuffix(".py")
    return None


def imports_of(repo: str, ref: str, path: str) -> set[str]:
    """Module names imported by a file, top-level only."""
    src = git(Path(repo), "show", f"{ref}:{path}")
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
    if not Path(args.repo).exists():
        print(f"no villa checkout at {args.repo}", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(errors="backslashreplace")  # a name that is not UTF-8
    refusal = not_own_repository(Path(args.repo))
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    # Resolved once and used throughout: a fetch mid-run (the upstream monitor
    # fetches this checkout) would otherwise move origin/main between calls.
    a, b = (
        git(Path(args.repo), "rev-parse", "--verify", f"{r}^{{commit}}").strip()
        for r in (a, b)
    )
    sa, sb = (git(Path(args.repo), "rev-parse", "--short=9", r).strip() for r in (a, b))
    # A path at neither ref would compare as unchanged.
    absent = [
        p
        for p in EXTRACTED + ENTRY_POINTS
        if tree(args.repo, a, p) is None and tree(args.repo, b, p) is None
    ]
    if absent:
        print(
            f"{', '.join(absent)}: at neither ref, so not comparable", file=sys.stderr
        )
        return 2
    irregular = [
        f
        for f in ENTRY_POINTS
        for r in (a, b)
        if (entry := tree(args.repo, r, f)) and entry[0] not in REGULAR_FILE_MODES
    ]
    if irregular:
        print(
            f"{', '.join(sorted(set(irregular)))}: not a regular file, so not traced",
            file=sys.stderr,
        )
        return 2
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
    # By stem, as before, or by the name an import resolves to, so a package
    # counts as well as a module: its __init__.py has the stem __init__.
    suspects = [
        f for f in non_test if Path(f).stem in imported or import_name(f) in imported
    ]
    # A change inside a pipeline stage, or a library one imports, counts whether
    # or not anything the entry points import uses it.
    stage_hits = [
        f
        for f in non_test
        if any(f.startswith(s + "/") for s in STAGE_PATHS + STAGE_LIBRARIES)
        and not f.endswith(DOC_SUFFIXES)
    ]
    for f in stage_hits:
        if f not in suspects:
            suspects.append(f)

    print(
        f"changed files in the differing paths: {len(changed)} "
        f"({len(non_test)} excluding tests)"
    )
    print(
        f"of those, imported by an entry point, or in a pipeline stage or a library "
        f"it imports: "
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
