import pytest
from vesuvius_autoresearch.detector.config import DetectorConfig


def test_defaults_are_proven_values():
    cfg = DetectorConfig()
    assert cfg.in_chans == 26
    assert cfg.size == 64
    assert cfg.start_idx == 17 and cfg.end_idx == 43  # 26 slices
    assert cfg.lr == 3e-5
    assert cfg.valid_fragment_id == "PHercParis2Fr143"


def test_default_window_is_compliant():
    DetectorConfig().validate_window()  # must not raise


def test_oversized_lateral_window_raises():
    cfg = DetectorConfig(size=128)
    with pytest.raises(ValueError, match="window"):
        cfg.validate_window()


def test_depth_is_not_window_limited():
    # large in_chans (depth) is allowed; only lateral size is constrained
    DetectorConfig(in_chans=40).validate_window()  # must not raise
