"""Tests for the outer-winding floor rule.

Written alongside the script and BEFORE the three seed renders finished, for the
reason the script's own docstring gives: a decision rule that first executes on
real data is a rule you can still talk yourself out of.

What matters most here is that the REVERSES branch is reachable and says the
uncomfortable thing. A rule whose only attainable verdict is "my earlier report was
fine" is not a rule, and this repository has already shipped one arm whose
verification condition could never fire.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_outer_floor as mod  # noqa: E402


def _verdict(metric, values):
    point = mod.cv(values)
    return mod.rule(metric, 2 * point, len(values), point)[0]


def test_a_single_arm_is_refused_rather_than_called_zero_spread():
    """One value has sd 0. Printing CV 0.0000 would read as 'no noise at all',
    which is the opposite of what one observation supports."""
    with pytest.raises(SystemExit):
        mod.cv([1_700_000.0])


def test_the_observed_deltas_are_constants_not_arguments():
    """They are already published. If they were arguments the rule could be
    re-aimed after seeing the floor."""
    assert mod.OBSERVED["total_fg_pixels"] == pytest.approx(-0.110300)
    assert mod.OBSERVED["overall_column_score"] == pytest.approx(-0.465748)


def test_the_cv_interval_brackets_the_point_estimate():
    lo, hi = mod.cv_interval(0.10, 4)
    assert lo < 0.10 < hi
    # registered as 0.57x to 3.73x at n=4, the exact chi values
    assert lo / 0.10 == pytest.approx(0.5665, abs=1e-3)
    assert hi / 0.10 == pytest.approx(3.7285, abs=1e-3)


def test_the_interval_narrows_as_n_grows():
    lo4, hi4 = mod.cv_interval(0.10, 4)
    lo9, hi9 = mod.cv_interval(0.10, 9)
    assert (hi9 - lo9) < (hi4 - lo4)


def test_a_noisy_outer_region_leaves_the_published_conclusion_standing():
    """Spread far wider than 11.03%: the whole floor interval clears the
    observation and nothing about the previous report changes."""
    assert _verdict("total_fg_pixels", [1.0e6, 1.6e6, 2.2e6, 2.8e6]) == "STANDS"


def test_a_very_quiet_outer_region_REVERSES_the_published_conclusion():
    """The branch that matters. If the outer windings are quiet enough that
    11.03% clears the floor outright, the gap fix has a measured negative ink
    effect and the earlier report is wrong. This must be reachable."""
    tag, sentence = mod.rule("total_fg_pixels", 2 * 0.004, 4, 0.004)
    assert tag == "REVERSES"
    assert "REVERSES" in sentence
    assert "NEGATIVE" in sentence
    assert "not as a" in sentence  # ... "not as a refinement"


def test_reverses_is_reachable_from_real_looking_arm_values():
    """Not just from a hand-passed CV: four tightly clustered renders get there."""
    assert (
        _verdict("total_fg_pixels", [1_789_206, 1_791_000, 1_787_500, 1_790_100])
        == "REVERSES"
    )


def test_a_straddling_interval_is_unresolved_not_rounded_to_a_side():
    """Point floor above the observation, but the interval covers it: the
    registered answer is UNRESOLVED, not STANDS."""
    point = 0.075  # floor 15.0%, above the observed 11.03%
    lo, hi = mod.cv_interval(point, 4)
    assert 2 * lo < 0.110300 < 2 * hi, "test premise: interval must straddle"
    assert mod.rule("total_fg_pixels", 2 * point, 4, point)[0] == "UNRESOLVED"


def test_the_column_observation_is_retired_when_the_floor_exceeds_it():
    assert _verdict("overall_column_score", [0.05, 0.15, 0.25, 0.35]) == "RETIRED"


def test_a_surviving_column_observation_is_only_ever_a_candidate():
    """It was never pre-registered for that arm, so it cannot be promoted to a
    claim by this script no matter how far it clears."""
    tag, sentence = mod.rule("overall_column_score", 2 * 0.001, 4, 0.001)
    assert tag == "CANDIDATE"
    assert "not a claim" in sentence


def test_the_line_score_is_reported_and_carries_no_verdict():
    tag, _ = mod.rule("overall_line_score", 2 * 0.03, 4, 0.03)
    assert tag == "REPORTED"


def test_end_to_end_over_written_metrics_files(tmp_path):
    """The script's own entry point, so a refactor that breaks argument parsing
    fails here rather than after a seven-hour render."""
    args = []
    for i, fg in enumerate([1_789_206, 1_650_000, 1_900_000, 1_720_000]):
        p = tmp_path / f"m{i}.json"
        p.write_text(
            json.dumps(
                {
                    "summary": {
                        "total_fg_pixels": fg,
                        "overall_line_score": 0.34 + i * 0.001,
                        "overall_column_score": 0.24 - i * 0.01,
                    }
                }
            )
        )
        args.append(f"seed0{i + 1}={p}")
    out = tmp_path / "out.json"
    sys.argv = ["analyse_outer_floor.py", *args, "--out", str(out)]
    mod.main()
    written = json.loads(out.read_text())
    assert written["n"] == 4
    assert set(written["results"]) == set(mod.INNER_CV)
    assert written["results"]["total_fg_pixels"]["verdict"] in {
        "STANDS",
        "REVERSES",
        "UNRESOLVED",
    }
