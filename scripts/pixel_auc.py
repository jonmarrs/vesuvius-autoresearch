"""Pooled pixel-level AUC over many per-patch probability/label arrays. Kept in
its own module (no `train` import) so train.py can import it without the circular
dependency that `measure_ink_auc.py` would introduce."""

import numpy as np
from sklearn.metrics import roc_auc_score


def pooled_pixel_auc(prob_arrays, label_arrays):
    """prob_arrays / label_arrays: lists of 1-D arrays (per-patch flattened
    sigmoid probabilities and binary labels). Concatenates all pixels and returns
    a single roc_auc_score; returns 0.5 if only one class is present."""
    p = np.concatenate([np.asarray(a).ravel() for a in prob_arrays])
    y = np.concatenate([np.asarray(a).ravel() for a in label_arrays])
    y = (y > 0.5).astype(int)
    if y.min() == y.max():
        return 0.5
    return float(roc_auc_score(y, p))
