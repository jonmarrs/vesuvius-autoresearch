import json

from scripts.review_villa_pin import build_review


def _write_audit(path, *, behind=True, areas=None):
    payload = {
        "local_ref": "local",
        "upstream_ref": "upstream",
        "behind": behind,
        "changed_files": sum((areas or {}).values()),
        "prize_relevant_areas": {
            name: {"changed_files": count, "sample_paths": [f"{name}/file.py"] if count else []}
            for name, count in (areas or {}).items()
        },
    }
    path.write_text(json.dumps(payload))
    return path


def test_review_villa_pin_marks_current_pin_when_not_behind(tmp_path):
    audit = _write_audit(tmp_path / "audit.json", behind=False, areas={"lasagna": 0})

    review = build_review(audit)

    assert review["recommendation"] == "villa_pin_current"
    assert review["villa_behind"] is False


def test_review_villa_pin_reviews_medium_risk_changed_areas(tmp_path):
    audit = _write_audit(tmp_path / "audit.json", areas={"lasagna": 5, "volume_cartographer": 13})

    review = build_review(audit)
    lasagna = next(area for area in review["areas"] if area["area"] == "lasagna")

    assert review["recommendation"] == "review_changed_areas_before_pin_update"
    assert lasagna["decision"] == "review_before_pin_update"
    assert lasagna["checks"]


def test_review_villa_pin_holds_for_high_risk_inference_changes(tmp_path):
    audit = _write_audit(tmp_path / "audit.json", areas={"optimized_inference": 2})

    review = build_review(audit)
    inference = next(area for area in review["areas"] if area["area"] == "optimized_inference")

    assert review["recommendation"] == "hold_pin_until_required_tests_pass"
    assert inference["decision"] == "test_before_pin_update"
