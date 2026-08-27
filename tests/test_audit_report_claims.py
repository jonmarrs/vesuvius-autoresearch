"""Tests for the report-versus-artifact number audit.

An auditor that flags nothing is indistinguishable from a clean report, and one
that flags everything gets ignored. Both failure modes are pinned here, along
with the count, so that a future drift shows up as a rising number rather than
as silence.
"""

import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import audit_report_claims as mod  # noqa: E402
from conftest import restore_cuda_env  # noqa: E402

restore_cuda_env()  # do not leave the mask for other test modules

EXPECTED_RESIDUAL_FLAGS = 5


def test_it_matches_a_number_the_artifact_contains():
    """The basic capability. A number present verbatim must not be flagged."""
    strings, values = {"0.846", "23.59"}, {0.846, 23.59}
    assert mod.appears("0.846", strings, values)
    assert mod.appears("23.59", strings, values)


def test_it_tolerates_the_report_rounding_the_artifact():
    """23.6 quoting an artifact's 23.59 is correct quotation, not drift."""
    assert mod.appears("23.6", {"23.59"}, {23.59})


def test_it_does_not_tolerate_the_report_inventing_precision():
    """The asymmetry that matters. An artifact saying 23.6 cannot support a report
    saying 23.59: the extra digit came from somewhere else."""
    assert not mod.appears("23.59", {"23.6"}, {23.6})


def test_it_flags_a_number_the_artifact_does_not_have():
    """Without this the auditor could be a function that always returns True."""
    assert not mod.appears("77", {"49", "47", "46"}, {49.0, 47.0, 46.0})


def test_it_understands_percent_versus_fraction():
    """A report writing 21.7% where the artifact prints 0.217 is quoting, not
    drifting, and flagging it would train the reader to ignore the output."""
    assert mod.appears("21.7", {"0.217"}, {0.217})


def test_the_residual_count_has_not_risen():
    """The regression guard. Five flags are expected and each is annotated in the
    report where it appears; a sixth means either a new unsourced number or a new
    class of false positive, and both are worth a look."""
    findings, checked = mod.audit()
    assert checked > 40, "the auditor stopped finding numbers to check"
    assert len(findings) <= EXPECTED_RESIDUAL_FLAGS, (
        f"{len(findings)} flags, expected at most {EXPECTED_RESIDUAL_FLAGS}: "
        + ", ".join(f"{n} in {a}" for a, n, _ in findings)
    )


def test_it_notices_a_missing_artifact():
    """A citation to a file that does not exist is the loudest possible drift."""
    strings, values = mod.artifact_numbers("/nonexistent/artifact.txt")
    assert strings is None and values is None
