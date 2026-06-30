# tests/test_detector_eval.py
import os

import numpy as np

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector import eval as E


def test_perfect_pred_scores_f1_and_keeps_auc_alias(tmp_path):
    cfg = DetectorConfig(reports_dir=str(tmp_path))
    label = np.zeros((64, 64), np.uint8)
    label[20:40, 20:40] = 1
    mask = np.ones((64, 64), bool)
    prob = label.astype(np.float32)
    card = E.evaluate(prob, label, mask, cfg)
    assert card["val_f1"] > 0.99               # new primary metric
    assert abs(card["pixel_auc"] - 1.0) < 1e-6  # backward-compat alias (= roc_auc)
    assert 0.0 <= card["threshold"] <= 1.0      # backward-compat alias (= best_threshold)
    assert os.path.exists(os.path.join(str(tmp_path), "frag_metrics_by_threshold.csv"))


def test_chance_pred_scores_auc_near_half(tmp_path):
    cfg = DetectorConfig(reports_dir=str(tmp_path))
    rng = np.random.default_rng(0)
    label = (rng.random((64, 64)) > 0.5).astype(np.uint8)
    mask = np.ones((64, 64), bool)
    prob = rng.random((64, 64)).astype(np.float32)
    card = E.evaluate(prob, label, mask, cfg)
    assert 0.4 < card["pixel_auc"] < 0.6
    assert "average_precision" in card and "ap_prevalence_lift" in card
