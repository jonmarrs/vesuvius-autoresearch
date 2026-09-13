"""Tests for the anchor-ablation decision rule, written before any arm exists.

Two rules carry the weight and both are pinned here rather than left to prose:

* **ink alone decides the verdict.** Geometry is interpretable in this study
  (unlike the same-winding one) and that makes it MORE tempting, not less, to let
  a geometry move rescue a null ink result.
* **an arm excluded by the winding-identity gate is reported**, because the
  quiet version of that exclusion is indistinguishable from dropping an
  inconvenient arm.
"""

import inspect
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_anchor_ablation as mod  # noqa: E402
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
                        "overall_fg_fraction": fg / 4.1e8,
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


def test_the_registered_arms_and_anchor_counts_are_constants():
    # NOT "anchor10_s*": that names the superseded z-collapsed dataset.
    assert mod.ABLATED_ARMS == ("anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3")
    assert all("cov" in a for a in mod.ABLATED_ARMS)
    assert mod.BASELINE_ARMS == ("curbase_s1", "curbase_s2", "curbase_s3")
    # 50, not 59: nine anchors lie outside the fit's z-ROI and are never used.
    assert (mod.N_ANCHORS_FULL, mod.N_ANCHORS_ABLATED) == (50, 10)


def test_it_uses_the_CURRENT_tier_noise_not_the_pinned_constant():
    """The pinned 0.0421 was inherited by four earlier scripts and is wrong for
    current code -- it would overstate the MDE by ~4x."""
    assert mod.CURRENT_CV == 0.0125
    assert mod.mde(3, 3) == pytest.approx(0.029, abs=0.002)


def test_geometry_is_not_an_input_to_the_verdict_signature():
    """It is accepted so it can be printed, and must not reach the decision."""
    assert set(inspect.signature(mod.verdict).parameters) == {"ink", "geom"}


def test_a_geometry_gain_cannot_rescue_a_null_ink_result():
    ink = welch([2.88e6, 2.90e6, 2.86e6], [2.89e6, 2.87e6, 2.91e6])
    geom = welch([0.8490, 0.8492, 0.8488], [0.8700, 0.8698, 0.8702])
    assert mod.verdict(ink, geom)[0] == "NULL"


def test_an_ink_loss_reads_as_anchors_mattering():
    ink = welch([2.90e6, 2.91e6, 2.89e6], [2.50e6, 2.51e6, 2.49e6])
    assert mod.verdict(ink, None)[0] == "ANCHORS MATTER FOR READING"


def test_an_ink_gain_is_reported_with_a_placement_caveat():
    ink = welch([2.50e6, 2.51e6, 2.49e6], [2.90e6, 2.91e6, 2.89e6])
    tag, why = mod.verdict(ink, None)
    assert tag == "FEWER ANCHORS READ BETTER"
    assert "better" in why and "placed" in why


def test_the_null_text_says_bounded_not_zero():
    ink = welch([2.88e6, 2.90e6, 2.86e6], [2.89e6, 2.87e6, 2.91e6])
    assert "Bounded, not zero" in mod.verdict(ink, None)[1]


def test_relative_ci_reproduces_the_hand_computed_same_winding_interval():
    """Positive control against a number published from a different script.

    reports/decoupling_does_not_cleanly_reproduce.md quotes +0.28%, 95% CI
    [-2.56%, +3.13%], Welch df 4.0, computed by hand for the same-winding arms.
    An instrument that cannot reproduce a known interval measures nothing.
    """
    ci = mod.relative_ci([2904520, 2901177, 2841071], [2893440, 2925553, 2852335])
    assert ci["rel"] == pytest.approx(0.0028, abs=0.0002)
    assert ci["lo"] == pytest.approx(-0.0256, abs=0.0005)
    assert ci["hi"] == pytest.approx(0.0313, abs=0.0005)
    assert ci["df"] == pytest.approx(4.0, abs=0.2)


def test_the_ci_brackets_the_point_estimate():
    ci = mod.relative_ci([100.0, 102.0, 98.0], [90.0, 92.0, 88.0])
    assert ci["lo"] < ci["rel"] < ci["hi"]
    assert ci["rel"] < 0, "ablated lower than base must give a negative relative effect"


def test_the_ci_is_None_rather_than_wrong_when_it_cannot_be_computed():
    assert mod.relative_ci([1.0], [2.0]) is None  # too few
    assert mod.relative_ci([5.0, 5.0, 5.0], [5.0, 5.0, 5.0]) is None  # zero spread


