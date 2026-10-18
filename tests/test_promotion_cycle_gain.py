"""scripts/promotion_cycle_gain.py: each loop cycle's val_f1 against the incumbent it faced."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import promotion_cycle_gain as pcg  # noqa: E402

LOG = """\
Starting with incumbent val_f1 from best_model.pt: 0.727323
--- DAY SHIFT STARTING AT 07:30:03 ---
Cycle 1: Applying lr_0.001 (Family Weight: 1.0)
Running 15-minute training for lr_0.001...
No improvement. (val_f1: 0.71, best was: 0.727323)
Caught signal 15. Cleaning up...
Starting with incumbent val_f1 from best_model.pt: 0.249348
--- DAY SHIFT STARTING AT 11:51:48 ---
Cycle 1: Sampled duplicate config (lr=0.001). Re-sampling for entropy...

Cycle 1: Applying a (Family Weight: 1.0)
Running 15-minute training for a...
No improvement. (val_f1: 0.264348, best was: 0.249348)
Cycle 2: Applying b (Family Weight: 1.0)
Running 60-minute training for b...
Cycle 2 timed out. Process group stopped.
CYCLE CRASHED (killed at the 3900 s timeout). Reverting but keeping family weight.
Cycle 3: Applying c (Family Weight: 1.0)
Running 15-minute training for c...
IMPROVEMENT FOUND! (val_f1: 0.2693480412) Committing config.
Cycle 4: Applying d (Family Weight: 1.0)
Running 15-minute training for d...
No improvement. (val_f1: 0.268348, best was: 0.269348)
Cycle 5: Applying e (Family Weight: 1.0)
Running 60-minute training for e...
No improvement. (val_f1: 0.272348, best was: 0.269348)
Cycle 6: Applying f (Family Weight: 1.0)
Running 15-minute training for f...
IMPROVEMENT FOUND! (val_f1: 0.28) Committing config.
Cycle 7: Applying g (Family Weight: 1.0)
Running 15-minute training for g...
IMPROVEMENT FOUND! (val_f1: 0.2905) Committing config.
Cycle 8: Applying h (Family Weight: 1.0)
Running 15-minute training for h...
No improvement. (val_f1: 0.2995, best was: 0.2905)
"""


def test_each_cycle_with_the_incumbent_it_faced():
    rows = pcg.cycles(LOG, first_incumbent=0.249348)
    got = [
        (r["cycle"], r["minutes"], r["val_f1"], r["incumbent"], r["outcome"])
        for r in rows
    ]
    assert got == [
        ("a", 15, 0.264348, 0.249348, "kept_incumbent"),
        ("b", 60, None, 0.249348, "crashed"),
        ("c", 15, 0.2693480412, 0.249348, "promoted"),
        (
            "d",
            15,
            0.268348,
            0.269348,
            "kept_incumbent",
        ),  # "best was", as the loop rounds it
        ("e", 60, 0.272348, 0.269348, "kept_incumbent"),
        ("f", 15, 0.28, 0.269348, "promoted"),
        ("g", 15, 0.2905, 0.28, "promoted"),  # faces the promotion before it
        ("h", 15, 0.2995, 0.2905, "kept_incumbent"),
    ]


def test_cycles_before_the_first_incumbent_are_left_out():
    assert pcg.cycles(LOG, first_incumbent=0.727323)[0]["cycle"] == "lr_0.001"
    with pytest.raises(ValueError):
        pcg.cycles(LOG, first_incumbent=0.5)


def test_segments_by_incumbent():
    segs = pcg.segments(
        pcg.cycles(LOG, first_incumbent=0.249348), tolerances=(0.01, 0.03)
    )
    first, second, third, fourth = segs
    assert (
        first["incumbent"],
        first["scored"],
        first["crashed"],
        first["promoted"],
    ) == (0.249348, 2, 1, 1)
    assert first["mean_gain"] == pytest.approx(0.0175, abs=1e-6)
    assert first["clear"] == {"0.01": 2, "0.03": 0}
    assert (second["incumbent"], second["scored"], second["promoted"]) == (
        0.269348,
        3,
        1,
    )
    assert second["mean_gain"] == pytest.approx((-0.001 + 0.003 + 0.010652) / 3)
    assert second["sd_gain"] == pytest.approx(0.0059206, abs=1e-6)
    assert second["clear"] == {"0.01": 1, "0.03": 0}
    assert (third["incumbent"], third["scored"], third["sd_gain"]) == (0.28, 1, None)
    assert fourth["clear"] == {"0.01": 0, "0.03": 0}  # a 0.009 gain clears neither
