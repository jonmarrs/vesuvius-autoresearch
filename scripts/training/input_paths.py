"""Local label paths shared by training and read-only setup inspection."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.training.config import ExperimentConfig


# The label file validation (and training) reads: the first of these beside
# the volume.
VALIDATION_LABEL_FILES = (
    "inklabels_refined.png",
    "inklabels_filled.png",
    "inklabels.png",
)


def validation_label_path(val_uri: str) -> str:
    """The label file read for this volume (inklabels.png when none exists)."""
    parent = os.path.dirname(val_uri.rstrip("/"))
    for name in VALIDATION_LABEL_FILES:
        path = os.path.join(parent, name)
        if os.path.exists(path):
            return path
    return path


def validation_input_paths(val_uri: str) -> dict[str, str]:
    """The files beside the volume that validation reads, by role. The one
    definition build_validation_dataset and the fingerprint both use."""
    parent = os.path.dirname(val_uri.rstrip("/"))
    return {
        "labels": validation_label_path(val_uri),
        "mask": os.path.join(parent, "mask.png"),
        "patches_json": os.path.join(parent, "patches.json"),
    }


def training_label_path(uri: str, config: ExperimentConfig) -> str:
    """The label file training reads for a labeled volume.

    A `<segment>_pseudo.png` in pseudo_label_dir takes precedence over the
    volume's own labels (docs/PSEUDO_LABEL_HANDOFF.md). Its uncertain band (PNG
    128) is a target like any other unless use_confidence_weight down-weights it,
    so a pseudo-label from pseudo_label_dir without it is refused rather than
    trained as ink 128/255.
    """
    if config.pseudo_label_dir:
        segment = os.path.basename(os.path.dirname(uri.rstrip("/")))
        pseudo = os.path.join(config.pseudo_label_dir, f"{segment}_pseudo.png")
        if os.path.exists(pseudo):
            if not getattr(config, "use_confidence_weight", False):
                raise ValueError(
                    f"{pseudo} replaces the labels of {uri}, but "
                    "use_confidence_weight is off, so its uncertain band would be "
                    "trained as ink probability 128/255 (docs/PSEUDO_LABEL_HANDOFF.md)"
                )
            return pseudo
    path = validation_label_path(uri)  # the same order as validation
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"no label file for training volume {uri} (looked for "
            f"{', '.join(VALIDATION_LABEL_FILES)} beside it)"
        )
    return path
