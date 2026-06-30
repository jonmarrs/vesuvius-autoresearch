# tests/test_detector_measure.py
import os

import numpy as np

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.model import DetectorModel
from vesuvius_autoresearch.detector import measure as M
from test_detector_data import _make_fake_fragment


def test_measure_writes_report_and_scores_targets(tmp_path):
    root = str(tmp_path / "scrolls")
    _make_fake_fragment(root, "PHercParis2Fr143", h=320, w=320)
    _make_fake_fragment(root, "20230702185753", h=320, w=320)
    cfg = DetectorConfig(data_root=root, reports_dir=str(tmp_path / "reports"))
    model = DetectorModel(cfg, pred_shape=(320, 320)).eval()
    targets = [("PHercParis2Fr143", "scroll2_same"), ("20230702185753", "scroll1_cross")]
    rows = M.measure(cfg, checkpoint_path=None, targets=targets, model=model)
    assert set(rows) == {"PHercParis2Fr143", "20230702185753"}
    assert "val_f1" in rows["PHercParis2Fr143"]
    assert rows["20230702185753"]["scroll_label"] == "scroll1_cross"
    assert os.path.exists(os.path.join(str(tmp_path / "reports"),
                                       "cross_scroll_measurement.md"))
