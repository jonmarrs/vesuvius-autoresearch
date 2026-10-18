#!/usr/bin/env python3
"""
Report how official ScrollPrize/villa components map into Autoresearch.

The goal is to keep prize work grounded in the official monorepo surface: data
access, ink inference, unwrapping, review tools, and validation paths.

It checks paths only: a hook that exists is not shown to run. Official paths are
read from the git tree of the villa commit this repository pins, so a sparse checkout
answers as the pin does; whether each path is also checked out is recorded beside it.
When the pin's tree cannot be read, the working tree answers and the report says why.
A component villa has moved under deprecated/ is reported as such.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


COMPONENTS = [
    {
        "name": "vesuvius",
        "official_path": "villa/vesuvius",
        "prize_use": "Official Python CT/Zarr data access and normalization.",
        "local_hooks": [
            "src/vesuvius_autoresearch/core/vesuvius_loader.py",
            "v3_training/trainer.py",
        ],
        "next_action": "Keep loader smoke tests aligned with the pinned Villa data API.",
        "priority": "high",
    },
    {
        "name": "ink-detection",
        "official_path": "villa/ink-detection",
        "prize_use": "Official Grand Prize ink model recipes and optimized inference contracts.",
        "local_hooks": [
            "scripts/training/train.py",
            "scripts/inference/predict.py",
            "scripts/smoke_test_villa_optimized_inference.py",
        ],
        "next_action": "Keep optimized-inference smoke checks in the post-sprint gate before packaging evidence.",
        "priority": "high",
    },
    {
        "name": "crackle-viewer",
        "official_path": "villa/crackle-viewer",
        "prize_use": "Human review and labeling of virtually unwrapped ink predictions.",
        "local_hooks": [
            "scripts/launch_crackle_viewer.py",
            "reports/villa_review_manifest.md",
        ],
        "next_action": "Open GPU-ready candidates from the review manifest for human text-legibility review.",
        "priority": "high",
    },
    {
        "name": "volume-cartographer",
        "official_path": "villa/volume-cartographer",
        "prize_use": "Maintained Villa path for volume/chunk access, VC3D surface tracing, segmentation, and overlay review.",
        "local_hooks": [
            "volume_cartographer_wrapper",
            "scripts/build_volume_cartographer_readiness.py",
            "scripts/launch_vc3d.py",
            "scripts/validate_prize_artifact.py",
            "reports/villa_review_manifest.md",
        ],
        "required_hooks": [
            "volume_cartographer_wrapper",
            "scripts/build_volume_cartographer_readiness.py",
        ],
        "next_action": "Keep Python loading and VC3D overlay validation aligned with Volume Cartographer; do not add new vesuvius-c hooks.",
        "priority": "high",
    },
    {
        "name": "lasagna",
        "official_path": "villa/lasagna",
        "prize_use": "Surface fitting, tifxyz conversion, and geometry-aware preprocessing.",
        "local_hooks": [
            "scripts/build_lasagna_fiber_worklist.py",
            "reports/lasagna_fiber_worklist.tsv",
        ],
        "next_action": "Route occupied Scroll 2/3 candidates through Lasagna/fiber preprocessing before more ink inference.",
        "priority": "high",
    },
    {
        "name": "segmentation",
        "official_path": "villa/segmentation",
        "prize_use": "Official segmentation models and topology-oriented evaluation metrics.",
        "local_hooks": [
            "tests/test_import.py",
            "submission_package_dry_run/HALLUCINATION_MITIGATION.md",
        ],
        "next_action": "Keep topology metrics available as hallucination mitigation evidence.",
        "priority": "medium",
    },
    {
        "name": "foundation",
        "official_path": "villa/foundation",
        "prize_use": "Dataset management and fiber-label assets.",
        "local_hooks": ["scripts/labeling/generate_fiber_labels.py"],
        "next_action": "Use fiber assets to expand supervision for hard geometry candidates.",
        "priority": "medium",
    },
    {
        "name": "thaumato-anakalyptor",
        "official_path": "villa/thaumato-anakalyptor",
        "prize_use": "Alternative semi-automatic unwrapping and surface extraction pipeline.",
        "local_hooks": [
            "scripts/launch_thaumato.py",
            "scripts/autoresearch_thaumato_solver.py",
        ],
        "next_action": "Retired here: the legacy Thaumato solver sweep (docs/SHEET_GRAPH_DIAGNOSTICS.md); upstream moved the tool to deprecated/.",
        "priority": "medium",
    },
]


def _resolve(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _path_exists(path):
    return _resolve(path).exists()


# Git exports these to hooks (GIT_DIR from a linked worktree), and with one set every
# call ignores -C and reads another repository; as scripts/audit_doc_references.py.
_GIT_LOCATORS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_PREFIX",
)


def _git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_LOCATORS}
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env
    )


def _villa_pin():
    """(commit, None) when the pinned villa commit's tree can be read, else
    (None, why not) and the working tree answers instead."""
    villa = _resolve("villa")
    if not (villa / ".git").exists():
        return None, "villa is not a git checkout"
    try:
        top = _git(villa, "rev-parse", "--show-toplevel")
        root = _git(REPO_ROOT, "rev-parse", "--show-toplevel")
        gitlink = _git(REPO_ROOT, "ls-tree", "HEAD", "villa")
    except FileNotFoundError:
        return None, "git is not installed"

    def opens(found, path):
        # An empty or broken .git sends git up to an enclosing repository instead.
        return (
            not found.returncode
            and Path(found.stdout.strip()).resolve() == path.resolve()
        )

    if not opens(top, villa):
        return None, "villa/.git does not open villa's own repository"
    if not opens(root, REPO_ROOT):
        return None, "this repository is not a git checkout"
    fields = gitlink.stdout.split()
    if gitlink.returncode or len(fields) < 3 or fields[1] != "commit":
        return None, "this repository's HEAD records no villa pin"
    pin = fields[2]
    if _git(villa, "rev-parse", "--verify", "-q", f"{pin}^{{tree}}").returncode:
        return None, f"the pinned commit {pin[:9]} is not in villa's object store"
    return pin, None


def _official_present(path, pin):
    """Whether the pinned villa holds path: the pin's tree when it can be read (a
    sparse checkout omits directories the pin has), else the working tree."""
    parts = Path(path).parts
    if pin and len(parts) > 1 and parts[0] == "villa":
        # rev-parse, not cat-file -e: in a blob:none clone cat-file fetches a blob.
        inner = "/".join(parts[1:])
        found = _git(_resolve("villa"), "rev-parse", "--verify", "-q", f"{pin}:{inner}")
        return found.returncode == 0
    return _path_exists(path)


def _deprecated_path(path):
    """villa/<name> as villa's deprecated/ tree holds it, or None."""
    parts = Path(path).parts
    if len(parts) == 2 and parts[0] == "villa":
        return f"villa/deprecated/{parts[1]}"
    return None


