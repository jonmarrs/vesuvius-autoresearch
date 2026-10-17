"""reports/noise_probe_v3_2026-10-16.md quotes its JSON and train.py's promotion rule correctly."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/noise_probe_v3_2026-10-16.md").read_text()
PROBE = json.loads((ROOT / "reports/noise_probe_v3_2026-10-16.json").read_text())
# best_model.pt's stored val_f1 after `reevaluate_best_model.py --update-stored` under v3 (2026-10-16).
INCUMBENT = 0.249348


# The report records the rule as it stood when the probe ran; the owner lowered
# F1_NOISE_TOLERANCE to 0.01 on 2026-10-17 (tests/test_f1_improvement_criterion.py).
TOLERANCE_AT_PROBE = 0.03


def _f1s() -> list[float]:
    return [run["metrics"]["val_f1"] for run in PROBE["runs"]]


def test_the_probe_is_complete_under_v3_and_uncalibrated():
    assert PROBE["status"] == "COMPLETE" and PROBE["tolerance_calibrated"] is False
    assert PROBE["protocol"] == "seeded-sample-400-v3+z1-27"
    assert len(PROBE["runs"]) == 4 and all(
        r["status"] == "COMPLETE" for r in PROBE["runs"]
    )


def test_summary_line_matches_the_json():
    f1 = _f1s()
    spread = PROBE["f1_spread"]
    assert math.isclose(spread["mean"], statistics.mean(f1))
    assert math.isclose(spread["sample_std"], statistics.stdev(f1))
    assert (
        f"mean {spread['mean']:.4f}, sample SD {spread['sample_std']:.4f}, "
        f"range {spread['range']:.4f}" in REPORT
    )


def test_each_trial_row_matches_the_json():
    for run in PROBE["runs"]:
        m = run["metrics"]
        row = (
            f"| {run['run']} | {run['train_sampling_seed']} | {m['val_f1']:.4f} | "
            f"{m['roc_auc']:.4f} | {m['ap_prevalence_lift']:.3f} |"
        )
        assert row in REPORT, row


def test_every_trial_beats_the_incumbent_and_none_clears_the_promotion_bar():
    f1 = _f1s()
    tol = TOLERANCE_AT_PROBE
    assert all(v > INCUMBENT for v in f1)
    assert not any(v > INCUMBENT + tol for v in f1)
    assert f"above {INCUMBENT + tol:.4f}" in REPORT
    assert all(r["metrics"]["ap_prevalence_lift"] > 1.02 for r in PROBE["runs"])
    gains = [v - INCUMBENT for v in f1]
    sd = PROBE["f1_spread"]["sample_std"]
    assert f"by {min(gains):.3f} to {max(gains):.3f}" in REPORT
    assert f"{min(gains) / sd:.1f} to {max(gains) / sd:.1f} SDs" in REPORT


def test_rederived_tolerance_is_the_july_formula_on_this_sigma():
    sd = PROBE["f1_spread"]["sample_std"]
    assert f"gives {1.645 * math.sqrt(2) * sd:.4f}" in REPORT


def test_the_decision_is_recorded():
    import train

    tol = train.F1_NOISE_TOLERANCE
    assert tol == 0.01
    assert all(v > INCUMBENT + tol for v in _f1s())
    assert f"set `F1_NOISE_TOLERANCE` to {tol}" in REPORT
    assert f"above {INCUMBENT + tol:.4f}" in REPORT
