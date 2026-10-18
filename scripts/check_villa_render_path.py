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
executable under those trees is in scope; this script diffs them by blob hash and
file mode between two refs and exits 1 if any differ, so it can gate a pin bump.
It exits 2 when it cannot compare them (a missing checkout or ref).

Usage:
    check_villa_render_path.py                      # old corpus's render source vs submodule HEAD
    check_villa_render_path.py 5479453a 908aa7f06
    check_villa_render_path.py --repo path/to/villa OLD NEW
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# What setup_workdir.sh extracts. Everything a render can execute lives here.
EXTRACTED_TREES = ("spiral-fitting", "lasagna", "vesuvius/src")

# Files known to be on the hot path, called out by name so a change to one of
# them is reported first rather than buried in a long list.
# THE SAMPLER IS NOT IN THE EXTRACTED TREES. vc_render_tifxyz, which reads the
# voxels, is compiled into the vc-render:local image from the Dockerfile's own
# ARG VILLA_SHA -- a second, independent pin (reports/the_render_has_a_second_pin.md).
# Changes under these paths do NOT reach a render until the image is rebuilt, and
# an image rebuild changes the sampler without moving VILLA_REF at all. So this
# check reports them SEPARATELY, as "image path", rather than folding them into
# HOT_PATH where they would look like something a VILLA_REF bump could fix.
IMAGE_PATH_PREFIXES = (
    "volume-cartographer/apps/src/vc_render_tifxyz",
    "volume-cartographer/apps/src/vc_tifxyz",
    "volume-cartographer/core/",
    "volume-cartographer/utils/",
)

HOT_PATH = (
    "spiral-fitting/render_ink.py",
    "spiral-fitting/get_ink_metrics.py",
    "spiral-fitting/tifxyz.py",
    "lasagna/fit.py",
)

# villa-spiral's origin/main, which the pinned-tier corpus's renders were
# extracted from (tests/test_villa_spiral_refs_pinned.py). Since 2026-09-19
# setup_workdir.sh extracts from this repo's submodule, at VILLA_REF, so this
# default asks how far the submodule's HEAD has moved from that render source.
RENDER_SOURCE_REF = "5479453a"


# Inherited, these make git ignore -C (a hook's GIT_DIR and friends) or read
# a pathspec differently, so every call below would answer something else.
_GIT_ENV_DROPPED = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_PREFIX",
    "GIT_GLOB_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
    "GIT_LITERAL_PATHSPECS",
)


def git(repo: Path, *args: str) -> str:
    # surrogateescape: a name that is not UTF-8 comes through -z unquoted.
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        errors="surrogateescape",
        env={k: v for k, v in os.environ.items() if k not in _GIT_ENV_DROPPED},
    )
    if out.returncode != 0:
        print(f"git {' '.join(args)} failed: {out.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return out.stdout


def not_own_repository(repo: Path) -> str | None:
    """Why `repo` is not a repository of its own, or None. In an empty
    directory (an uninitialised submodule) git answers for the repository
    around it, whose refs and trees the gate would then compare."""
    bare = git(repo, "rev-parse", "--is-bare-repository").strip() == "true"
    where = git(repo, "rev-parse", "--absolute-git-dir" if bare else "--show-toplevel")
    if Path(where.strip()).samefile(repo):
        return None
    return f"{repo} is not a repository of its own: git answers for {where.strip()}"


def is_tree(repo: Path, ref: str, tree: str) -> bool:
    """Whether `tree` is a directory at `ref`, from its parent tree's entry."""
    for entry in git(repo, "ls-tree", "-z", "--full-tree", ref, "--", tree).split("\0"):
        meta, _, path = entry.partition("\t")
        if path == tree and meta.split()[1:2] == ["tree"]:
            return True
    return False


def blobs(repo: Path, ref: str, tree: str) -> dict[str, tuple[str, str]]:
    """path -> (mode, blob hash) for every file under `tree` at `ref`, none if
    `tree` is absent there: a removed tree is a difference, not an error. The
    mode is whether a file is executable or a link, which the hash leaves out."""
    listing = git(repo, "ls-tree", "-r", "-z", "--full-tree", ref, "--", tree)
    found = {}
    for entry in listing.split("\0"):
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) >= 3 and parts[1] == "blob":
            found[path] = (parts[0], parts[2])
    return found


