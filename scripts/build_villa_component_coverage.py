#!/usr/bin/env python3
"""
Report how official ScrollPrize/villa components map into Autoresearch.

The goal is to keep prize work grounded in the official monorepo surface: data
access, ink inference, unwrapping, review tools, and validation paths.
"""
import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


COMPONENTS = [
    {
        "name": "vesuvius",
        "official_path": "villa/vesuvius",
        "prize_use": "Official Python CT/Zarr data access and normalization.",
        "local_hooks": ["vesuvius_loader.py", "v3_training/trainer.py", "check_loader.py"],
        "next_action": "Keep loader smoke tests aligned with the pinned Villa data API.",
        "priority": "high",
    },
    {
        "name": "vesuvius-c",
        "official_path": "villa/vesuvius-c",
        "prize_use": "Low-level CT access for high-throughput chunk reads.",
        "local_hooks": ["vesuvius_c_wrapper", "benchmark_vesuvius_c.py", "test_vesuvius_c.py", "SPRINT_KANBAN.md"],
        "required_hooks": ["vesuvius_c_wrapper"],
        "next_action": "Run the Vesuvius-C benchmark on local CT chunks before claiming a Progress Prize speedup.",
        "priority": "medium",
    },
    {
        "name": "ink-detection",
        "official_path": "villa/ink-detection",
        "prize_use": "Official Grand Prize ink model recipes and optimized inference contracts.",
        "local_hooks": ["train.py", "predict.py", "scripts/smoke_test_villa_optimized_inference.py"],
        "next_action": "Keep optimized-inference smoke checks in the post-sprint gate before packaging evidence.",
        "priority": "high",
    },
    {
        "name": "crackle-viewer",
        "official_path": "villa/crackle-viewer",
        "prize_use": "Human review and labeling of virtually unwrapped ink predictions.",
        "local_hooks": ["scripts/launch_crackle_viewer.py", "reports/villa_review_manifest.md"],
        "next_action": "Open GPU-ready candidates from the review manifest for human text-legibility review.",
        "priority": "high",
    },
    {
        "name": "volume-cartographer",
        "official_path": "villa/volume-cartographer",
        "prize_use": "VC3D surface tracing, segmentation, and overlay review.",
        "local_hooks": ["scripts/launch_vc3d.py", "scripts/validate_prize_artifact.py", "reports/villa_review_manifest.md"],
        "next_action": "Validate ink/fiber OME-Zarr overlays before VC3D review or Progress Prize packaging.",
        "priority": "high",
    },
    {
        "name": "lasagna",
        "official_path": "villa/lasagna",
        "prize_use": "Surface fitting, tifxyz conversion, and geometry-aware preprocessing.",
        "local_hooks": ["scripts/build_lasagna_fiber_worklist.py", "reports/lasagna_fiber_worklist.tsv"],
        "next_action": "Route occupied Scroll 2/3 candidates through Lasagna/fiber preprocessing before more ink inference.",
        "priority": "high",
    },
    {
        "name": "segmentation",
        "official_path": "villa/segmentation",
        "prize_use": "Official segmentation models and topology-oriented evaluation metrics.",
        "local_hooks": ["test_import.py", "submission_package_dry_run/HALLUCINATION_MITIGATION.md"],
        "next_action": "Keep topology metrics available as hallucination mitigation evidence.",
        "priority": "medium",
    },
    {
        "name": "foundation",
        "official_path": "villa/foundation",
        "prize_use": "Dataset management and fiber-label assets.",
        "local_hooks": ["generate_fiber_labels.py"],
        "next_action": "Use fiber assets to expand supervision for hard geometry candidates.",
        "priority": "medium",
    },
    {
        "name": "thaumato-anakalyptor",
        "official_path": "villa/thaumato-anakalyptor",
        "prize_use": "Alternative semi-automatic unwrapping and surface extraction pipeline.",
        "local_hooks": ["scripts/launch_thaumato.py", "scripts/autoresearch_thaumato_solver.py"],
        "next_action": "Use as a fallback review route when VC3D/Lasagna surfaces are poor.",
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


def build_component_coverage(components=None):
    rows = []
    for component in components or COMPONENTS:
        official_present = _path_exists(component["official_path"])
        hook_status = [
            {"path": hook, "present": _path_exists(hook)}
            for hook in component["local_hooks"]
        ]
        required_hooks = component.get("required_hooks", [])
        missing_required_hooks = [
            hook
            for hook in required_hooks
            if not _path_exists(hook)
        ]
        present_hooks = sum(1 for hook in hook_status if hook["present"])
        if official_present and present_hooks == len(hook_status) and not missing_required_hooks:
            status = "covered"
        elif official_present and missing_required_hooks and present_hooks:
            status = "blocked_missing_required_hook"
        elif official_present and present_hooks:
            status = "partial"
        elif official_present:
            status = "unwired"
        else:
            status = "missing_official_component"
        rows.append(
            {
                **component,
                "official_present": official_present,
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
            1 for row in rows if row["coverage_status"] == "blocked_missing_required_hook"
        ),
        "unwired": sum(1 for row in rows if row["coverage_status"] == "unwired"),
        "missing_official_component": sum(1 for row in rows if row["coverage_status"] == "missing_official_component"),
    }
    return {"source": "ScrollPrize/villa local checkout", "summary": summary, "components": rows}


def render_markdown(report):
    summary = report["summary"]
    lines = [
        "# Villa Component Coverage",
        "",
        "This report maps official `ScrollPrize/villa` components to local Autoresearch hooks.",
        "",
        "## Summary",
        "",
        f"- Total components: `{summary['total_components']}`",
        f"- Covered: `{summary['covered']}`",
        f"- Partial: `{summary['partial']}`",
        f"- Blocked by missing required hook: `{summary['blocked_missing_required_hook']}`",
        f"- Unwired: `{summary['unwired']}`",
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