def build_component_coverage(components=None):
    pin, unread = _villa_pin()
    rows = []
    for component in components or COMPONENTS:
        official_present = _official_present(component["official_path"], pin)
        deprecated = _deprecated_path(component["official_path"])
        deprecated_present = bool(deprecated) and _official_present(deprecated, pin)
        hook_status = [
            {"path": hook, "present": _path_exists(hook)}
            for hook in component["local_hooks"]
        ]
        required_hooks = component.get("required_hooks", [])
        missing_required_hooks = [
            hook for hook in required_hooks if not _path_exists(hook)
        ]
        present_hooks = sum(1 for hook in hook_status if hook["present"])
        if (
            official_present
            and present_hooks == len(hook_status)
            and not missing_required_hooks
        ):
            status = "covered"
        elif official_present and missing_required_hooks and present_hooks:
            status = "blocked_missing_required_hook"
        elif official_present and present_hooks:
            status = "partial"
        elif official_present:
            status = "unwired"
        elif deprecated_present:
            status = "deprecated_upstream"
        else:
            status = "missing_official_component"
        rows.append(
            {
                **component,
                "official_present": official_present,
                "official_checked_out": _path_exists(component["official_path"]),
                "deprecated_path": deprecated if deprecated_present else None,
                "deprecated_checked_out": bool(deprecated_present)
                and _path_exists(deprecated),
                "local_hook_status": hook_status,
                "required_hooks": required_hooks,
                "missing_required_hooks": missing_required_hooks,
                "present_local_hooks": present_hooks,
                "total_local_hooks": len(hook_status),
                "coverage_status": status,
            }
        )
    summary = {
        "total_components": len(rows),
        "covered": sum(1 for row in rows if row["coverage_status"] == "covered"),
        "partial": sum(1 for row in rows if row["coverage_status"] == "partial"),
        "blocked_missing_required_hook": sum(
            1
            for row in rows
            if row["coverage_status"] == "blocked_missing_required_hook"
        ),
        "unwired": sum(1 for row in rows if row["coverage_status"] == "unwired"),
        "deprecated_upstream": sum(
            1 for row in rows if row["coverage_status"] == "deprecated_upstream"
        ),
        "missing_official_component": sum(
            1 for row in rows if row["coverage_status"] == "missing_official_component"
        ),
        "villa_path_not_checked_out": sum(
            1
            for row in rows
            if (row["official_present"] and not row["official_checked_out"])
            or (row["deprecated_path"] and not row["deprecated_checked_out"])
        ),
    }
    return {
        "source": (
            "ScrollPrize/villa at this repository's pin (git tree)"
            if pin
            else f"the villa working tree ({unread})"
        ),
        "villa_commit": pin,
        "pin_unread": unread,
        "summary": summary,
        "components": rows,
    }


