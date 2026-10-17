#!/usr/bin/env python3
"""
Report how official ScrollPrize/villa components map into Autoresearch.

The goal is to keep prize work grounded in the official monorepo surface: data
access, ink inference, unwrapping, review tools, and validation paths.

It checks paths only: a hook that exists is not shown to run. Official paths are
read from the pinned villa's own git tree, so a sparse checkout answers as the pin
does; a component villa has moved under deprecated/ is reported as such.
"""

import argparse
import json
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


def _official_present(path):
    """Whether the pinned villa holds path: its HEAD tree when villa is a git
    checkout (a sparse one omits directories the pin has), else the working tree."""
    parts = Path(path).parts
    villa = _resolve("villa")
    if len(parts) > 1 and parts[0] == "villa" and (villa / ".git").exists():
        inner = "/".join(parts[1:])
        found = subprocess.run(
            ["git", "-C", str(villa), "cat-file", "-e", f"HEAD:{inner}"],
            capture_output=True,
        )
        return found.returncode == 0
    return _path_exists(path)


def _villa_commit():
    """The villa commit the official paths were read from, or None."""
    villa = _resolve("villa")
    if not (villa / ".git").exists():
        return None
    head = subprocess.run(
        ["git", "-C", str(villa), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return head.stdout.strip() or None


def _deprecated_path(path):
    """villa/<name> as villa's deprecated/ tree holds it, or None."""
    parts = Path(path).parts
    if len(parts) == 2 and parts[0] == "villa":
        return f"villa/deprecated/{parts[1]}"
    return None


def build_component_coverage(components=None):
    rows = []
    for component in components or COMPONENTS:
        official_present = _official_present(component["official_path"])
        deprecated = _deprecated_path(component["official_path"])
        deprecated_present = (
            not official_present and deprecated and _official_present(deprecated)
        )
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
                "deprecated_path": deprecated if deprecated_present else None,
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
    }
    return {
        "source": "ScrollPrize/villa at its checked-out commit (git tree)",
        "villa_commit": _villa_commit(),
        "summary": summary,
        "components": rows,
    }


def render_markdown(report):
    summary = report["summary"]
    lines = [
        "# Villa Component Coverage",
        "",
        "This report maps official `ScrollPrize/villa` components to local Autoresearch hooks.",
        "",
        "It checks paths only: a hook that exists is not shown to run, and nothing here is",
        "scientific validation. Official paths are read from the pinned villa's git tree"
        + (
            f" (`{report['villa_commit'][:9]}`)." if report.get("villa_commit") else "."
        ),
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
        "",
        "## Components",
        "",
        "| Component | Status | Priority | Prize use | Local hooks | Next action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["components"]:
        hooks = ", ".join(
            f"`{hook['path']}`{' ok' if hook['present'] else ' missing'}"
            for hook in row["local_hook_status"]
        )
        lines.append(
            "| {name} | `{status}` | `{priority}` | {prize_use} | {hooks} | {next_action} |".format(
                name=row["name"],
                status=row["coverage_status"],
                priority=row["priority"],
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
