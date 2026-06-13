import numpy as np

from scripts.pseudo_label_quality_report import score_pseudo


def test_score_pseudo_perfect_labels():
    true = np.array([[1, 0, 1, 0]], dtype=np.uint8)
    pseudo = np.array([[255, 0, 255, 0]], dtype=np.uint8)
    r = score_pseudo(pseudo, true)
    assert r["coverage"] == 1.0
    assert r["precision"] == 1.0 and r["recall"] == 1.0


def test_score_pseudo_ignores_uncertain_band():
    true = np.array([[1, 1, 0, 0]], dtype=np.uint8)
    pseudo = np.array([[255, 128, 128, 0]], dtype=np.uint8)
    r = score_pseudo(pseudo, true)
    assert r["coverage"] == 0.5
    assert r["precision"] == 1.0 and r["recall"] == 1.0
