"""Tests for the probe closing the report's two untested cells.

The load-bearing claims are (a) that villa's verdict never distinguishes the two
arms under real scatter at real scale, and (b) that acceptance of a displacement
is PERIODIC -- governed by distance from the nearest integer winding, not by the
size of the displacement. Both are asserted against the real metric, not mocked.
"""

import os
import re
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import pytest  # noqa: E402
from probe_spiral_satisfaction_untested_cells import (  # noqa: E402
    DR,
    REAL_DR,
    format_report,
    nearest_winding_offset,
    reference_failures,
    run_cell,
    run_cell1_absolute,
    run_cell1_fractional,
    run_cell2,
    verdict_disagreements,
)


def test_anchors_to_the_pinned_zero_delta():
    """At dr=100, ratio 1.0, no scatter, this harness must reproduce the pinned
    exact-zero result of the original probe. If it does not, the new harness is
    measuring something different and nothing else here can be trusted."""
    row = run_cell(DR, 1.0, scatter_voxels=0.0)
    assert row["delta_combined"] == pytest.approx(0.0, abs=1e-9)
    assert row["ref_combined"] == pytest.approx(1.0, abs=1e-9)


def test_scatter_is_applied_in_absolute_voxels():
    """A scatter of 6.0 voxels must perturb the patch enough to move the score
    off 1.0 at both scales -- otherwise the 'absolute voxels' parameterization is
    not doing what it claims and Cell 1b compares nothing."""
    for dr in (REAL_DR, DR):
        clean = run_cell(dr, 1.0, scatter_voxels=0.0)
        noisy = run_cell(dr, 1.0, scatter_voxels=6.0)
        assert clean["ref_combined"] == pytest.approx(1.0, abs=1e-9)
        assert noisy["ref_combined"] < 1.0


def test_reference_never_fails_villas_verdict_under_real_scatter():
    """Cell 1's question, from the report: does real scatter at real scale push
    the CORRECTLY PLACED patch below villa's 0.95 threshold? If it ever did, the
    practical question would change entirely."""
    rows = run_cell1_absolute() + run_cell1_fractional()
    assert reference_failures(rows) == []


def test_verdict_never_distinguishes_the_arms_under_scatter():
    """Cell 1's finding: across every scatter level at both scales, villa's
    patch verdict is identical for the correctly placed and displaced patch."""
    assert verdict_disagreements(run_cell1_absolute()) == []


def test_acceptance_is_periodic_not_magnitude_bounded():
    """Cell 2's finding, stated as the falsifiable form: a displacement of 23.8
    windings is ACCEPTED (it lands 0.1994 from an integer) while a displacement
    of only 0.5 windings is REJECTED. If acceptance were bounded by displacement
    size this would be impossible."""
    far = run_cell(REAL_DR, 23.8006)
    near = run_cell(REAL_DR, 0.5)
    assert nearest_winding_offset(23.8006) < nearest_winding_offset(0.5)
    assert far["disp_verdict"] is True
    assert near["disp_verdict"] is False


def test_acceptance_edge_is_villas_own_radius_tolerance():
    """The acceptance half-width is villa's satisfaction_radius_tolerance (0.45),
    not an arbitrary empirical constant: an offset of 0.44 is accepted and 0.46
    is rejected."""
    assert run_cell(REAL_DR, 0.44)["disp_verdict"] is True
    assert run_cell(REAL_DR, 0.46)["disp_verdict"] is False


def test_every_rejected_ratio_sits_nearer_the_midpoint_than_every_accepted_one():
    """The structural claim: acceptance is a function of offset from the nearest
    winding alone. Were any accepted row to sit further from an integer than any
    rejected row, 'periodic' would be the wrong description."""
    rows = run_cell2()
    accepted = [
        nearest_winding_offset(r["n_windings"]) for r in rows if r["disp_verdict"]
    ]
    rejected = [
        nearest_winding_offset(r["n_windings"]) for r in rows if not r["disp_verdict"]
    ]
    assert accepted and rejected
    assert max(accepted) < min(rejected)


def test_narrative_counts_match_the_rows_they_quote():
    """Drift guard. Every count in the rendered report must be recomputed from
    the rows, not typed. Mirrors the guard added after two hand-typed statistics
    shipped wrong in this series."""
    rows_1a, rows_1b, rows_2 = run_cell1_fractional(), run_cell1_absolute(), run_cell2()
    text = format_report(rows_1a, rows_1b, rows_2)

    m = re.search(r"Verdict disagreements in Cell 1b: (\d+) of (\d+) cells", text)
    assert m and int(m.group(1)) == len(verdict_disagreements(rows_1b))
    assert int(m.group(2)) == len(rows_1b)

    m = re.search(r"already fails villa's verdict: (\d+) of (\d+)", text)
    assert m and int(m.group(1)) == len(reference_failures(rows_1b))

    m = re.search(r"accepted in (\d+) of (\d+) ratio cells; rejected in (\d+)", text)
    assert m
    assert int(m.group(1)) == len([r for r in rows_2 if r["disp_verdict"]])
    assert int(m.group(2)) == len(rows_2)
    assert int(m.group(3)) == len([r for r in rows_2 if not r["disp_verdict"]])
