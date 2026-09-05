"""Tests for the STRIPMATCH decision rule, written before any arm existed.

The rule is the parent study's, and the branch that has to survive contact with
the data is the same one: geometry up + ink null is a FAILURE. It matters more
here, not less. BOOTSTRAP is selected ON satisfaction and STRIPMATCH is not, so
the geometry comparison is guaranteed to flatter BOOTSTRAP, and reading that as
"promising" would be reporting an artefact of the selection rule.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_stripmatch as mod  # noqa: E402
from analyse_gap_ink_arm import welch  # noqa: E402


def _files(tmp_path, ink_by_tag, geom_by_tag=None):
    args = []
    for tag, fg in ink_by_tag.items():
        m = tmp_path / f"{tag}.json"
        m.write_text(
            json.dumps(
                {
                    "summary": {
                        "total_fg_pixels": fg,
                        "overall_fg_fraction": fg / 3.6e8,
                        "overall_line_score": 0.35,
                        "overall_column_score": 0.19,
                    }
                }
            )
        )
        spec = f"{tag}={m}"
        if geom_by_tag and tag in geom_by_tag:
            s = tmp_path / f"{tag}_sat.json"
            s.write_text(
                json.dumps({"summary": {"satisfied_area_fraction": geom_by_tag[tag]}})
            )
            spec += f",{s}"
        args.append(spec)
    return args


def test_the_registered_arms_are_constants():
    assert mod.BOOTSTRAP_ARMS == ("boot090s1", "boot090s2", "boot090s3")
    assert mod.STRIPMATCH_ARMS == ("strip090s1", "strip090s2", "strip090s3")
    assert mod.REQUIRED_PER_ARM == 3


def test_geometry_only_gain_is_still_a_FAILURE():
    """The circular geometry gain is GUARANTEED here; it must never read as promise."""
    ink = welch([1.70e6, 1.72e6, 1.68e6], [1.71e6, 1.69e6, 1.73e6])
    geom = welch([0.8330, 0.8340, 0.8320], [0.9798, 0.9795, 0.9804])
    tag, why = mod.verdict(ink, geom)
    assert tag == "FAILURE"
    assert "NOT a partial success" in why
    assert "side effect rather than the cause" in why


def test_an_ink_gain_is_the_only_WORKS_and_is_marked_a_prediction_miss():
    ink = welch([1.60e6, 1.62e6, 1.58e6], [1.85e6, 1.87e6, 1.86e6])
    geom = welch([0.8330, 0.8340, 0.8320], [0.9798, 0.9795, 0.9804])
    tag, why = mod.verdict(ink, geom)
    assert tag == "WORKS"
    assert "MISS against my registered prediction" in why


def test_an_ink_loss_is_HARMS_even_with_geometry_up():
    ink = welch([1.85e6, 1.87e6, 1.86e6], [1.60e6, 1.62e6, 1.58e6])
    geom = welch([0.8330, 0.8340, 0.8320], [0.9798, 0.9795, 0.9804])
    assert mod.verdict(ink, geom)[0] == "HARMS"


def test_both_null_is_NULL():
    ink = welch([1.70e6, 1.72e6, 1.68e6], [1.71e6, 1.69e6, 1.73e6])
    geom = welch([0.8330, 0.8340, 0.8320], [0.8331, 0.8339, 0.8321])
    assert mod.verdict(ink, geom)[0] == "NULL"


def test_the_prediction_is_met_by_FAILURE_and_NULL_only():
    """Recorded so a WORKS or HARMS result cannot be quietly scored as a hit."""
    ink_null = welch([1.70e6, 1.72e6, 1.68e6], [1.71e6, 1.69e6, 1.73e6])
    ink_up = welch([1.60e6, 1.62e6, 1.58e6], [1.85e6, 1.87e6, 1.86e6])
    geom_up = welch([0.8330, 0.8340, 0.8320], [0.9798, 0.9795, 0.9804])
    assert mod.verdict(ink_null, geom_up)[0] in ("FAILURE", "NULL")
    assert mod.verdict(ink_up, geom_up)[0] == "WORKS"


def test_a_partial_sample_is_refused(tmp_path):
    ink = {t: 1.7e6 for t in mod.BOOTSTRAP_ARMS}
    ink.update({t: 1.7e6 for t in mod.STRIPMATCH_ARMS[:2]})
    sys.argv = ["x", *_files(tmp_path, ink)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "refused" in str(e.value)


def test_a_parent_study_arm_is_refused(tmp_path):
    """rand090s* belong to the parent comparison and must not leak in here."""
    ink = {t: 1.7e6 for t in mod.BOOTSTRAP_ARMS + mod.STRIPMATCH_ARMS}
    ink["rand090s1"] = 1.6e6
    sys.argv = ["x", *_files(tmp_path, ink)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "rand090s1" in str(e.value)


def test_end_to_end_reports_failure_and_the_bounded_null(tmp_path, capsys):
    ink = dict(zip(mod.BOOTSTRAP_ARMS, [1.71e6, 1.69e6, 1.73e6], strict=False))
    ink.update(dict(zip(mod.STRIPMATCH_ARMS, [1.70e6, 1.72e6, 1.68e6], strict=False)))
    geom = dict(zip(mod.BOOTSTRAP_ARMS, [0.9798, 0.9795, 0.9804], strict=False))
    geom.update(dict(zip(mod.STRIPMATCH_ARMS, [0.8330, 0.8340, 0.8320], strict=False)))
    out = tmp_path / "res.json"
    sys.argv = ["x", *_files(tmp_path, ink, geom), "--out", str(out)]
    mod.main()
    text = capsys.readouterr().out
    assert "VERDICT: FAILURE" in text
    assert "NOT 'no effect'" in text
    assert "carries no credit" in text
    assert json.loads(out.read_text())["prediction_met"] is True
