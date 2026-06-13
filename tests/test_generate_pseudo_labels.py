import numpy as np

from scripts.generate_pseudo_labels import prob_to_pseudo_png


def test_prob_to_pseudo_three_values():
    prob = np.array([[0.05, 0.5, 0.9]], dtype=np.float32)
    region = np.ones_like(prob, dtype=bool)
    out = prob_to_pseudo_png(prob, region, tau_high=0.65, tau_low=0.15)
    assert out.tolist() == [[0, 128, 255]]


def test_outside_region_is_ignore():
    prob = np.array([[0.9, 0.9]], dtype=np.float32)
    region = np.array([[True, False]])
    out = prob_to_pseudo_png(prob, region, tau_high=0.65, tau_low=0.15)
    assert out.tolist() == [[255, 128]]
