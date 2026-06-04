import os
import sys

import numpy as np
import pytest
import torch

# Add villa paths
VILLA_SRC = os.path.abspath("villa/segmentation/evaluation")
if VILLA_SRC not in sys.path:
    sys.path.append(VILLA_SRC)


def test_dice_metric():
    from metrics.dice import compute as compute_dice

    label = torch.tensor([[[0, 1], [1, 0]]]).float()
    pred = torch.tensor([[[0.1, 0.9], [0.8, 0.2]]]).float()
    d = compute_dice(label, pred)
    assert 0.0 < d <= 1.0


def test_centerline_dice():
    from metrics.centerline_dice import compute as compute_cd

    # Simple line
    gt = np.zeros((10, 10, 10), dtype=np.uint8)
    gt[5, :, 5] = 1
    pred = np.zeros((10, 10, 10), dtype=np.uint8)
    pred[5, :, 5] = 1
    res = compute_cd(gt, pred, tolerance_radius=1.0)
    assert res["centerline_dice"] > 0.9


def test_connected_components():
    from metrics.connected_components import compute as compute_cc

    gt = np.zeros((10, 10, 10), dtype=np.uint8)
    gt[2, 2, 2] = 1
    gt[8, 8, 8] = 1  # 2 components

    pred = np.zeros((10, 10, 10), dtype=np.uint8)
    pred[2, 2, 2] = 1  # 1 component

    res = compute_cc(gt, pred, num_classes=2, ignore_index=0)
    # diff = abs(2 - 1) = 1
    assert res["connected_components_difference_total"] == 1.0


def test_skeleton_distance(monkeypatch):
    import unittest.mock as mock

    monkeypatch.setattr("metrics.skeleton_distance_length.wandb", mock.Mock())
    try:
        from metrics.skeleton_distance_length import compute as compute_skel_dist

        gt = np.zeros((20, 20, 20), dtype=np.uint8)
        gt[10, 2:18, 10] = 1
        pred = np.zeros((20, 20, 20), dtype=np.uint8)
        pred[10, 2:18, 10] = 1
        res = compute_skel_dist(gt, pred)
        assert res >= 0
    except ImportError:
        pytest.skip("Skeleton distance dependencies missing")
    except Exception as e:
        pytest.fail(f"Skeleton distance failed: {e}")
