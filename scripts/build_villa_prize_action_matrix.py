#!/usr/bin/env python3
"""
Build an operator-facing action matrix from Villa opportunity and evidence reports.

This turns the official ScrollPrize/villa opportunity ranking plus current
Autoresearch preflight results into a short, repeatable sprint decision artifact.
"""
import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


AREA_ACTIONS = {
    "lasagna": {
        "autopipeline_action": "Route ready Scroll 2/3 windows through Lasagna/fiber preprocessing before the next ink pass.",
        "evidence_gate": "Use GPU-ready preflight candidates with occupied CT chunks.",
        "review_artifact": "reports/lasagna_fiber_worklist.tsv",
    },
    "volume_cartographer": {
        "autopipeline_action": "Export ink and fiber maps as VC3D-compatible OME-Zarr overlays for surface review.",
        "evidence_gate": "Require prediction Zarr metadata and scale metadata to validate cleanly.",
        "review_artifact": "VC3D overlay path in prediction metadata",
    },
    "optimized_inference": {
        "autopipeline_action": "Run the optimized inference smoke contract before packaging evidence.",
        "evidence_gate": "Require reproducible predict command plus non-placeholder image and metadata.",
        "review_artifact": "scripts/smoke_test_villa_optimized_inference.py",
    },
    "resnet3d_decoder": {
        "autopipeline_action": "Use official 3D decoder changes to prioritize cross-scroll augmentation ablations.",
        "evidence_gate": "Require a sprint log entry that records scroll-specific augmentation settings.",
        "review_artifact": "sprint_logs/",
    },
}


