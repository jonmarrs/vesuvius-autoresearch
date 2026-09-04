"""Tests for the patch-bootstrap decision rule.

Written before any of the six arms produced a number.

The test that matters most is `test_geometry_only_gain_is_a_FAILURE`. A method
that selects patches by satisfaction and is then judged on satisfaction is
circular, and the natural reporting instinct — "geometry improved, ink was
inconclusive, promising" — is exactly the error `gap_fix_costs_ink_established.md`
makes impossible to excuse. The rule has to be in code, because prose in a
registration is easy to reinterpret once the numbers are in.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_patch_bootstrap as mod  # noqa: E402
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
    assert mod.RANDOM_ARMS == ("rand090s1", "rand090s2", "rand090s3")
    assert mod.REQUIRED_PER_NEW_ARM == 3


def test_geometry_only_gain_is_a_FAILURE():
    """The core rule. Geometry up, ink null -> FAILURE, never 'promising'."""
    ink = welch([1.70e6, 1.72e6, 1.68e6], [1.71e6, 1.69e6, 1.73e6])  # null
    geom = welch([0.8390, 0.8392, 0.8388], [0.8480, 0.8478, 0.8482])  # up, tight
    tag, why = mod.verdict(ink, geom)
    assert tag == "FAILURE"
    assert "NOT a partial success" in why
    assert "circular" in why


def test_ink_gain_is_the_only_way_to_WORK():
    ink = welch([1.60e6, 1.62e6, 1.58e6], [1.85e6, 1.87e6, 1.86e6])
    geom = welch([0.8390, 0.8392, 0.8388], [0.8480, 0.8478, 0.8482])
    assert mod.verdict(ink, geom)[0] == "WORKS"


def test_an_ink_loss_is_reported_as_harm_even_if_geometry_rose():
    ink = welch([1.85e6, 1.87e6, 1.86e6], [1.60e6, 1.62e6, 1.58e6])
    geom = welch([0.8390, 0.8392, 0.8388], [0.8480, 0.8478, 0.8482])
    assert mod.verdict(ink, geom)[0] == "HARMS"


def test_both_null_is_NULL_not_failure():
    ink = welch([1.70e6, 1.72e6, 1.68e6], [1.71e6, 1.69e6, 1.73e6])
    geom = welch([0.8390, 0.8392, 0.8388], [0.8391, 0.8389, 0.8392])
    assert mod.verdict(ink, geom)[0] == "NULL"


def test_geometry_DOWN_with_null_ink_is_not_a_failure_verdict():
    """FAILURE means specifically the circular pattern. Geometry falling is a
    different thing and must not be relabelled."""
    ink = welch([1.70e6, 1.72e6, 1.68e6], [1.71e6, 1.69e6, 1.73e6])
    geom = welch([0.8480, 0.8478, 0.8482], [0.8390, 0.8392, 0.8388])
    assert mod.verdict(ink, geom)[0] == "NULL"


def test_a_partial_sample_is_refused(tmp_path):
    ink = {t: 1.7e6 for t in mod.BOOTSTRAP_ARMS[:2]}
    ink.update({t: 1.7e6 for t in mod.RANDOM_ARMS})
    sys.argv = ["x", *_files(tmp_path, ink)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "refused" in str(e.value)


def test_an_unregistered_arm_is_refused(tmp_path):
    ink = {t: 1.7e6 for t in mod.BOOTSTRAP_ARMS + mod.RANDOM_ARMS}
    ink["gap133"] = 1.5e6
    sys.argv = ["x", *_files(tmp_path, ink)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "gap133" in str(e.value)


def test_the_mde_matches_the_registered_figure():
    """The registration commits to ~9.6% at 3 vs 3 and CV 0.0421."""
    assert mod.mde(3, 3) == pytest.approx(0.096, abs=0.004)


def test_end_to_end_reports_the_verdict_and_the_null_reading(tmp_path, capsys):
    ink = dict(zip(mod.BOOTSTRAP_ARMS, [1.71e6, 1.69e6, 1.73e6], strict=False))
    ink.update(dict(zip(mod.RANDOM_ARMS, [1.70e6, 1.72e6, 1.68e6], strict=False)))
    geom = dict(zip(mod.BOOTSTRAP_ARMS, [0.8480, 0.8478, 0.8482], strict=False))
    geom.update(dict(zip(mod.RANDOM_ARMS, [0.8390, 0.8392, 0.8388], strict=False)))
    out = tmp_path / "res.json"
    sys.argv = ["x", *_files(tmp_path, ink, geom), "--out", str(out)]
    mod.main()
    text = capsys.readouterr().out
    assert "VERDICT: FAILURE" in text
    assert "NOT 'no effect'" in text
    got = json.loads(out.read_text())
    assert got["verdict"] == "FAILURE"
    assert got["prediction_met"] is True
