#!/usr/bin/env python3
"""
Summarize prize-relevant changes available in the upstream ScrollPrize/villa repo.

This intentionally reads only git metadata from the local villa submodule. Run
`git -C villa fetch origin main` first when network is available.
"""

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PRIZE_AREAS = {
    "lasagna": {
        "prefixes": ("lasagna/",),
        "prize_use": "Surface fitting, tifxyz conversion, and 3D training for better Scroll 2/3 unwrapping.",
    },
    "optimized_inference": {
        "prefixes": ("ink-detection/optimized_inference/", "ink-detection/inference_"),
        "prize_use": "Official Docker/runtime contract for reproducible ink prediction submissions.",
    },
    "resnet3d_decoder": {
        "prefixes": (
            "ink-detection/train_resnet3d_3d_decoder.py",
            "ink-detection/optimized_inference/model_resnet3d_3d_decoder.py",
        ),
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


def _git(args, cwd):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def _changed_paths(villa_dir, base_ref, head_ref):
    out = _git(["diff", "--name-only", f"{base_ref}..{head_ref}"], cwd=villa_dir)
    return [line for line in out.splitlines() if line]


def _count_commits(villa_dir, base_ref, head_ref):
    out = _git(["rev-list", "--count", f"{base_ref}..{head_ref}"], cwd=villa_dir)
    return int(out or 0)


def _group_paths_by_area(paths):
    areas = {}
    for name, spec in PRIZE_AREAS.items():
        matches = [
            path
            for path in paths
            if any(
                path == prefix.rstrip("/") or path.startswith(prefix)
                for prefix in spec["prefixes"]
            )
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
