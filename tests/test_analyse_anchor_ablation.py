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
    assert "quote the CI on the observed effect" in text
    got = json.loads(out.read_text())
    assert got["cv"] == 0.0125 and got["n_anchors"] == [50, 10]
