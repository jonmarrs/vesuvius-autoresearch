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


def test_trim_is_parsed_from_the_render_log(tmp_path):
    from analyse_resampling_or_distortion import parse_trim

    log = tmp_path / "r.log"
    log.write_text("x\ntrim grid 8266x426 -> 8263x424 (rect c=1+8263 r=0+424)\ny\n")
    assert parse_trim(log) == (1, 0)
    log.write_text("no trim here\n")
    assert parse_trim(log) == (0, 0)


def test_aligned_block_sd_removes_a_pure_offset():
    """A reference and an arm that is the SAME content, trimmed by 1 cell (10 px)
    and shifted 5 px, must read ~0 once aligned -- and clearly >0 if not."""
    import numpy as np
    from analyse_resampling_or_distortion import aligned_block_sd

    rng = np.random.default_rng(0)
    # Ink comes in coherent runs, not independent columns: independent noise would
    # average out over a 2048-px block and hide a misalignment, as real ink does not
    # (a 10 px offset of the real reference masks gives sd 0.013).
    runs = rng.exponential(300.0, 240) * (rng.random(240) < 0.3)
    ref = np.repeat(runs, 50)[:12000]
    off = 15
    arm = ref[off : off + 11000].copy()
    assert aligned_block_sd(ref, arm, off, block=2048) < 1e-12
    assert aligned_block_sd(ref, arm, 0, block=2048) > 0.005
