"""The same-fit re-layout summary: layout-only noise on total_fg_pixels."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from measure_same_fit_relayout import summarise  # noqa: E402


def test_identical_pairs_have_no_spread_and_zero_share():
    pairs = {f"s{i}": {"stock": 1000 + i, "det": 1000 + i} for i in range(4)}
    r = summarise(pairs)
    assert r["sd_ln_ratio"] == 0 and r["layout_share_of_fit_variance"] == 0


def test_sd_is_of_the_log_ratio_and_the_band_is_applied():
    pairs = {
        "a": {"stock": 100, "det": 103},
        "b": {"stock": 100, "det": 97},
        "c": {"stock": 100, "det": 102},
        "d": {"stock": 100, "det": 98},
    }
    r = summarise(pairs)
    ln = [math.log(1.03), math.log(0.97), math.log(1.02), math.log(0.98)]
    m = sum(ln) / 4
    sd = math.sqrt(sum((x - m) ** 2 for x in ln) / 3)
    assert abs(r["sd_ln_ratio"] - sd) < 1e-12
    assert r["in_band"] is (0.015 <= sd <= 0.045)
    lo, hi = r["sd_ci95"]
    assert lo < sd < hi
