#!/usr/bin/env python3
"""
Summarize prize-relevant changes available in the upstream ScrollPrize/villa repo.

This intentionally reads only git metadata from the local villa submodule. Run
`git -C villa fetch origin main` first when network is available. It refuses a
villa directory that is not a repository of its own: git run in an uninitialised
submodule answers for the enclosing repository.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PRIZE_AREAS = {
    "lasagna": {
        "prefixes": ("lasagna/",),
        "prize_use": "Surface fitting, tifxyz conversion, and 3D training for better Scroll 2/3 unwrapping.",
    },
    # villa #1486 (af8bac80e, 2026-08-17) deprecated the standalone ink-detection
    # pipeline in favour of vesuvius/src/vesuvius/ink_detection/: its inference_*.py
    # and train_resnet3d_3d_decoder.py moved to deprecated/ and are no longer
    # tracked. No area tracks the replacement (docs/DESIGN_ARCHITECTURE_REVIEW_
    # 2026-10-18_VILLA_UPSTREAM_AUDIT.md); stale_prefixes reports any prefix that
    # stops matching.
    "optimized_inference": {
        "prefixes": ("ink-detection/optimized_inference/",),
        "prize_use": "Official Docker/runtime contract for reproducible ink prediction submissions.",
    },
    "resnet3d_decoder": {
        "prefixes": ("ink-detection/optimized_inference/model_resnet3d_3d_decoder.py",),
        "prize_use": "Tracked 3D decoder baseline for thicker-layer context and stronger cross-scroll generalization.",
    },
    "volume_cartographer": {
        "prefixes": ("volume-cartographer/",),
        "prize_use": "VC3D segmentation, browsing, growth, and tifxyz utilities for producing reviewable surfaces.",
    },
    "vesuvius_data": {
        "prefixes": (
            "vesuvius/src/vesuvius/data/",
            "vesuvius/src/vesuvius/scripts/build_chunk_occupancy.py",
        ),
        "prize_use": "Chunk occupancy and volume access improvements that reduce empty-window search waste.",
    },
    "prize_docs": {
        "prefixes": ("scrollprize.org/docs/34_prizes.md",),
        "prize_use": "Current prize rules, deadlines, and submission criteria.",
    },
}


# Git exports these to hooks (GIT_DIR from a linked worktree), and with one set
# every call reads that repository instead; as scripts/audit_doc_references.py.
_GIT_LOCATORS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_PREFIX",
)


def _git_env():
    return {k: v for k, v in os.environ.items() if k not in _GIT_LOCATORS}


def _git(args, cwd):
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, env=_git_env()
    ).strip()


def _check_own_repository(villa_dir):
    """Raise unless villa_dir is the top of a repository of its own.

    An uninitialised submodule is an empty directory, and git run there answers
    for the enclosing repository: the audit reported this repository's HEAD as
    both villa's local and upstream ref, and villa as up to date."""
    top = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=villa_dir,
        capture_output=True,
        text=True,
        env=_git_env(),
    )
    found = top.stdout.strip()
    if top.returncode:
        reason = top.stderr.strip().splitlines()[-1] if top.stderr.strip() else ""
        raise RuntimeError(f"{villa_dir} is not a git checkout: {reason}")
    if Path(found).resolve() == villa_dir.resolve():
        return
    if "/.git/" in f"{found}/":
        # A linked villa worktree whose core.worktree is villa's git directory.
        advice = "a dev worktree made before #119: run scripts/dev_worktree.sh repair <branch>"
    else:
        advice = (
            "an uninitialised submodule: in a clone run `git submodule update --init "
            "villa`; make a dev worktree with scripts/dev_worktree.sh add"
        )
    raise RuntimeError(
        f"{villa_dir} is not a villa checkout of its own (git answers for {found}); {advice}"
    )


