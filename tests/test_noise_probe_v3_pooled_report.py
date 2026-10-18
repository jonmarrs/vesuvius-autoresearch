"""reports/noise_probe_v3_pooled_2026-10-17.md quotes the registered analysis
(scripts/noise_probe_pooled.py) of its two committed probe batches correctly."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import noise_probe_pooled as npp  # noqa: E402

REPORT = " ".join(
    (ROOT / "reports/noise_probe_v3_pooled_2026-10-17.md").read_text().split()
)  # line wraps
RESULT = json.loads(
    (ROOT / "reports/noise_probe_v3_pooled_2026-10-17.json").read_text()
)
SOURCES = [
    "reports/noise_probe_v3_2026-10-16.json",
    "reports/noise_probe_v3_2026-10-17.json",
]
PROBES = [json.loads((ROOT / p).read_text()) for p in SOURCES]
# best_model.pt's stored val_f1 under v3 (tests/test_noise_probe_v3_report.py).
INCUMBENT = 0.249348


def _f1s() -> list[float]:
    return [v for b in RESULT["batches"] for v in b["val_f1"]]


def _hashes(probe) -> dict:
    """input_hashes keyed by repo path: batch 1 ran from a worktree."""
    return {
        k.split("/vesuvius-autoresearch/")[-1].split(
            "/worktrees/noise-probe-short-tmpdir/"
        )[-1]: v
        for k, v in probe["input_hashes"].items()
    }


def test_the_json_is_the_registered_analysis_of_the_committed_batches():
    assert RESULT["sources"] == SOURCES
    assert RESULT["incumbent"] == INCUMBENT and RESULT["tolerance"] == 0.01
    npp.poolable(PROBES)
    rerun = npp.analyse([npp.completed(p) for p in PROBES], INCUMBENT, 0.01)
    rerun["sources"] = SOURCES
    assert rerun == RESULT


def test_batch_two_is_complete_under_v3_with_batch_ones_inputs():
    new = PROBES[1]
    assert new["status"] == "COMPLETE" and new["tolerance_calibrated"] is False
    assert new["protocol"] == npp.PROTOCOL
    assert len(new["runs"]) == 4 and all(r["status"] == "COMPLETE" for r in new["runs"])
    old, cur = _hashes(PROBES[0]), _hashes(new)
    assert sorted(old) == sorted(cur)
    assert [k for k in old if old[k] != cur[k]] == ["scripts/training/train.py"]
    train = "scripts/training/train.py"
    assert f"`{old[train][:8]}` → `{cur[train][:8]}`" in REPORT


def test_each_batch_two_row_matches_the_json():
    for run in PROBES[1]["runs"]:
        m = run["metrics"]
        row = (
            f"| {run['run']} | {run['train_sampling_seed']} | {m['val_f1']:.4f} | "
            f"{m['roc_auc']:.4f} | {m['ap_prevalence_lift']:.3f} |"
        )
        assert row in REPORT, row


def test_the_pooled_summary():
    p = RESULT["pooled"]
    assert p["n"] == 8 and p["df"] == 7
    lo, hi = p["interval"]
    assert (
        f"mean {p['mean']:.4f}, SD {p['sd']:.4f} (df 7), 95% interval {lo:.4f}–{hi:.4f}"
        in REPORT
    )
    assert f"spans a factor of {hi / lo:.1f}" in REPORT


def test_no_shift_so_the_pooled_sd_leads():
    s, w = RESULT["shift"], RESULT["within_batch"]
    assert not s["shifted"] and RESULT["lead"]["estimate"] == "pooled"
    means = [b["mean"] for b in RESULT["batches"]]
    assert f"batch means {means[0]:.4f} and {means[1]:.4f}" in REPORT
    assert (
        f"difference {s['difference']:.4f} against a Welch SE of {s['se']:.4f}"
        in REPORT
    )
    lo, hi = w["interval"]
    assert f"{w['sd']:.4f} ({lo:.4f}–{hi:.4f}, df 6)" in REPORT


def test_the_false_promotion_rates():
    fp = RESULT["false_promotion"]
    assert fp["point"] < 0.05  # the registered "say so first" clause does not apply
    assert fp["high"] > 0.05
    assert (
        f"{100 * fp['point']:.2f}% at the point estimate, {100 * fp['low']:.3f}% at the "
        f"interval's low end and {100 * fp['high']:.1f}% at its high end"
    ) in REPORT


def test_the_july_tolerance():
    j = RESULT["july_tolerance"]
    assert f"{j['point']:.4f} ({j['low']:.4f}–{j['high']:.4f})" in REPORT
    assert j["point"] < 0.01 < j["high"]


def test_all_three_predictions_held():
    assert len(RESULT["predictions"]) == 3 and all(RESULT["predictions"].values())
    assert "all three held" in REPORT
    b1, b2 = RESULT["batches"]
    band = f"{b1['mean'] - 3 * b1['sd']:.4f}–{b1['mean'] + 3 * b1['sd']:.4f}"
    assert f"band {band}" in REPORT
    assert f"batch 2 spans {min(b2['val_f1']):.4f}–{max(b2['val_f1']):.4f}" in REPORT
    lifts = [r["metrics"]["ap_prevalence_lift"] for r in PROBES[1]["runs"]]
    assert f"AP lifts {min(lifts):.3f}–{max(lifts):.3f}" in REPORT


def test_every_trial_clears_the_current_incumbent():
    f1, sd = _f1s(), RESULT["pooled"]["sd"]
    assert all(v > INCUMBENT + 0.01 for v in f1)
    assert all(
        r["metrics"]["ap_prevalence_lift"] > npp.LIFT_GATE
        for p in PROBES
        for r in p["runs"]
    )
    assert "8 of 8 would be promoted" in REPORT
    gaps = [v - INCUMBENT for v in f1]
    assert f"by {min(gaps):.3f} to {max(gaps):.3f}" in REPORT
    gap = statistics.mean(f1) - INCUMBENT
    assert f"mean {gap:.4f}, {gap / sd:.1f} pooled SDs" in REPORT


def test_the_loop_cycles_quoted_from_106():
    text = " ".join(
        w for w in (ROOT / "scripts/training/train.py").read_text().split() if w != "#"
    )
    assert "none of the 34 loop cycles scored under v3 (10-16/17) promoted" in text
    assert "each beat the incumbent by 0.011-0.022" in text
    assert "all 34 loop cycles scored under v3" in REPORT