def _villa_paths(row):
    """The row's official paths that the source holds, each marked when absent here."""
    held = []
    if row["official_present"]:
        held.append((row["official_path"], row["official_checked_out"]))
    if row["deprecated_path"]:
        held.append((row["deprecated_path"], row["deprecated_checked_out"]))
    return (
        ", ".join(
            f"`{path}`" + ("" if checked_out else " (not checked out)")
            for path, checked_out in held
        )
        or "none"
    )


def render_markdown(report):
    summary = report["summary"]
    if report.get("villa_commit"):
        source = (
            "Official paths are read from the git tree of the villa commit this repository"
            f" pins (`{report['villa_commit'][:9]}`), so a sparse checkout answers as the pin"
            " does. A path marked not checked out is in the pin but not in the villa"
            " working tree this report was generated from, so a tool that reads it there fails."
        )
    else:
        source = (
            "Official paths are read from the villa working tree, not the pin: the pinned"
            f" tree could not be read ({report.get('pin_unread')})."
        )
    lines = [
        "# Villa Component Coverage",
        "",
        "This report maps official `ScrollPrize/villa` components to local Autoresearch hooks.",
        "",
        "It checks paths only: a hook that exists is not shown to run, and nothing here is",
        "scientific validation. " + source,
        "",
        "## Summary",
        "",
        f"- Total components: `{summary['total_components']}`",
        f"- Covered: `{summary['covered']}`",
        f"- Partial: `{summary['partial']}`",
        f"- Blocked by missing required hook: `{summary['blocked_missing_required_hook']}`",
        f"- Unwired: `{summary['unwired']}`",
        f"- Deprecated upstream (moved to `villa/deprecated/`): `{summary['deprecated_upstream']}`",
        f"- Missing official component: `{summary['missing_official_component']}`",
        f"- Components with a villa path not checked out: `{summary['villa_path_not_checked_out']}`",
        "",
        "## Components",
        "",
        "| Component | Status | Priority | Villa path | Prize use | Local hooks | Next action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["components"]:
        hooks = ", ".join(
            f"`{hook['path']}`{' ok' if hook['present'] else ' missing'}"
            for hook in row["local_hook_status"]
        )
        lines.append(
            "| {name} | `{status}` | `{priority}` | {villa} | {prize_use} | {hooks} | {next_action} |".format(
                name=row["name"],
                status=row["coverage_status"],
                priority=row["priority"],
                villa=_villa_paths(row),
                prize_use=row["prize_use"].replace("|", "\\|"),
                hooks=hooks.replace("|", "\\|"),
                next_action=row["next_action"].replace("|", "\\|"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", default="reports/villa_component_coverage.json")
    parser.add_argument("--out-md", default="reports/villa_component_coverage.md")
    args = parser.parse_args()

    report = build_component_coverage()
    out_json = _resolve(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n")

    out_md = _resolve(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(report))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
