#!/usr/bin/env python3
"""
Rank concrete ways to use ScrollPrize/villa for prize-facing Autoresearch work.

Inputs are local and reproducible: the Villa upstream audit plus a curated list
of official open issue cues that are good matches for this repository.
"""
import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


OFFICIAL_OPPORTUNITIES = [
    {
        "id": "villa-issue-203",
        "official_issue": "https://github.com/ScrollPrize/villa/issues/203",
        "title": "Whole-volume deformation from vertical fibers and large meshes",
        "track": "progress_prize",
        "villa_area": "volume_cartographer",
        "local_hook": "scripts/register_volumes.py + generate_fiber_labels.py",
        "why_it_matters": "Improves surface geometry and deformation correction, a blocker for legible Scroll 2/3 text.",
        "next_action": "Prototype a deformation review metric that compares fiber coherence before/after registration.",
        "base_score": 88,
    },
    {
        "id": "villa-issue-201",
        "official_issue": "https://github.com/ScrollPrize/villa/issues/201",
        "title": "Scroll-specific 3D augmentations for model training",
        "track": "progress_and_first_letters",
        "villa_area": "resnet3d_decoder",
        "local_hook": "train.py scroll-specific 3D augmentation preset",
        "why_it_matters": "Targets cross-scroll generalization, the core weakness for First Letters and Title submissions.",
        "next_action": "Run ablations over aug_scroll_decohesion_p, aug_scroll_squeeze_p, aug_scroll_z_dropout_p, and aug_scroll_intensity_drift_p.",
        "base_score": 92,
    },
    {
        "id": "villa-issue-193",
        "official_issue": "https://github.com/ScrollPrize/villa/issues/193",
        "title": "Methods for generating surface, fiber, or ink labels",
        "track": "progress_and_first_letters",
        "villa_area": "lasagna",
        "local_hook": "scripts/compute_structure_tensors.py + scripts/run_villa_prize_evidence_chain.py",
        "why_it_matters": "Creates better supervision and review evidence for non-metal ink signals in Scrolls 2-3.",
        "next_action": "Convert top occupancy-aware candidates into a label-generation worklist for Lasagna and Crackle review.",
        "base_score": 95,
    },
    {
        "id": "villa-issue-192",
        "official_issue": "https://github.com/ScrollPrize/villa/issues/192",
        "title": "Accurate 3D ink labels",
        "track": "progress_and_grand_prize",
        "villa_area": "optimized_inference",
        "local_hook": "scripts/smoke_test_villa_optimized_inference.py + scripts/validate_prize_artifact.py",
        "why_it_matters": "Aligns our model outputs with official 3D labeling and reproducible inference expectations.",
        "next_action": "Extend the optimized-inference smoke test to cover upstream 3D decoder model contracts.",
        "base_score": 86,
    },
    {
        "id": "villa-issue-191",
        "official_issue": "https://github.com/ScrollPrize/villa/issues/191",
        "title": "Surface and fiber predictions in compressed or highly curved areas",
        "track": "first_letters",
        "villa_area": "lasagna",
        "local_hook": "reports/scroll23_ranked_candidates.tsv + scripts/launch_crackle_viewer.py",
        "why_it_matters": "Scroll 2/3 high-value candidates often sit in hard geometry where plain ink inference stays low confidence.",
        "next_action": "Route high-occupancy, high-fiber candidates to Lasagna preprocessing before ink inference.",
        "base_score": 98,
    },
    {
        "id": "villa-issue-369",
        "official_issue": "https://github.com/ScrollPrize/villa/issues/369",
        "title": "VC3D integrate fiber predictions",
        "track": "progress_prize",
        "villa_area": "volume_cartographer",
        "local_hook": "predict.py fiber outputs + VC3D-compatible Zarr metadata",
        "why_it_matters": "Turns Autoresearch fiber predictions into a community-usable VC3D review layer.",
        "next_action": "Export fiber maps beside ink maps as VC3D OME-Zarr overlays and document the viewer workflow.",
        "base_score": 90,
    },
    {
        "id": "villa-issue-497",
        "official_issue": "https://github.com/ScrollPrize/villa/issues/497",
        "title": "vc_render_tifxyz OME-Zarr metadata scales",
        "track": "progress_prize",
        "villa_area": "volume_cartographer",
        "local_hook": "scripts/validate_prize_artifact.py VC3D/Zarr checks",
        "why_it_matters": "Correct scale metadata is a direct submission requirement because images need accurate 1 cm scale bars.",
        "next_action": "Add a scale-metadata regression test using our prize artifact validator as the oracle.",
        "base_score": 82,
    },
]


def _load_audit(path):
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return json.load(f)


def _area_boost(audit, area):
    info = audit.get("prize_relevant_areas", {}).get(area, {})
    changed = int(info.get("changed_files", 0) or 0)
    if changed >= 100:
        return 10
    if changed >= 10:
        return 6
    if changed > 0:
        return 3
    return 0


def build_opportunity_plan(audit_path="reports/villa_upstream_audit.json", limit=None):
    audit = _load_audit(audit_path)
    rows = []
    for item in OFFICIAL_OPPORTUNITIES:
        score = item["base_score"] + _area_boost(audit, item["villa_area"])
        if audit.get("behind"):
            score += 2
        row = dict(item)
        row["priority_score"] = score
        row["villa_pin_status"] = "behind_upstream" if audit.get("behind") else "current_or_unknown"
        rows.append(row)

    rows.sort(key=lambda row: row["priority_score"], reverse=True)
    if limit is not None:
        rows = rows[:limit]

    return {
        "source_audit": str(audit_path),
        "villa_local_ref": audit.get("local_ref"),
        "villa_upstream_ref": audit.get("upstream_ref"),
        "villa_behind": bool(audit.get("behind")),
        "opportunities": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", default="reports/villa_upstream_audit.json")
    parser.add_argument("--out", default="reports/villa_prize_opportunities.json")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    report = build_opportunity_plan(args.audit, args.limit)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
