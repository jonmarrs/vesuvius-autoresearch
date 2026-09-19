"""Guards on the strip-extent pilot's analysis.

Written before either arm produced a number, so the decision rule could not be
tuned to the data. The rule's thresholds come from
`docs/preregistration/2026-09-19_strip_extent_pilot.md`, which fixed them against a
measured seed-noise floor rather than a guess.
"""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "abp", Path(__file__).resolve().parents[1] / "scripts" / "analyse_bounds_pilot.py"
)
assert SPEC and SPEC.loader
abp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(abp)


def _arm(root: Path, tag: str, area: float) -> None:
    d = root / f"outer_{tag}" / "ink_metric"
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps({"summary": {"total_pixels": area}}))


def test_thresholds_match_the_registration():
    assert (abp.GO, abp.MARGINAL) == (0.15, 0.06)


def test_the_floor_is_the_measured_seed_cv_not_a_guess():
    """0.0199 comes from reports/outer_winding_noise_floor.md."""
    assert abp.SEED_AREA_CV == 0.0199


def test_the_two_radii_bracket_the_default_symmetrically():
    lo, hi = abp.RADIUS["bounds_lo"], abp.RADIUS["bounds_hi"]
    assert lo == 2720 and hi == 3680
    assert abs((3200 - lo) - (hi - 3200)) < 1, (
        "the arms are not symmetric about the default"
    )


@pytest.mark.parametrize(
    "delta,expected",
    [
        (0.30, "GO"),
        (0.15, "GO"),
        (0.149, "MARGINAL"),
        (0.06, "MARGINAL"),
        (0.059, "NO GO"),
        (0.0, "NO GO"),
    ],
)
def test_the_rule_is_applied_at_its_stated_boundaries(delta, expected):
    assert abp.verdict(delta)[0] == expected


def test_a_partial_sample_is_refused_not_reported(tmp_path, monkeypatch):
    """One arm scored must not yield half a verdict."""
    _arm(tmp_path, "bounds_lo", 4.0e8)
    monkeypatch.setattr("sys.argv", ["x", "--spiral-out", str(tmp_path)])
    with pytest.raises(SystemExit) as e:
        abp.main()
    assert "bounds_hi" in str(e.value) and "refused" in str(e.value)


def test_both_arms_scored_gives_a_verdict(tmp_path, monkeypatch, capsys):
    _arm(tmp_path, "bounds_lo", 4.0e8)
    _arm(tmp_path, "bounds_hi", 4.8e8)  # +20% -> GO
    monkeypatch.setattr("sys.argv", ["x", "--spiral-out", str(tmp_path)])
    assert abp.main() == 0
    out = capsys.readouterr().out
    assert "VERDICT: GO" in out
    assert "NOTHING about ink" in out, "the scope disclaimer must survive"
