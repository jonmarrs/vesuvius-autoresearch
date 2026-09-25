"""The tier table is load-bearing: a misfiled arm silently corrupts a correlation.

These tests exist because that already happened. `anchor10cov` ran on current
villa, `correlate_geometry_ink.py` carried its own prefix tuple that did not
mention it, and the `else "pinned"` default absorbed three current-tier fits into
the pinned tier -- moving r from -0.121 to -0.008 and widening the guard bound
the project reports. Nothing failed; the number just changed.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from arm_tiers import TIERS, UnknownArm, classify, tier_of  # noqa: E402


@pytest.mark.parametrize(
    "tag,tier",
    [
        ("baseline01", "pinned"),
        ("seed02", "pinned"),
        ("seed06", "pinned"),
        ("gap133", "pinned"),
        ("gap133s6", "pinned"),
        ("boot090s1", "pinned"),
        ("rand090s3", "pinned"),
        ("nosame_s1", "pinned"),
        ("strip090s2", "pinned"),
        ("curbase_s1", "current"),
        ("curbase_s9", "current"),
        ("nosamecur_s3", "current"),
        ("anchor10cov_pilot", "current"),
        ("anchor10cov_s2", "current"),
        ("anchor10cov_s3", "current"),
    ],
)
def test_known_arms_resolve(tag, tier):
    assert tier_of(tag) == tier


def test_the_regression_anchor10cov_is_current_not_pinned():
    """THE bug. Its registration says 'Current villa, 30,000 steps', and its ink
    (2.72-2.95M) sits with curbase (2.90M), not with pinned baseline01 (1.79M)."""
    for s in ("anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3"):
        assert tier_of(s) == "current"


def test_nosame_and_nosamecur_are_not_confused():
    """Adjacent names, opposite tiers -- longest-prefix matching must hold, and
    a plain `startswith('nosame')` rule would put both in pinned."""
    assert tier_of("nosame_s1") == "pinned"
    assert tier_of("nosamecur_s1") == "current"


def test_unknown_arm_raises_rather_than_defaulting():
    """The defect was a silent default, not a wrong prefix."""
    with pytest.raises(UnknownArm):
        tier_of("some_unregistered_arm_s1")


def test_classify_raises_on_any_unknown_member():
    with pytest.raises(UnknownArm):
        classify(["baseline01", "definitely_not_registered"])


def test_noise_floor_groups_agree_with_the_tier_table():
    """The two encodings of the same fact must not diverge again."""
    import measure_noise_floor as nf

    for tier, groups in nf.TIERS.items():
        for group, arms in groups.items():
            for arm in arms:
                assert tier_of(arm) == tier, f"{group}/{arm} disagrees"


def test_correlation_script_uses_the_shared_table():
    """It must not reintroduce a local prefix tuple."""
    import correlate_geometry_ink as cgi

    assert cgi.tier_of is tier_of
    src = (
        Path(__file__).resolve().parents[1] / "scripts" / "correlate_geometry_ink.py"
    ).read_text()
    # Match the ASSIGNMENT, not the word: the file explains in a comment why the
    # old tuple was removed, and a bare substring test flags its own postmortem.
    assert not re.search(r"^\s*CURRENT_TREE_PREFIXES\s*=", src, re.M), (
        "a local tier list came back; tier membership belongs in arm_tiers.py"
    )


def test_every_tier_name_is_known():
    assert set(TIERS) == {"pinned", "current", "upstream"}


def test_upstream_fits_are_their_own_tier():
    """Fitted on 75c79ac5f (2026-09-24); pooling them with `current` before the
    registered comparison would assume its answer."""
    assert tier_of("upfit_s1") == "upstream"
