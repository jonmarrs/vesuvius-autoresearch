#!/usr/bin/env python3
"""
Build a safe update checklist for the local ScrollPrize/villa checkout.

The goal is to avoid blind submodule updates. This script reads the existing
Villa upstream audit and turns it into a focused review plan for prize-relevant
areas before Autoresearch adopts a newer official Villa commit.
"""
import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REVIEW_AREAS = {
    "lasagna": {
        "risk": "medium",
        "reason": "Geometry preprocessing changes can reorder or alter Scroll 2/3 candidate surfaces.",
        "checks": [
            "uv run python scripts/build_lasagna_fiber_worklist.py --ranked reports/scroll23_ranked_candidates.tsv --limit 12",
            "uv run python scripts/run_post_sprint_villa_handoff.py --preflight-only",
        ],
    },
    "volume_cartographer": {
        "risk": "medium",
        "reason": "VC3D review and dataset changes affect how ink/fiber overlays are inspected.",
        "checks": [
            "uv run python scripts/validate_prize_artifact.py --metadata predictions/pred_10_1000_1000_64x64_meta.json",
            "uv run python scripts/run_post_sprint_villa_handoff.py --preflight-only",
        ],
    },
    "optimized_inference": {
        "risk": "high",
        "reason": "Inference contract changes can break reproducible prize packaging.",
        "checks": [
            "uv run python scripts/smoke_test_villa_optimized_inference.py",
        ],
    },
    "resnet3d_decoder": {
        "risk": "high",
        "reason": "Model contract changes can affect checkpoint compatibility and inference outputs.",
        "checks": [
            "uv run python scripts/smoke_test_villa_optimized_inference.py",
        ],
    },
    "vesuvius_data": {
        "risk": "medium",
        "reason": "Data loader changes can change candidate occupancy and volume addressing.",
        "checks": [
            "uv run python scripts/rank_scroll23_candidates.py --queue reports/scroll23_search_queue.tsv --prediction-dir predictions --out reports/scroll23_ranked_candidates.tsv",
        ],
    },
    "prize_docs": {
        "risk": "high",
        "reason": "Prize criteria changes can invalidate packaging assumptions.",
        "checks": [
            "uv run python scripts/validate_prize_artifact.py --metadata predictions/pred_10_1000_1000_64x64_meta.json",
        ],
    },
}


def _load_json(path):
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    with open(path) as f:
        return json.load(f)


def _decision_for(changed_files, risk):
    if changed_files == 0:
        return "no_action"
    if risk == "high":
        return "test_before_pin_update"
    return "review_before_pin_update"


def build_review(audit_path="reports/villa_upstream_audit.json"):
    audit = _load_json(audit_path)
    areas = []
    for area, spec in REVIEW_AREAS.items():
        audit_area = audit.get("prize_relevant_areas", {}).get(area, {})
        local_area = audit.get("local_prize_relevant_areas", {}).get(area, {})
        changed_files = int(audit_area.get("changed_files") or 0)
        local_changed_files = int(local_area.get("changed_files") or 0)
        areas.append(
            {
                "area": area,
                "changed_files": changed_files,
                "local_changed_files": local_changed_files,
                "sample_paths": audit_area.get("sample_paths", []),
                "local_sample_paths": local_area.get("sample_paths", []),
                "risk": spec["risk"],
                "decision": _decision_for(changed_files, spec["risk"]),
                "reason": spec["reason"],
                "checks": spec["checks"] if changed_files else [],
            }
        )

    changed_areas = [area for area in areas if area["changed_files"]]
    local_changed_areas = [area for area in areas if area["local_changed_files"]]
    if not audit.get("behind"):
        recommendation = "villa_pin_current"
    elif audit.get("diverged"):
        recommendation = "preserve_local_patches_before_pin_update"
    elif any(area["decision"] == "test_before_pin_update" for area in changed_areas):
        recommendation = "hold_pin_until_required_tests_pass"
    elif changed_areas:
        recommendation = "review_changed_areas_before_pin_update"
    else:
        recommendation = "pin_update_low_risk_after_smoke_check"

    adoption_mode = "no_update_needed"
    if audit.get("behind") and audit.get("diverged"):
        adoption_mode = "rebase_or_selectively_port"
    elif audit.get("behind"):
        adoption_mode = "fast_forward_after_checks"

    return {
        "source_audit": str(audit_path),
        "villa_local_ref": audit.get("local_ref"),
        "villa_upstream_ref": audit.get("upstream_ref"),
        "villa_merge_base": audit.get("merge_base"),
        "villa_behind": bool(audit.get("behind")),
        "villa_diverged": bool(audit.get("diverged")),
        "villa_upstream_ahead_commits": int(audit.get("upstream_ahead_commits", 0) or 0),
        "villa_local_ahead_commits": int(audit.get("local_ahead_commits", 0) or 0),
        "changed_files": audit.get("changed_files", 0),
        "local_changed_files": audit.get("local_changed_files", 0),
        "adoption_mode": adoption_mode,
        "recommendation": recommendation,
        "local_patch_warning": int(audit.get("local_changed_files", 0) or 0) > 0 or bool(local_changed_areas),
        "areas": areas,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", default="reports/villa_upstream_audit.json")
    parser.add_argument("--out", default="reports/villa_pin_review.json")
    args = parser.parse_args()

    report = build_review(args.audit)
    out = Path(args.out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
