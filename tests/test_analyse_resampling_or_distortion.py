"""The resampling-or-distortion rule, tested before either arm was rendered."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_resampling_or_distortion import HI, LO, REF, verdict  # noqa: E402


def test_bands_are_fractions_of_the_relayout_reference():
    assert REF == 0.135
    assert (LO, HI) == (0.02, 0.07)


def test_verdict_bands():
    assert verdict(0.10)[0] == "RE-SAMPLING SUFFICES"
    assert verdict(0.07)[0] == "RE-SAMPLING SUFFICES"
    assert verdict(0.05)[0] == "BOTH CONTRIBUTE"
    assert verdict(0.02)[0] == "DISTORTION REQUIRED"
    assert verdict(0.0002)[0] == "DISTORTION REQUIRED"
