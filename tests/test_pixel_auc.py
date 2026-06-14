import numpy as np

from scripts.pixel_auc import pooled_pixel_auc


def test_perfect_separation():
    probs = [np.array([0.9, 0.8]), np.array([0.1, 0.2])]
    labels = [np.array([1, 1]), np.array([0, 0])]
    assert pooled_pixel_auc(probs, labels) == 1.0


def test_random_is_near_half():
    rng = np.random.RandomState(0)
    probs = [rng.rand(500)]
    labels = [(rng.rand(500) > 0.5).astype(int)]
    assert 0.4 < pooled_pixel_auc(probs, labels) < 0.6


def test_single_class_guard_returns_half():
    probs = [np.array([0.9, 0.1])]
    labels = [np.array([1, 1])]
    assert pooled_pixel_auc(probs, labels) == 0.5
