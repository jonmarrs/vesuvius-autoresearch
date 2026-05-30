import json

from scripts.review_villa_pin import build_review


def _write_audit(path, *, behind=True, diverged=False, areas=None, local_areas=None):
    payload = {
        "local_ref": "local",
        "upstream_ref": "upstream",
        "merge_base": "base",
        "behind": behind,
        "diverged": diverged,
        "upstream_ahead_commits": 5 if behind else 0,
        "local_ahead_commits": 2 if diverged else 0,
        "changed_files": sum((areas or {}).values()),
        "local_changed_files": sum((local_areas or {}).values())
        or (3 if diverged else 0),
        "prize_relevant_areas": {
            name: {
                "changed_files": count,
                "sample_paths": [f"{name}/file.py"] if count else [],
            }
            for name, count in (areas or {}).items()
        },
        "local_prize_relevant_areas": {
            name: {
                "changed_files": count,
                "sample_paths": [f"{name}/local.py"] if count else [],
            }
            for name, count in (local_areas or {}).items()
        },
    }
    path.write_text(json.dumps(payload))
    return path


def test_review_villa_pin_marks_current_pin_when_not_behind(tmp_path):
    audit = _write_audit(tmp_path / "audit.json", behind=False, areas={"lasagna": 0})

    review = build_review(audit)

    assert review["recommendation"] == "villa_pin_current"
    assert review["villa_behind"] is False
    assert review["adoption_mode"] == "no_update_needed"


def test_review_villa_pin_reviews_medium_risk_changed_areas(tmp_path):
    audit = _write_audit(
        tmp_path / "audit.json", areas={"lasagna": 5, "volume_cartographer": 13}
    )

    review = build_review(audit)
    lasagna = next(area for area in review["areas"] if area["area"] == "lasagna")

    assert review["recommendation"] == "review_changed_areas_before_pin_update"
    assert review["adoption_mode"] == "fast_forward_after_checks"
    assert lasagna["decision"] == "review_before_pin_update"
    assert lasagna["checks"]


def test_review_villa_pin_holds_for_high_risk_inference_changes(tmp_path):
    audit = _write_audit(tmp_path / "audit.json", areas={"optimized_inference": 2})

    review = build_review(audit)
    inference = next(
        area for area in review["areas"] if area["area"] == "optimized_inference"
    )

    assert review["recommendation"] == "hold_pin_until_required_tests_pass"
    assert inference["decision"] == "test_before_pin_update"


def test_review_villa_pin_preserves_local_patches_for_diverged_checkout(tmp_path):
    audit = _write_audit(
        tmp_path / "audit.json",
        diverged=True,
        areas={"lasagna": 5, "volume_cartographer": 13},
        local_areas={"volume_cartographer": 2},
    )

    review = build_review(audit)
    vc3d = next(
        area for area in review["areas"] if area["area"] == "volume_cartographer"
    )

    assert review["recommendation"] == "preserve_local_patches_before_pin_update"
    assert review["adoption_mode"] == "rebase_or_selectively_port"
    assert review["villa_diverged"] is True
    assert review["villa_upstream_ahead_commits"] == 5
    assert review["villa_local_ahead_commits"] == 2
    assert review["local_patch_warning"] is True
    assert vc3d["changed_files"] == 13
    assert vc3d["local_changed_files"] == 2
    assert vc3d["local_sample_paths"] == ["volume_cartographer/local.py"]
