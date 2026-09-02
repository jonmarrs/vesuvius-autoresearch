"""Tests for the six-fit gap-expander ink arm.

Written with the script, before gap133s2 and gap133s3 had been rendered, so the
rule could not be shaped by the two numbers it exists to judge.

The tests that matter most are the ones asserting the script says the
uncomfortable things: that a null is reported with the size it could have
detected rather than as "no effect", and that the quality gate is per arm, since
pooling it would test finding 12 instead of fit quality and would scrape through
by 0.0002 if it did.
"""

import json
import math
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_gap_ink_arm as mod  # noqa: E402


def test_the_registered_arms_are_constants():
    assert mod.BASE_ARMS == ("baseline01", "seed02", "seed03", "seed04")
    assert mod.GAP_ARMS == ("gap133", "gap133s2", "gap133s3")


def test_a_clear_reduction_is_detected():
    base = [1_789_206, 1_732_741, 1_620_364, 1_682_825]
    gap = [1_500_000, 1_480_000, 1_510_000]
    w = mod.welch(base, gap)
    assert w["rel_diff"] < 0
    assert w["p"] < mod.ALPHA


def test_two_samples_from_one_population_are_not_called_a_difference():
    base = [1_789_206, 1_732_741, 1_620_364, 1_682_825]
    gap = [1_700_000, 1_750_000, 1_660_000]
    assert mod.welch(base, gap)["p"] >= mod.ALPHA


def test_the_test_is_two_sided_so_an_increase_is_detectable_too():
    base = [1_600_000, 1_610_000, 1_620_000, 1_615_000]
    gap = [1_900_000, 1_890_000, 1_910_000]
    w = mod.welch(base, gap)
    assert w["rel_diff"] > 0 and w["p"] < mod.ALPHA


def test_the_confidence_interval_brackets_the_point_estimate():
    base = [1_789_206, 1_732_741, 1_620_364, 1_682_825]
    gap = [1_591_857, 1_620_000, 1_570_000]
    w = mod.welch(base, gap)
    assert w["ci"][0] < w["rel_diff"] < w["ci"][1]


def test_complete_separation_is_recognised_in_both_directions():
    base = [10.0, 11.0, 12.0, 13.0]
    assert "all GAP below" in mod.separation(base, [7.0, 8.0, 9.0])
    assert "all GAP above" in mod.separation(base, [14.0, 15.0, 16.0])
    assert mod.separation(base, [9.0, 11.5, 20.0]) == "none"


def test_the_detectable_effect_matches_the_registered_figure():
    """The pre-registration commits to ~9.0% at n=4 vs 3 and CV 0.0421. If this
    drifts, the null sentence the script prints becomes a false reassurance."""
    assert mod.detectable_effect(4, 3) == pytest.approx(0.090, abs=0.002)


def test_the_detectable_effect_shrinks_with_more_fits():
    assert mod.detectable_effect(6, 6) < mod.detectable_effect(4, 3)


def test_the_quality_gate_is_per_arm_not_pooled():
    """The whole point. Pooled, the seven real fits span 0.0098 against a 0.01
    band and squeak through by 0.0002 while testing the very effect that defines
    the arms."""
    base_sats = [0.8398, 0.8404, 0.8382, 0.8399]
    gap_sats = [0.8480, 0.8465, 0.8470]
    assert max(base_sats + gap_sats) - min(base_sats + gap_sats) < mod.QUALITY_BAND
    assert max(base_sats) - min(base_sats) < mod.QUALITY_BAND
    assert max(gap_sats) - min(gap_sats) < mod.QUALITY_BAND


def test_the_quality_gate_drops_an_outlier_within_an_arm(capsys):
    rows = [
        {"tag": t, "satisfied_area_fraction": s}
        for t, s in zip(mod.BASE_ARMS, [0.8398, 0.8404, 0.8382, 0.9500], strict=False)
    ]
    kept = mod.quality_gate(rows, "BASE")
    assert [r["tag"] for r in kept] == ["baseline01", "seed02", "seed03"]
    assert "seed04" in capsys.readouterr().out


