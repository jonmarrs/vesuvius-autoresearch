"""scripts/neural_tracer_refit_presence_screen.py and its record: the AUC and pooling are exact, the on-reference test
reproduced ScrollGT's baseline rows on every cube, and finding 104's report quotes the record."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_refit_presence_screen as ps  # noqa: E402

E = json.loads(
    (
        ROOT / "reports/evidence/neural_tracer_refit_presence_screen_2026-11-03.json"
    ).read_text()
)
REPORT = " ".join((ROOT / "reports/neural_tracer_refit_retry.md").read_text().split())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
P = E["per_cube"]


def test_auc_counts_is_the_mann_whitney_probability():
    rng = np.random.default_rng(0)
    pos = rng.integers(0, 256, 700).astype(np.uint8)
    neg = rng.integers(0, 180, 900).astype(np.uint8)
    brute = ((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (pos.size * neg.size)  # fmt: skip
    assert ps.auc_counts(pos, neg) == pytest.approx(brute, abs=1e-12)
    assert ps.auc_counts(np.full(3, 9, np.uint8), np.full(4, 9, np.uint8)) == 0.5
    assert ps.auc_counts(np.array([], np.uint8), neg) is None


def test_pooled_is_the_sum_of_the_cubes():
    assert ps.pooled(P) == json.loads(json.dumps(E["pooled"]), object_hook=lambda d: {int(k) if k.isdigit() else k: v for k, v in d.items()})  # fmt: skip
    for c, r in P.items():
        assert sum(r["hist_added_on"]) == r["added_on"]
        assert sum(r["hist_added_on"]) + sum(r["hist_added_off"]) == r["added"]
        on, off = np.repeat(np.arange(256), r["hist_added_on"]), np.repeat(np.arange(256), r["hist_added_off"])  # fmt: skip
        assert ps.auc_counts(on, off) == pytest.approx(r["auc_added"], abs=1e-12)


def test_the_screen_covers_the_held_out_cubes_and_reproduces_scrollgt():
    assert sorted(P) == sorted(ps.rr.HELD)
    assert all(r["reproduces_baseline_row"] for r in P.values())
    assert E["tolerance"] == 2.0 and "not registered, decides nothing" in E["after"]


def test_the_report_quotes_the_record():
    pool = E["pooled"]
    auc = [r["auc_added"] for r in P.values()]
    base_auc = [r["auc_base"] for r in P.values()]
    assert (
        "## After the result: presence would not make the retry precise (not registered; decides nothing)"
        in REPORT
    )
    assert (
        f"{pool['added']:,} voxels the refit runs label and the baseline runs do not"
        in REPORT
    )
    assert f"{pool['added_on_share']:.3f} of them on the reference" in REPORT
    assert (
        f"a median AUC of {statistics.median(auc):.2f} ({min(auc):.2f}–{max(auc):.2f} by cube)"
        in REPORT
    )
    assert f"the baseline's own voxels, {statistics.median(base_auc):.2f}" in REPORT
    k = pool["kept_at"]["192"]
    assert (
        f"keeps {k['on']:.2f} of the added voxels on the reference and {k['off']:.2f} of those off it"
        in REPORT
    )
    assert (
        f"{k['on_share']:.2f} of what it keeps is on the reference, below the baseline's {pool['base_precision']:.3f}"
        in REPORT
    )
    k = pool["kept_at"]["240"]
    assert (
        f"Only at 240 ({k['on_share']:.2f}) does it pass the baseline, keeping {k['on']:.2f} of the on-reference additions"
        in REPORT
    )
    assert pool["kept_at"]["224"]["on_share"] < pool["base_precision"] < k["on_share"]
    assert (
        f"additions with a median AUC of {statistics.median(auc):.2f}, no better than on the stock trace"
        in STRATEGY
    )
