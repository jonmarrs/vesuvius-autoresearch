"""Input/report validity around the unchanged shared scientific metric formula."""

import numpy as np

from .metrics import segmentation_metrics


def score_prediction(prob, label, mask):
    arrays = [np.asarray(value) for value in (prob, label, mask)]
    for name, array in zip(("probability", "label", "mask"), arrays, strict=True):
        if (
            array.ndim != 2
            or not array.size
            or array.dtype.kind not in "buif"
            or not np.isfinite(array).all()
        ):
            raise ValueError(f"{name} must be a nonempty finite numeric 2D array")
    prob, label, mask = arrays
    if prob.shape != label.shape or prob.shape != mask.shape:
        raise ValueError("probability, label, and mask shapes must match")
    if np.any((prob < 0) | (prob > 1)) or np.any((label < 0) | (label > 1)):
        raise ValueError("probabilities and labels must be between 0 and 1")
    if np.any(mask < 0):
        raise ValueError("mask must be nonnegative")
    card = segmentation_metrics(prob, label, mask)
    if "note" in card:
        raise ValueError(card["note"])
    return card
