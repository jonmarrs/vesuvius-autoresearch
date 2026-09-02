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
        args.append(f"{mod.REGISTERED_ARMS[i]}={p}")
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


def _metrics_file(tmp_path, name, fg, sat=None):
    p = tmp_path / f"{name}.json"
    p.write_text(
        json.dumps(
            {
                "summary": {
                    "total_fg_pixels": fg,
                    "overall_line_score": 0.34,
                    "overall_column_score": 0.24,
                }
            }
        )
    )
    if sat is None:
        return str(p)
    s = tmp_path / f"{name}_sat.json"
    s.write_text(json.dumps({"summary": {"satisfied_area_fraction": sat}}))
    return f"{p},{s}"


def test_an_unregistered_arm_is_refused(tmp_path):
    """The trap this gate exists for. gap133 is a CONFIG arm; pooling it would put
    a config effect into a seed floor, and a wider floor is exactly what leaves the
    published conclusion standing -- failure in the flattering direction."""
    sys.argv = [
        "analyse_outer_floor.py",
        f"baseline01={_metrics_file(tmp_path, 'a', 1_789_206)}",
        f"gap133={_metrics_file(tmp_path, 'b', 1_591_857)}",
    ]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "gap133" in str(e.value)


def test_quality_alone_would_not_have_caught_gap133():
    """Documents why the allowlist is needed on top of the quality gate: gap133's
    satisfied_area is 0.0082 from baseline01, inside the 0.01 band."""
    assert abs(0.8480 - 0.8398) < mod.QUALITY_BAND


def test_a_duplicated_arm_is_refused(tmp_path):
    """Passing one arm twice shrinks the CV toward zero, which pushes the verdict
    toward REVERSES. Refuse rather than compute it."""
    f = _metrics_file(tmp_path, "a", 1_789_206)
    sys.argv = ["analyse_outer_floor.py", f"seed02={f}", f"seed02={f}"]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "twice" in str(e.value)


def test_the_quality_gate_drops_an_outlying_fit(tmp_path, capsys):
    """A fit whose satisfied_area sits outside the band is not a like-for-like
    member of the sample and must be named, not averaged in."""
    rows = [
        {"tag": "baseline01", "satisfied_area_fraction": 0.8398},
        {"tag": "seed02", "satisfied_area_fraction": 0.8402},
        {"tag": "seed03", "satisfied_area_fraction": 0.8390},
        {"tag": "seed04", "satisfied_area_fraction": 0.9600},
    ]
    kept = mod.quality_gate(rows)
    assert [r["tag"] for r in kept] == ["baseline01", "seed02", "seed03"]
    assert "seed04" in capsys.readouterr().out


def test_the_quality_gate_pools_four_honest_seeds(tmp_path, capsys):
    """The real values: spread 0.0022, comfortably inside the band."""
    rows = [
        {"tag": t, "satisfied_area_fraction": s}
        for t, s in zip(
            mod.REGISTERED_ARMS, [0.8398, 0.8382, 0.8404, 0.8390], strict=False
        )
    ]
    assert len(mod.quality_gate(rows)) == 4
    assert "pooled" in capsys.readouterr().out


def test_the_quality_gate_skips_when_satisfaction_is_not_supplied(capsys):
    """It must announce that it skipped, so a missing gate is visible rather than
    mistaken for a pass."""
    rows = [{"tag": "seed02"}, {"tag": "seed03"}]
    assert len(mod.quality_gate(rows)) == 2
    assert "SKIPPED" in capsys.readouterr().out