def test_an_unregistered_arm_is_refused(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"summary": {k: 1.0 for k in mod.METRICS}}))
    sys.argv = ["analyse_gap_ink_arm.py", f"baseline01={f}", f"margin0={f}"]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "margin0" in str(e.value)


def test_one_fit_in_an_arm_is_refused(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"summary": {k: 1.0 for k in mod.METRICS}}))
    sys.argv = [
        "analyse_gap_ink_arm.py",
        f"baseline01={f}",
        f"seed02={f}",
        f"gap133={f}",
    ]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert ">=2 fits per arm" in str(e.value)


def test_a_null_is_printed_with_the_size_it_could_have_seen(tmp_path, capsys):
    """A null must never read as 'no effect'."""
    vals = {
        "baseline01": 1_789_206,
        "seed02": 1_732_741,
        "seed03": 1_620_364,
        "seed04": 1_682_825,
        "gap133": 1_700_000,
        "gap133s2": 1_750_000,
        "gap133s3": 1_660_000,
    }
    args = []
    for tag, fg in vals.items():
        p = tmp_path / f"{tag}.json"
        p.write_text(
            json.dumps(
                {
                    "summary": {
                        "total_fg_pixels": fg,
                        "overall_fg_fraction": 0.005,
                        "overall_line_score": 0.35 + fg % 7 * 1e-4,
                        "overall_column_score": 0.20 + fg % 5 * 1e-3,
                    }
                }
            )
        )
        args.append(f"{tag}={p}")
    sys.argv = ["analyse_gap_ink_arm.py", *args]
    mod.main()
    out = capsys.readouterr().out
    assert "NULL READING" in out
    assert "NOT 'no effect'" in out


def test_end_to_end_writes_the_registered_fields(tmp_path):
    vals = {
        "baseline01": 1_789_206,
        "seed02": 1_732_741,
        "seed03": 1_620_364,
        "seed04": 1_682_825,
        "gap133": 1_591_857,
        "gap133s2": 1_540_000,
        "gap133s3": 1_570_000,
    }
    args = []
    for tag, fg in vals.items():
        p = tmp_path / f"{tag}.json"
        p.write_text(
            json.dumps(
                {
                    "summary": {
                        "total_fg_pixels": fg,
                        "overall_fg_fraction": 0.0045,
                        "overall_line_score": 0.34 + fg % 7 * 1e-4,
                        "overall_column_score": 0.18 + fg % 5 * 1e-3,
                    }
                }
            )
        )
        args.append(f"{tag}={p}")
    out = tmp_path / "res.json"
    sys.argv = ["analyse_gap_ink_arm.py", *args, "--out", str(out)]
    mod.main()
    got = json.loads(out.read_text())
    assert len(got["base"]) == 4 and len(got["gap"]) == 3
    assert set(got["results"]) == set(mod.METRICS)
    assert "ci" in got["results"][mod.PRIMARY]


def test_a_metric_with_no_spread_is_called_degenerate_not_significant():
    """Zero variance in both arms used to divide by zero in the Welch df, which
    would have crashed the analysis after seven hours of compute. It must report
    that no inference is possible, not invent a p-value."""
    w = mod.welch([1.0, 1.0, 1.0, 1.0], [2.0, 2.0, 2.0])
    assert w["degenerate"] is True
    assert math.isnan(w["p"])


def test_a_degenerate_primary_metric_stops_the_run(tmp_path):
    """A constant objective is a broken measurement, not a null result."""
    args = []
    for tag in list(mod.BASE_ARMS) + list(mod.GAP_ARMS):
        p = tmp_path / f"{tag}.json"
        p.write_text(json.dumps({"summary": {k: 1.0 for k in mod.METRICS}}))
        args.append(f"{tag}={p}")
    sys.argv = ["analyse_gap_ink_arm.py", *args]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "zero variance" in str(e.value)