def _resolve(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _load_json(path, default):
    path = _resolve(path)
    if not path.exists():
        return default
    with open(path, "r") as f:
        return json.load(f)


def _candidate_digest(preflight):
    rows = preflight.get("rows", [])
    ready = [row for row in rows if row.get("ready_for_gpu") is True]
    return {
        "total_preflight_candidates": int(preflight.get("total", len(rows)) or 0),
        "ready_for_gpu": int(preflight.get("ready_for_gpu", len(ready)) or 0),
        "blocked": int(preflight.get("blocked", 0) or 0),
        "gpu_queue": preflight.get("gpu_queue"),
        "top_ready_candidates": ready[:3],
    }


def _readiness_label(opportunity, digest):
    area = opportunity.get("villa_area")
    if digest["ready_for_gpu"] > 0 and area in {"lasagna", "volume_cartographer", "optimized_inference"}:
        return "ready_now"
    if area == "resnet3d_decoder":
        return "training_ablation"
    return "planning"


_BASELINE_MARKERS = (
    {
        "id": "gp_winner_baseline",
        "label": "Villa GP-2023 TimeSFormerInk recipe",
        "purpose": "fixed research-only comparator (patch 16x256x256, not submittable)",
        "marker_path": "reports/gp_winner_baseline.json",
        "launcher": "scripts/launch_gp_winner.py",
    },
    {
        "id": "mutex_affinity",
        "label": "Villa MutexAffinityTrainer (sheet instance segmentation)",
        "purpose": "Grand-Prize-aligned lane; submittable when patch<=64",
        "marker_path": "reports/mutex_affinity_run.json",
        "launcher": "scripts/launch_mutex.py",
    },
    {
        "id": "neural_tracing_service",
        "label": "Villa neural_tracing trace_service",
        "purpose": "Review-time tracing daemon for VC3D / Crackle Viewer",
        "marker_path": "reports/neural_tracing_service.json",
        "launcher": "scripts/launch_neural_tracing.py",
    },
    {
        "id": "finetune_lejepa",
        "label": "LeJEPA -> UNet ink fine-tune (TrainFineTuneLEJEPA)",
        "purpose": "Convert pretrained LeJEPA encoder into a submittable ink model (patch 64)",
        "marker_path": "reports/finetune_lejepa_run.json",
        "launcher": "scripts/launch_finetune_lejepa.py",
    },
)


def _collect_baselines():
    items = []
    for entry in _BASELINE_MARKERS:
        marker = _load_json(entry["marker_path"], None)
        status = "missing"
        details = {}
        if isinstance(marker, dict):
            details = {
                k: marker.get(k)
                for k in (
                    "model_name",
                    "config_path",
                    "executed",
                    "submittable",
                    "data_prepared",
                    "ready",
                    "blockers",
                )
                if k in marker
            }
            if marker.get("executed"):
                status = "executed"
            elif marker.get("ready") or marker.get("data_prepared"):
                status = "ready"
            else:
                status = "dry_run"
        items.append({**entry, "status": status, "details": details})
    return items


def build_action_matrix(
    opportunities_path="reports/villa_prize_opportunities.json",
    preflight_path="reports/scroll23_evidence_preflight_summary.json",
    limit=5,
):
    opportunities_report = _load_json(opportunities_path, {"opportunities": []})
    preflight = _load_json(preflight_path, {"rows": []})
    digest = _candidate_digest(preflight)

    actions = []
    for rank, opportunity in enumerate(opportunities_report.get("opportunities", [])[:limit], start=1):
        area = opportunity.get("villa_area")
        area_action = AREA_ACTIONS.get(
            area,
            {
                "autopipeline_action": opportunity.get("next_action", ""),
                "evidence_gate": "Review local hook and add a measurable preflight gate.",
                "review_artifact": opportunity.get("local_hook", ""),
            },
        )
        actions.append(
            {
                "rank": rank,
                "id": opportunity.get("id"),
                "official_issue": opportunity.get("official_issue"),
                "title": opportunity.get("title"),
                "track": opportunity.get("track"),
                "villa_area": area,
                "priority_score": opportunity.get("priority_score"),
                "readiness": _readiness_label(opportunity, digest),
                "local_hook": opportunity.get("local_hook"),
                "why_it_matters": opportunity.get("why_it_matters"),
                "official_next_action": opportunity.get("next_action"),
                "autoresearch_action": area_action["autopipeline_action"],
                "evidence_gate": area_action["evidence_gate"],
                "review_artifact": area_action["review_artifact"],
            }
        )

    return {
        "source_opportunities": str(opportunities_path),
        "source_preflight": str(preflight_path),
        "villa_local_ref": opportunities_report.get("villa_local_ref"),
        "villa_upstream_ref": opportunities_report.get("villa_upstream_ref"),
        "villa_behind": bool(opportunities_report.get("villa_behind")),
        "villa_diverged": bool(opportunities_report.get("villa_diverged")),
        "candidate_digest": digest,
        "actions": actions,
        "baselines": _collect_baselines(),
    }


def render_markdown(matrix):
    digest = matrix["candidate_digest"]
    lines = [
        "# Villa Autoresearch Prize Action Matrix",
        "",
        "This matrix joins official `ScrollPrize/villa` opportunity tracking with the current Autoresearch evidence queue.",
        "",
        "## Current State",
        "",
        f"- Villa local ref: `{matrix.get('villa_local_ref')}`",
        f"- Villa upstream ref: `{matrix.get('villa_upstream_ref')}`",
        f"- Villa behind upstream: `{matrix.get('villa_behind')}`",
        f"- Villa diverged with local patches: `{matrix.get('villa_diverged')}`",
        f"- Evidence preflight candidates: `{digest['total_preflight_candidates']}`",
        f"- GPU-ready evidence candidates: `{digest['ready_for_gpu']}`",
        f"- Blocked evidence candidates: `{digest['blocked']}`",
        f"- GPU queue: `{digest.get('gpu_queue')}`",
        "",
        "## Ranked Actions",
        "",
        "| Rank | Official Villa hook | Track | Readiness | Autoresearch action | Evidence gate |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for action in matrix["actions"]:
        title = str(action.get("title") or "").replace("|", "\\|")
        issue = action.get("official_issue") or ""
        hook = f"[{action.get('id')}]({issue}) {title}" if issue else f"{action.get('id')} {title}"
        lines.append(
            "| {rank} | {hook} | `{track}` | `{readiness}` | {autoresearch_action} | {evidence_gate} |".format(
                rank=action["rank"],
                hook=hook,
                track=action.get("track"),
                readiness=action.get("readiness"),
                autoresearch_action=str(action.get("autoresearch_action") or "").replace("|", "\\|"),
                evidence_gate=str(action.get("evidence_gate") or "").replace("|", "\\|"),
            )
        )

    baselines = matrix.get("baselines") or []
    if baselines:
        lines.extend(["", "## Villa Baselines & Lanes", ""])
        lines.append("| ID | Status | Purpose | Marker | Launcher |")
        lines.append("| --- | --- | --- | --- | --- |")
        for b in baselines:
            lines.append(
                "| {id} | `{status}` | {purpose} | `{marker}` | `{launcher}` |".format(
                    id=b.get("id"),
                    status=b.get("status"),
                    purpose=str(b.get("purpose") or "").replace("|", "\\|"),
                    marker=b.get("marker_path"),
                    launcher=b.get("launcher"),
                )
            )

    lines.extend(["", "## Top GPU-Ready Candidates", ""])
    candidates = digest.get("top_ready_candidates", [])
    if not candidates:
        lines.append("- None currently ready.")
    else:
        for row in candidates:
            lines.append(
                "- `{artifact}`: {scroll} {division} z={z} y={y} x={x}, review_score={score}, report=`{report}`".format(
                    artifact=row.get("artifact_stem"),
                    scroll=row.get("scroll_id"),
                    division=row.get("division"),
                    z=row.get("z"),
                    y=row.get("y"),
                    x=row.get("x"),
                    score=row.get("review_score"),
                    report=row.get("report_path"),
                )
            )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--opportunities", default="reports/villa_prize_opportunities.json")
    parser.add_argument("--preflight", default="reports/scroll23_evidence_preflight_summary.json")
    parser.add_argument("--out-json", default="reports/villa_prize_action_matrix.json")
    parser.add_argument("--out-md", default="reports/villa_prize_action_matrix.md")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    matrix = build_action_matrix(args.opportunities, args.preflight, args.limit)
    out_json = _resolve(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(matrix, indent=2) + "\n")

    out_md = _resolve(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(matrix))
    print(json.dumps(matrix, indent=2))


if __name__ == "__main__":
    main()