# Documentation cannot change a render. Counting it as a render-path difference
# makes the gate cry wolf, and a gate that cries wolf gets ignored -- which is
# how the 908aa7f06 case it exists for would slip through. Found 2026-09-07 when
# our own merged docs PR (#1721, autoresearch.md) flipped the verdict to DIFFERS.
DOC_SUFFIXES = (".md", ".txt", ".rst", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")


def is_docs(path: str) -> bool:
    return path.lower().endswith(DOC_SUFFIXES)


def image_path_changes(repo: Path, old: str, new: str) -> list[str]:
    """Files on the sampler's build path that changed between two refs. Without
    --no-renames a file moved out of the path is listed only where it went, and
    -z keeps the names git would otherwise quote or split on a space."""
    out = git(
        repo,
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        old,
        new,
        "--",
        "volume-cartographer",
    )
    return [p for p in out.split("\0") if p.startswith(IMAGE_PATH_PREFIXES)]


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
        print(f"no villa checkout at {repo}", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(errors="backslashreplace")  # a name that is not UTF-8
    refusal = not_own_repository(repo)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2

    changed, added, removed = compare(repo, args.old, args.new)
    # A tree at one ref only is a difference whichever ref it is at (added
    # files alone do not set the verdict); at neither, the refs are not the
    # render path this gate knows.
    present = {
        tree: (is_tree(repo, args.old, tree), is_tree(repo, args.new, tree))
        for tree in EXTRACTED_TREES
    }
    absent = [tree for tree, at in present.items() if not any(at)]
    if absent:
        print(
            f"{', '.join(absent)}: at neither ref, so not comparable", file=sys.stderr
        )
        return 2
    moved = [tree for tree, (before, after) in present.items() if before != after]
    print(f"villa render path: {args.old} -> {args.new}")
    print(f"  trees compared: {', '.join(EXTRACTED_TREES)}")
    for tree in moved:
        print(f"\n  TREE {'ADDED' if present[tree][1] else 'REMOVED'}: {tree}")

    hot = [p for p in changed if p in HOT_PATH]
    other = [p for p in changed if p not in HOT_PATH and not is_docs(p)]
    docs = [p for p in changed if is_docs(p)]

    # The image path is outside EXTRACTED_TREES, so `changed` never contains it;
    # ask git directly for the same revision range.
    image_changed = image_path_changes(repo, args.old, args.new)
    if image_changed:
        print(
            f"\n  IMAGE PATH CHANGED ({len(image_changed)}) -- the vc_render_tifxyz sampler:"
        )
        for p in image_changed[:12]:
            print(f"    {p}")
        print("    these reach a render ONLY via a docker image rebuild, and a rebuild")
        print("    changes the sampler under every study without moving VILLA_REF.")
        print(
            "    Compare RENDER_IMAGE files, not VILLA_SHA, to know which sampler ran."
        )

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
    if docs:
        print(f"\n  documentation changed ({len(docs)}), does NOT affect the render:")
        for d in docs[:10]:
            print(f"    {d}")
    if removed:
        print(f"\n  REMOVED ({len(removed)}):")
        for p in removed[:20]:
            print(f"    {p}")
    if added:
        print(f"\n  added ({len(added)}): {len(added)} file(s)")

    # Docs are excluded from the verdict but still printed above: a markdown or
    # image change cannot alter a render, and letting it flip the verdict trains
    # the reader to ignore this gate.
    if hot or other or removed or moved:
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
