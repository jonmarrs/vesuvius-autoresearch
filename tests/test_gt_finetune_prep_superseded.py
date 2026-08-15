"""The committed prep artifact must not keep telling the retracted story.

gt_finetune_prep.json predates the 2026-08-14 placement gate. It recorded all four
training regions as passing, which is how the GT fine-tune came to train on displaced
labels. Three of those four fail the gate, so the file must not assert any pass.
"""

import json
import pathlib
import sys
from unittest.mock import MagicMock

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PREP = REPO_ROOT / "reports" / "detector" / "gt_finetune_prep.json"
HELDOUT_MD = REPO_ROOT / "reports" / "detector" / "gt_finetune_heldout.md"
HELDOUT_JSON = REPO_ROOT / "reports" / "detector" / "gt_finetune_heldout.json"


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


def test_the_result_report_carries_a_retraction_marker():
    """The prep artifact was corrected while the report of the result was not.

    gt_finetune_heldout.md is the record of the retracted finding and is linked publicly
    from the July filing, so it is the one file that must not read as live evidence.
    """
    md = HELDOUT_MD.read_text()
    assert "RETRACTED" in md.split("# Ground-truth fine-tuning", 1)[0], (
        "the retraction must appear before the title, not buried below it"
    )
    assert "gt_training_data_exhaustion_2026-08-15" in md
    # The original text stays readable; a deletion would defeat the audit trail.
    assert "GT fine-tuning did not add held-out reading" in md


def test_the_result_json_marks_its_copy_of_the_passing_regions_void():
    """It holds a verbatim copy of the four passed:true records removed from the prep
    artifact, which made that removal cosmetic until the copy was marked."""
    d = json.loads(HELDOUT_JSON.read_text())
    assert "superseded" in d
    marker = json.dumps(d["superseded"])
    assert "gt_training_data_exhaustion_2026-08-15" in marker
    assert "void" in marker.lower()
    # Deliberately NOT deleted: this file is the evidentiary record of what was published.
    assert len(d["prep"]["regions"]) == 4


# --- guard reachability regression (2026-08-15) -----------------------------------------


_HEAVY_MODULES = [
    "pytorch_lightning",
    "pytorch_lightning.callbacks",
    "pytorch_lightning.loggers",
    "torch",
    "torch.utils",
    "torch.utils.data",
    "vesuvius_autoresearch.detector.config",
    "vesuvius_autoresearch.detector.data",
    "vesuvius_autoresearch.detector.model",
]


def test_finetune_guard_reaches_the_explanatory_message(monkeypatch):
    """cmd_finetune() used to open with `if not kept: raise ValueError(...)`, a terse
    guard that fired whenever `kept == []` -- exactly what the committed prep JSON now
    contains -- and pre-empted the explanatory `len(kept) < 2` branch below it that
    names the exhaustion report. That guard is gone; this pins that a real call to
    cmd_finetune() against the real committed prep JSON raises the explanatory message,
    not the old terse one, without requiring torch/pytorch_lightning to be installed.
    """
    for name in _HEAVY_MODULES:
        monkeypatch.setitem(sys.modules, name, MagicMock())

    from repro.sota_data import gt_finetune as gf

    with open(PREP) as f:
        kept = json.load(f)["kept"]
    assert kept == [], "test assumes the committed prep JSON has zero kept regions"

    with pytest.raises(ValueError) as exc_info:
        gf.cmd_finetune()

    msg = str(exc_info.value)
    assert "has no kept regions" not in msg, "the pre-empting guard is back"
    assert "gt_training_data_exhaustion_2026-08-15" in msg
    assert "kept only 0 region(s)" in msg


def test_score_refuses_rather_than_overwriting_the_retraction_records(monkeypatch):
    """cmd_score() rewrites both heldout artifacts from scratch, and the ft_epoch=*.ckpt
    models are still on disk -- so it was one invocation away from erasing the retraction
    and re-emitting "N/4 regions passed the teacher-free alignment gate"."""
    for name in _HEAVY_MODULES:
        monkeypatch.setitem(sys.modules, name, MagicMock())

    from repro.sota_data import gt_finetune as gf

    before = (HELDOUT_MD.read_text(), HELDOUT_JSON.read_text())
    with pytest.raises(ValueError) as exc_info:
        gf.cmd_score()
    assert "gt_training_data_exhaustion_2026-08-15" in str(exc_info.value)
    assert (HELDOUT_MD.read_text(), HELDOUT_JSON.read_text()) == before
