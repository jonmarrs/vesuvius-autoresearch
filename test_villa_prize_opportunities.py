import json

from scripts.plan_villa_prize_opportunities import build_opportunity_plan


def test_villa_prize_opportunities_prioritize_large_upstream_deltas(tmp_path):
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "local_ref": "local",
                "upstream_ref": "upstream",
                "behind": True,
                "prize_relevant_areas": {
                    "lasagna": {"changed_files": 150},
                    "volume_cartographer": {"changed_files": 314},
                    "optimized_inference": {"changed_files": 7},
                    "resnet3d_decoder": {"changed_files": 2},
                },
            }
        )
    )

    report = build_opportunity_plan(audit_path=audit_path, limit=3)

    assert report["villa_behind"] is True
    assert len(report["opportunities"]) == 3
    assert report["opportunities"][0]["id"] == "villa-issue-191"
    assert report["opportunities"][0]["priority_score"] > report["opportunities"][-1]["priority_score"]
    assert all(row["villa_pin_status"] == "behind_upstream" for row in report["opportunities"])


def test_villa_prize_opportunities_work_without_audit(tmp_path):
    report = build_opportunity_plan(audit_path=tmp_path / "missing.json", limit=1)

    assert report["villa_behind"] is False
    assert len(report["opportunities"]) == 1
    assert report["opportunities"][0]["official_issue"].startswith("https://github.com/ScrollPrize/villa/issues/")
