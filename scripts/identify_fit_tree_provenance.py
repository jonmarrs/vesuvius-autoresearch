"""Which upstream villa commit does each subtree of the fit tree actually match?

`villa-spiral-current/` is the tree every current-code arm was fitted and
rendered from. It is a **copy**, not a checkout: no `.git`, no recorded
provenance, and `git -C` inside it silently resolves to the enclosing workspace
repo and reports an unrelated commit. That is how
`reports/decoupling_does_not_cleanly_reproduce.md` came to state a version for
the renders that was not the one used.

This recovers the provenance by content: for each subtree, walk candidate commits
in the `villa/` submodule and report the ones whose tracked files are
byte-identical to the copy.

The answer is not a single commit. `spiral-fitting` and `lasagna` match
**different** upstream commits, which is a fact about the tree, not a bug -- but
it has to be stated as two refs rather than one.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SUBTREES = ("spiral-fitting", "lasagna", "vesuvius")
SKIP = {".venv", "__pycache__", "build", ".pytest_cache"}


def tracked_files(repo: Path, commit: str, subtree: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", commit, subtree],
        capture_output=True,
        text=True,
        check=False,
    )
    return [f for f in out.stdout.splitlines() if not any(s in f for s in SKIP)]


def blob(repo: Path, commit: str, path: str) -> bytes | None:
    out = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True,
        check=False,
    )
    return out.stdout if out.returncode == 0 else None


def compare(
    repo: Path, tree: Path, commit: str, subtree: str
) -> tuple[int, int, list[str]]:
    """(matching, total, first few differing paths) for tracked files."""
    files = tracked_files(repo, commit, subtree)
    match, diffs = 0, []
    for f in files:
        local = tree / f
        if not local.is_file():
            diffs.append(f + " (absent locally)")
            continue
        b = blob(repo, commit, f)
        if b is not None and b == local.read_bytes():
            match += 1
        else:
            diffs.append(f)
    return match, len(files), diffs[:5]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tree", required=True, help="the copied tree, e.g. villa-spiral-current"
    )
    ap.add_argument(
        "--repo", required=True, help="a villa checkout to search, e.g. ./villa"
    )
    ap.add_argument("--commits", nargs="+", required=True)
    args = ap.parse_args()

    tree, repo = Path(args.tree), Path(args.repo)
    if (tree / ".git").exists():
        print(f"note: {tree} HAS a .git; prefer asking it directly")

    verdict = {}
    for sub in SUBTREES:
        if not (tree / sub).is_dir():
            continue
        print(f"\n=== {sub}")
        best = None
        for c in args.commits:
            m, n, diffs = compare(repo, tree, c, sub)
            if n == 0:
                print(f"  {c}: subtree absent at this commit")
                continue
            star = "  <-- EXACT" if m == n else ""
            print(f"  {c}: {m}/{n} files identical{star}")
            for d in diffs:
                print(f"       differs: {d}")
            if m == n and best is None:
                best = c
        verdict[sub] = best
        print(f"  => {sub} matches {best or 'NONE of the candidates'}")

    print("\n" + "=" * 60)
    exact = {k: v for k, v in verdict.items() if v}
    if len(set(exact.values())) > 1:
        print("THE TREE IS NOT ONE REF. Subtrees match different commits:")
        for k, v in verdict.items():
            print(f"  {k:16} {v or 'unmatched'}")
        print("Any provenance statement must name each subtree separately.")
    elif exact:
        print(f"whole tree matches {next(iter(set(exact.values())))}")
    else:
        print("no candidate commit matched; widen --commits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
