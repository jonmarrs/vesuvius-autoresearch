"""The committed prep artifact must not keep telling the retracted story.

gt_finetune_prep.json predates the 2026-08-14 placement gate. It recorded all four
training regions as passing, which is how the GT fine-tune came to train on displaced
labels. Three of those four fail the gate, so the file must not assert any pass.
"""

import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PREP = REPO_ROOT / "reports" / "detector" / "gt_finetune_prep.json"


def test_prep_artifact_claims_no_passing_region():
    d = json.loads(PREP.read_text())
    assert d.get("kept") == [], (
        "kept regions imply a usable training split; there is none"
    )
    for r in d.get("regions", []):
        assert r.get("passed") is not True, (
            f"{r.get('frag_id')} still recorded as passing"
        )


def test_prep_artifact_says_why_and_points_at_the_report():
    d = json.loads(PREP.read_text())
    assert "superseded" in d
    assert "gt_training_data_exhaustion_2026-08-15" in json.dumps(d["superseded"])