def test_adding_the_ci_did_not_change_what_decides_the_verdict():
    """The CI is reporting. If it ever becomes an input to verdict(), the
    registered rule -- ink decides -- has been changed after the fact."""
    assert set(inspect.signature(mod.verdict).parameters) == {"ink", "geom"}
    src = inspect.getsource(mod.verdict)
    assert "relative_ci" not in src and "ci" not in src.split("def ")[0]


def test_the_sign_convention_is_pinned_WITHOUT_calling_welch():
    """Every other test here builds its input by calling welch(), so if welch's
    sign convention were ever flipped the tests would flip with it and keep
    passing while the verdict inverted. This one states the contract literally.

    welch(base, gap) returns rel_diff = (mean_gap - mean_base) / mean_base, and
    the analysis passes BASELINE as `base` and ABLATED as `gap`. So a NEGATIVE
    rel_diff means the ablated arm -- the one with 10 anchors instead of 50 --
    recovered LESS ink, which is anchors mattering.
    """
    less_ink = {
        "mean_base": 2.88e6,
        "mean_gap": 2.50e6,
        "rel_diff": -0.132,
        "p": 0.001,
        "degenerate": False,
    }
    more_ink = {
        "mean_base": 2.50e6,
        "mean_gap": 2.88e6,
        "rel_diff": +0.152,
        "p": 0.001,
        "degenerate": False,
    }
    assert mod.verdict(less_ink, None)[0] == "ANCHORS MATTER FOR READING"
    assert mod.verdict(more_ink, None)[0] == "FEWER ANCHORS READ BETTER"


def test_welch_still_has_the_convention_this_module_assumes():
    """Guards the other half: if welch changes, the literal test above becomes a
    lie about the real pipeline. Checked against the real function, once."""
    got = welch([100.0, 100.0, 100.0], [90.0, 90.0, 90.0])
    assert got["rel_diff"] < 0, "welch(base, gap) must be (gap - base) / base"


def test_a_partial_sample_is_refused(tmp_path):
    ink = {t: 2.88e6 for t in mod.ABLATED_ARMS[:2]}
    ink.update({t: 2.88e6 for t in mod.BASELINE_ARMS})
    sys.argv = ["x", *_files(tmp_path, ink)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "refused" in str(e.value)


def test_an_unregistered_arm_is_refused(tmp_path):
    ink = {t: 2.88e6 for t in mod.ABLATED_ARMS + mod.BASELINE_ARMS}
    ink["nosamecur_s1"] = 2.89e6
    sys.argv = ["x", *_files(tmp_path, ink)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "nosamecur_s1" in str(e.value)


def test_an_excluded_arm_is_printed_not_hidden(tmp_path, capsys):
    ink = dict(zip(mod.ABLATED_ARMS, [2.89e6, 2.87e6, 2.91e6], strict=False))
    ink.update(dict(zip(mod.BASELINE_ARMS, [2.88e6, 2.90e6, 2.86e6], strict=False)))
    sys.argv = ["x", *_files(tmp_path, ink), "--excluded", "anchor10cov_s4"]
    mod.main()
    out = capsys.readouterr().out
    assert "EXCLUDED" in out and "anchor10cov_s4" in out
    assert "different papyrus" in out


def test_end_to_end_records_the_verdict_and_the_null_reading(tmp_path, capsys):
    ink = dict(zip(mod.ABLATED_ARMS, [2.89e6, 2.87e6, 2.91e6], strict=False))
    ink.update(dict(zip(mod.BASELINE_ARMS, [2.88e6, 2.90e6, 2.86e6], strict=False)))
    geom = dict(zip(mod.ABLATED_ARMS, [0.8500, 0.8498, 0.8502], strict=False))
    geom.update(dict(zip(mod.BASELINE_ARMS, [0.8490, 0.8492, 0.8488], strict=False)))
    out = tmp_path / "res.json"
    sys.argv = ["x", *_files(tmp_path, ink, geom), "--out", str(out)]
    mod.main()
    text = capsys.readouterr().out
    assert "VERDICT: NULL" in text
    assert "interpretable here" in text
    # the null must now carry a real interval, not just advice to compute one
    assert "The data EXCLUDE any ink effect outside" in text
    assert "QUOTE THAT INTERVAL, not the MDE" in text
    assert "Welch df=" in text
    got = json.loads(out.read_text())
    assert got["cv"] == 0.0125 and got["n_anchors"] == [50, 10]
    ci = got["ink_relative_ci"]
    assert ci is not None and ci["lo"] < ci["rel"] < ci["hi"]
