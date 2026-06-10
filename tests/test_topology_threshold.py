import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

import train
from train import TOPOLOGY_THRESHOLD_CANDIDATES, select_topology_threshold


def test_selects_interior_peak_threshold(monkeypatch):
    # Fake centerline_dice peaks when half the pixels survive binarization, so
    # the selector must find an interior threshold, not just the lowest one.
    def cd_peaks_at_half(gt, pred, **kw):
        frac = float(np.asarray(pred).mean())
        return {"centerline_dice": 1.0 - abs(frac - 0.5)}

    monkeypatch.setattr(train, "compute_centerline_dice", cd_peaks_at_half)
    # Per patch: thr 0.05 keeps 4/4 (frac 1.0), thr 0.15 keeps 2/4 (frac 0.5),
    # thr 0.25 keeps 0/4 (frac 0.0). cd: 0.5, 1.0, 0.5 -> argmax at 0.15.
    probs = [torch.tensor([[[[0.18, 0.12], [0.16, 0.08]]]]) for _ in range(3)]
    targets = [torch.ones((1, 1, 2, 2)) for _ in range(3)]
    thr, cd = select_topology_threshold(
        probs, targets, candidates=(0.05, 0.15, 0.25), subset_step=1
    )
    assert thr == 0.15
    assert cd == 1.0


def test_fallback_when_all_predictions_empty(monkeypatch):
    monkeypatch.setattr(
        train,
        "compute_centerline_dice",
        lambda *a, **k: {"centerline_dice": float("nan")},
    )
    probs = [torch.zeros((1, 1, 4, 4)) for _ in range(3)]
    targets = [torch.ones((1, 1, 4, 4)) for _ in range(3)]
    thr, cd = select_topology_threshold(probs, targets, fallback=0.42, subset_step=1)
    assert thr == 0.42
    assert cd == 0.0


def test_subset_step_limits_patches_evaluated(monkeypatch):
    seen = {"count": 0}

    def counting_cd(gt, pred, **kw):
        seen["count"] += 1
        return {"centerline_dice": 0.1}

    monkeypatch.setattr(train, "compute_centerline_dice", counting_cd)
    probs = [torch.ones((1, 1, 2, 2)) for _ in range(20)]
    targets = [torch.ones((1, 1, 2, 2)) for _ in range(20)]
    select_topology_threshold(probs, targets, candidates=(0.05,), subset_step=10)
    # 20 patches, step 10 -> indices 0 and 10 -> 2 evaluations for one candidate.
    assert seen["count"] == 2


def test_candidates_cover_low_range():
    # This model's probability mass collapses above ~0.25; the default candidate
    # set must cover that low region where topology is actually achievable.
    assert min(TOPOLOGY_THRESHOLD_CANDIDATES) <= 0.05
    assert any(c <= 0.2 for c in TOPOLOGY_THRESHOLD_CANDIDATES)
