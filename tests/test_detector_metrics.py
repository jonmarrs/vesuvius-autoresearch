import numpy as np
from vesuvius_autoresearch.detector.metrics import segmentation_metrics


def _label():
    lab = np.zeros((64, 64), np.uint8)
    lab[20:44, 20:44] = 1  # ~14% positive
    return lab


def test_perfect_prediction_scores_f1_and_ap_one():
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = lab.astype(np.float32)
    m = segmentation_metrics(prob, lab, mask)
    assert m["val_f1"] > 0.99
    assert m["average_precision"] > 0.99
    assert m["roc_auc"] > 0.99


def test_chance_prediction_ap_near_prevalence_and_lift_near_one():
    rng = np.random.default_rng(0)
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = rng.random((64, 64)).astype(np.float32)
    m = segmentation_metrics(prob, lab, mask)
    assert abs(m["average_precision"] - m["positive_rate"]) < 0.05
    assert abs(m["ap_prevalence_lift"] - 1.0) < 0.3
    assert 0.4 < m["roc_auc"] < 0.6


def test_paint_everything_is_not_rewarded():
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = np.ones((64, 64), np.float32)  # predict ink everywhere
    m = segmentation_metrics(prob, lab, mask)
    assert m["recall"] > 0.99
    assert m["pred_positive_rate"] > 0.99
    assert abs(m["ap_prevalence_lift"] - 1.0) < 0.3  # collapse not rewarded
    assert m["precision"] < 0.3


def test_degenerate_mask_returns_nan_with_note():
    lab = np.zeros((64, 64), np.uint8)  # no positives
    mask = np.ones((64, 64), bool)
    prob = np.random.default_rng(0).random((64, 64)).astype(np.float32)
    m = segmentation_metrics(prob, lab, mask)
    assert np.isnan(m["val_f1"])
    assert "note" in m


def test_metrics_by_threshold_length():
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = lab.astype(np.float32)
    m = segmentation_metrics(prob, lab, mask, thresholds=np.linspace(0.1, 0.9, 9))
    assert len(m["metrics_by_threshold"]) == 9
