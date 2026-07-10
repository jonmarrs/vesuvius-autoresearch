import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

from train import pooled_segmentation_metrics


def test_empty_returns_empty_dict():
    assert pooled_segmentation_metrics([], []) == {}


def test_perfect_prediction_scores_high_f1_and_lift():
    # Two 1x1x4x4 patches; label has a clear positive region, prob matches it.
    label = torch.zeros(1, 1, 4, 4)
    label[..., :2, :] = 1.0  # 50% prevalence
    prob = label.clone() * 0.99 + 0.005  # near-perfect, in (0,1)
    seg = pooled_segmentation_metrics([prob, prob], [label, label])
    assert seg["val_f1"] > 0.9
    assert seg["ap_prevalence_lift"] > 1.5
    assert 0.0 <= seg["best_threshold"] <= 1.0


def test_degenerate_all_negative_is_nan():
    label = torch.zeros(1, 1, 4, 4)
    prob = torch.full((1, 1, 4, 4), 0.3)
    seg = pooled_segmentation_metrics([prob], [label])
    assert np.isnan(seg["val_f1"])
