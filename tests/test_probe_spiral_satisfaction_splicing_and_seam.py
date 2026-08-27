"""Tests for the splicing-configuration and theta=0 seam probe.

The load-bearing claims: the blindness holds under the configuration that gates
the output mesh (not only the one that prints), it is not an artifact of avoiding
the branch cut, and the report's unmeasured claim about the verdict-flipping cell
is settled. All asserted against villa's real unmodified function.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""  # CPU-only for the imports below
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import pytest  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REAL_DR,
    REPORTING,
    SPLICING,
    acceptance_edge,
    run_flip_cell_under,
    run_offset_sweep,
    score_with,
    seam_patch,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    build_synthetic_patch,
    displace,
)

restore_cuda_env()  # do not leave the mask for other test modules


def test_whole_winding_blindness_holds_under_both_configurations():
    """The finding must hold under the config that GATES THE MESH, not only the
    one that prints. If it held only under the reporting config it would be a
    curiosity about a log line."""
    for cfg in (REPORTING, SPLICING):
        rows = run_offset_sweep(REAL_DR, cfg)
        zero = next(r for r in rows if r["offset"] == 0.0)
        assert zero["delta"] == pytest.approx(0.0, abs=1e-9)
        assert zero["ref_verdict"] is True
        assert zero["disp_verdict"] is True


def test_the_splicing_configuration_is_strictly_more_permissive():
    """Its acceptance edge must sit further out than the reporting config's, so
    the mesh-gating path rejects a strictly narrower strip around the midpoint."""
    rep_hi, rep_rej = acceptance_edge(run_offset_sweep(REAL_DR, REPORTING))
    spl_hi, spl_rej = acceptance_edge(run_offset_sweep(REAL_DR, SPLICING))
    assert spl_hi > rep_hi
    assert spl_rej > rep_rej


def test_the_seam_patch_actually_crosses_the_branch_cut():
    """Guard on the probe itself: if the seam patch did not straddle theta=0 the
    seam result would be vacuous. Points on both sides of the cut must exist."""
    import torch

    p = seam_patch(REAL_DR)
    thetas = torch.arctan2(p.zyxs[..., 1], p.zyxs[..., 2]) % (2 * torch.pi)
    assert float(thetas.max() - thetas.min()) > 3.0


def test_blindness_is_not_an_artifact_of_avoiding_the_seam():
    """A patch spanning theta=0 exercises the branch-offset unwrap. The whole
    winding delta must still be zero under both configurations."""
    for cfg in (REPORTING, SPLICING):
        ref = seam_patch(REAL_DR)
        moved = displace(ref, REAL_DR, n_windings=1.0)
        assert score_with(moved, REAL_DR, cfg) == pytest.approx(
            score_with(ref, REAL_DR, cfg), abs=1e-9
        )


def test_the_flip_cell_flips_under_reporting_and_not_under_splicing():
    """The report claimed this, but reused the reporting config's fractions
    against the splicing threshold, and flagged that as unmeasured. Measured
    here: under splicing BOTH arms score 165/165, not 159 and 156."""
    rep = run_flip_cell_under(REPORTING)
    spl = run_flip_cell_under(SPLICING)

    assert rep["ref_verdict"] is True and rep["disp_verdict"] is False
    assert rep["ref_quads"] == 159 and rep["disp_quads"] == 156

    assert spl["ref_verdict"] is True and spl["disp_verdict"] is True
    assert spl["ref_quads"] == spl["total"] and spl["disp_quads"] == spl["total"]


def test_reference_patch_is_valid_under_both_configs():
    """Anchor: a correctly placed, unperturbed patch scores 1.0 under both, or
    the harness is not measuring what it claims."""
    ref = build_synthetic_patch(dr=REAL_DR, winding=5)
    for cfg in (REPORTING, SPLICING):
        assert score_with(ref, REAL_DR, cfg) == pytest.approx(1.0, abs=1e-9)
