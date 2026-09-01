from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.model import DetectorModel
from vesuvius_autoresearch.detector.model_resenc import ResEncDetectorModel
from vesuvius_autoresearch.detector.train import build_model


def test_build_model_dispatches_by_architecture():
    assert isinstance(build_model(DetectorConfig(), (64, 64)), DetectorModel)
    assert isinstance(
        build_model(DetectorConfig(architecture="resenc"), (64, 64)),
        ResEncDetectorModel,
    )