def _changed_paths(villa_dir, base_ref, head_ref):
    # --no-renames: with rename detection a moved file is listed only at its new
    # path, so a move out of an area went uncounted; and finding inexact renames
    # reads blobs, which a blob:none clone (villa's) fetches over the network.
    out = _git(
        ["diff", "--no-renames", "--name-only", f"{base_ref}..{head_ref}"],
        cwd=villa_dir,
    )
    return [line for line in out.splitlines() if line]


def _count_commits(villa_dir, base_ref, head_ref):
    out = _git(["rev-list", "--count", f"{base_ref}..{head_ref}"], cwd=villa_dir)
    return int(out or 0)


def _tree_paths(villa_dir, ref):
    """Every file path in ref's tree (trees only: no blob is read)."""
    out = _git(["ls-tree", "-r", "--name-only", ref], cwd=villa_dir)
    return [line for line in out.splitlines() if line]


def _stale_prefixes(paths):
    """The prefixes that match no path: a file or directory villa moved."""
    return sorted(
        prefix
        for spec in PRIZE_AREAS.values()
        for prefix in spec["prefixes"]
        if not any(_matches(path, prefix) for path in paths)
    )


def _matches(path, prefix):
    return path == prefix.rstrip("/") or path.startswith(prefix)


def _group_paths_by_area(paths):
    areas = {}
    for name, spec in PRIZE_AREAS.items():
        matches = [
            path
            for path in paths
            if any(_matches(path, prefix) for prefix in spec["prefixes"])
        ]
        areas[name] = {
            "changed_files": len(matches),
            "sample_paths": matches[:12],
            "prize_use": spec["prize_use"],
        }
    return areas


def audit_villa_upstream(villa_dir="villa", head_ref="origin/main"):
    villa_dir = Path(villa_dir)
    if not villa_dir.is_absolute():
        villa_dir = REPO_ROOT / villa_dir
    if not villa_dir.exists():
        raise FileNotFoundError(f"villa submodule not found: {villa_dir}")
    _check_own_repository(villa_dir)

    local_ref = _git(["rev-parse", "HEAD"], cwd=villa_dir)
    upstream_ref = _git(["rev-parse", head_ref], cwd=villa_dir)
    merge_base = _git(["merge-base", local_ref, head_ref], cwd=villa_dir)
    upstream_changed = _changed_paths(villa_dir, merge_base, head_ref)
    local_changed = _changed_paths(villa_dir, merge_base, local_ref)

    upstream_ahead_commits = _count_commits(villa_dir, merge_base, head_ref)
    local_ahead_commits = _count_commits(villa_dir, merge_base, local_ref)
    direct_changed = _changed_paths(villa_dir, local_ref, head_ref)

    commits = _git(
        ["log", "--oneline", "--max-count=20", f"{local_ref}..{head_ref}"],
        cwd=villa_dir,
    )
    return {
        "villa_dir": str(villa_dir),
        "local_ref": local_ref,
        "upstream_ref": upstream_ref,
        "merge_base": merge_base,
        "behind": upstream_ahead_commits > 0,
        "diverged": upstream_ahead_commits > 0 and local_ahead_commits > 0,
        "upstream_ahead_commits": upstream_ahead_commits,
        "local_ahead_commits": local_ahead_commits,
        "changed_files": len(upstream_changed),
        "direct_tree_changed_files": len(direct_changed),
        "local_changed_files": len(local_changed),
        "prize_relevant_areas": _group_paths_by_area(upstream_changed),
        "local_prize_relevant_areas": _group_paths_by_area(local_changed),
        "recent_upstream_commits": [line for line in commits.splitlines() if line],
        # Prefixes that match nothing in each tree: the files moved, so their
        # area counts nothing until PRIZE_AREAS is updated.
        "stale_prefixes": {
            "local": _stale_prefixes(_tree_paths(villa_dir, local_ref)),
            "upstream": _stale_prefixes(_tree_paths(villa_dir, upstream_ref)),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--villa-dir", default="villa")
    parser.add_argument("--head-ref", default="origin/main")
    parser.add_argument("--out", default="reports/villa_upstream_audit.json")
    args = parser.parse_args()

    report = audit_villa_upstream(args.villa_dir, args.head_ref)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
