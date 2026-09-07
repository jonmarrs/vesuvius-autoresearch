"""Tests for the same-winding ablation rule, written before any arm existed.

The load-bearing test is `test_geometry_is_not_an_input_to_the_verdict`. The two
previous studies made a geometry rise a FAILURE signal; here it must not enter
the decision at all, because the manipulation removes 5,413 of the inputs
satisfaction is computed against — a rise can mean "less left to satisfy". A
verdict function that read geometry would be measuring the manipulation rather
than its effect.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_same_winding as mod  # noqa: E402
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
    assert mod.ABLATED_ARMS == ("nosame_s1", "nosame_s2", "nosame_s3")
    assert len(mod.BASELINE_ARMS) == 6
    assert mod.REQUIRED_ABLATED == 3 and mod.REQUIRED_BASELINE == 6


def test_geometry_is_not_an_input_to_the_verdict():
    """verdict() takes ink alone. If an edit adds geometry, this fails and forces
    the author to justify deciding on a metric the manipulation directly moves."""
    import inspect

    assert set(inspect.signature(mod.verdict).parameters) == {"ink"}


def test_a_null_ink_result_is_NULL_whatever_geometry_did():
    ink = welch(
        [1.70e6, 1.72e6, 1.68e6, 1.71e6, 1.69e6, 1.70e6], [1.71e6, 1.69e6, 1.73e6]
    )
    tag, why = mod.verdict(ink)
    assert tag == "NULL"
    assert "Bounded, not zero" in why


def test_an_ink_drop_means_the_constraints_help_reading():
    ink = welch(
        [1.85e6, 1.87e6, 1.86e6, 1.85e6, 1.88e6, 1.86e6], [1.60e6, 1.62e6, 1.58e6]
    )
    tag, why = mod.verdict(ink)
    assert tag == "CONSTRAINTS HELP READING"
    assert "MISS against my registered prediction" in why


def test_an_ink_rise_is_flagged_as_needing_a_mechanism():
    ink = welch(
        [1.60e6, 1.62e6, 1.58e6, 1.61e6, 1.59e6, 1.60e6], [1.85e6, 1.87e6, 1.86e6]
    )
    tag, why = mod.verdict(ink)
    assert tag == "REMOVING THEM HELPS"
    assert "needs a mechanism" in why


def test_the_mde_reflects_three_versus_six():
    """3v6 is tighter than the 3v3 of the earlier studies; the registration
    commits to ~8.3%. It first said 7.9% and this test is what caught that."""
    assert mod.mde(3, 6) == pytest.approx(0.083, abs=0.002)
    assert mod.mde(3, 6) < mod.mde(3, 3)


def test_a_partial_sample_is_refused(tmp_path):
    ink = {t: 1.7e6 for t in mod.ABLATED_ARMS}
    ink.update({t: 1.7e6 for t in mod.BASELINE_ARMS[:4]})
    sys.argv = ["x", *_files(tmp_path, ink)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "refused" in str(e.value)


def test_end_to_end_prints_the_geometry_caveat(tmp_path, capsys):
    ink = dict(zip(mod.ABLATED_ARMS, [1.71e6, 1.69e6, 1.73e6], strict=False))
    ink.update(
        dict(
            zip(
                mod.BASELINE_ARMS,
                [1.70e6, 1.72e6, 1.68e6, 1.71e6, 1.69e6, 1.70e6],
                strict=False,
            )
        )
    )
    geom = {t: 0.8480 for t in mod.ABLATED_ARMS}
    geom.update({t: 0.8390 for t in mod.BASELINE_ARMS})
    sys.argv = ["x", *_files(tmp_path, ink, geom)]
    mod.main()
    text = capsys.readouterr().out
    assert "VERDICT: NULL" in text
    assert "REPORT ONLY, NOT AN ENDPOINT" in text
    assert "less left to satisfy" in text
    assert "NOT 'no effect'" in text
