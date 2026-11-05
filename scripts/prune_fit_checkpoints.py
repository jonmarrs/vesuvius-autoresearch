"""Reclaim fit checkpoints unreferenced by the checked repository artifacts.

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
mentioned**, rather than leaving that to the operator's memory. HEAD, the index
and current nonignored files are checked; errors never count as no match.
Dry-run is the default. See docs/CHECKPOINT_PRUNING.md for scope and limits.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.checkpoint_cleanup import (
    CKPT,
    discover_checkpoints as _discover,
    require_unchanged as _unchanged,
)

SEARCH_SUBDIRS = ("reports", "docs", "scripts", "repro", "tests")
SEARCH_PATHS = (*SEARCH_SUBDIRS, ":(top,glob)*.md", "config.json")
_GIT_SCOPE_OVERRIDES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_PREFIX",
    "GIT_LITERAL_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
)


def _git_env():
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in _GIT_SCOPE_OVERRIDES
    }
    env.update(GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    return env


def _git(repo, *args):
    try:
        return subprocess.run(
            ["git", "--no-pager", "-C", str(repo), "-c", "core.fsmonitor=false", *args],
            env=_git_env(),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            "reference command timed out; reference state is unknown"
        ) from exc


def _repository(repo, expected_head=None):
    repo = Path(repo).resolve()
    top = _git(repo, "rev-parse", "--show-toplevel")
    if (
        top.returncode != 0
        or top.stderr.strip()
        or Path(top.stdout.rstrip("\n")).resolve() != repo
    ):
        raise ValueError("--repo must be the root of an accessible Git worktree")
    result = _git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    head = result.stdout.strip()
    if (
        result.returncode != 0
        or result.stderr.strip()
        or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head)
    ):
        raise ValueError("cannot identify committed reference state")
    if expected_head is not None and head != expected_head:
        raise ValueError(
            "repository HEAD changed; rerun the plan with stable references"
        )
    return repo, head


def is_referenced(repo, arm_dir, *, expected_head=None):
    """Check HEAD, index and current nonignored files; search failure is not absence."""
    if (
        not isinstance(arm_dir, str)
        or not arm_dir
        or not arm_dir.isprintable()
        or Path(arm_dir).name != arm_dir
    ):
        raise ValueError("arm must be a nonempty printable directory basename")
    repo, head = _repository(repo, expected_head)
    needles = [arm_dir]
    if "-patch_" in arm_dir:
        tag = arm_dir.split("-patch_", 1)[1]
        if tag and tag != arm_dir:
            needles.append(tag)
    for needle in needles:
        for selection in ([head], ["--cached"], ["--untracked", "--exclude-standard"]):
            result = _git(
                repo,
                "grep",
                "-l",
                "-F",
                "--no-textconv",
                "--no-recurse-submodules",
                "-e",
                needle,
                *selection,
                "--",
                *SEARCH_PATHS,
            )
            if result.stderr.strip() or result.returncode not in (0, 1):
                detail = " ".join(result.stderr.split())[:300]
                raise ValueError(
                    f"reference search failed (exit {result.returncode}): "
                    f"{detail or 'unavailable result'}; reference state is unknown"
                )
            if result.returncode == 0:
                if not result.stdout.strip():
                    raise ValueError(
                        "reference search returned no matches with success status"
                    )
                return True, needle
            if result.stdout.strip():
                raise ValueError(
                    "reference search returned inconsistent no-match output"
                )
    return False, None


def find_checkpoints(spiral_out):
    """Compatibility inventory of direct, regular, nonsymlink checkpoints only."""
    _, rows = _discover(spiral_out)
    return [(row["arm"], row["path"], row["bytes"]) for row in rows]


def _render(report, as_json):
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(f"Reference commit: {report['reference_commit'] or 'unavailable'}")
    for row in report["checkpoints"]:
        suffix = f" (matched {row['matched']!r})" if row["referenced"] else ""
        print(f"  {row['action']}: {row['arm']} ({row['bytes']} bytes){suffix}")
    if report["mode"] == "dry_run":
        print(
            "DRY RUN. Nothing deleted. Re-run with --delete for a fresh checked plan."
        )
    else:
        print(
            f"deleted {report['deleted_count']} checkpoint(s), {report['deleted_bytes']} logical bytes"
        )
    for error in report["errors"]:
        print(f"Pruning refused: {error}", file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spiral-out", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument(
        "--delete",
        action="store_true",
        help="remove only checked, unreferenced checkpoints",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the checked plan or action result as JSON",
    )
    args = parser.parse_args(argv)
    report = {
        "mode": "delete" if args.delete else "dry_run",
        "status": "BLOCKED",
        "repository": args.repo,
        "spiral_out": args.spiral_out,
        "reference_commit": None,
        "reference_scope": list(SEARCH_PATHS),
        "discovery_scope": "direct nonsymlink arm directories; regular checkpoint files",
        "checkpoints": [],
        "deleted_count": 0,
        "deleted_bytes": 0,
        "errors": [],
    }
    try:
        repo, head = _repository(args.repo)
        report["repository"], report["reference_commit"] = str(repo), head
        root, rows = _discover(args.spiral_out)
        for row in rows:
            row.update(referenced=False, matched=None, action="WOULD_DELETE")
        report["spiral_out"], report["checkpoints"] = str(root), rows
        for row in rows:
            ref, needle = is_referenced(repo, row["arm"], expected_head=head)
            row.update(
                referenced=ref, matched=needle, action="KEEP" if ref else "WOULD_DELETE"
            )
        _repository(repo, head)
        candidates = [row for row in rows if not row["referenced"]]
        if args.delete:
            # Preflight the whole deletion set before removing its first file.
            for row in candidates:
                _unchanged(row)
                ref, _ = is_referenced(repo, row["arm"], expected_head=head)
                if ref:
                    raise ValueError("a checkpoint gained a reference; rerun the plan")
            _repository(repo, head)
            for row in candidates:
                _unchanged(row)
                os.remove(row["path"])
                row["action"] = "DELETED"
                report["deleted_count"] += 1
                report["deleted_bytes"] += row["bytes"]
        report["status"] = "COMPLETE"
    except (OSError, ValueError, RuntimeError) as exc:
        report["errors"].append(str(exc))
        report["status"] = "PARTIAL" if report["deleted_count"] else "BLOCKED"
        for row in report["checkpoints"]:
            if row["action"] == "WOULD_DELETE":
                row["action"] = "REFUSED"
    _render(report, args.json)
    return int(report["status"] != "COMPLETE")


if __name__ == "__main__":
    raise SystemExit(main())
