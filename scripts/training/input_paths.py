"""Local label paths shared by training and read-only setup inspection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from vesuvius_autoresearch.core.volume_paths import volume_location

if TYPE_CHECKING:
    from scripts.training.config import ExperimentConfig


# The label file validation (and training) reads: the first of these beside
# the volume.
VALIDATION_LABEL_FILES = (
    "inklabels_refined.png",
    "inklabels_filled.png",
    "inklabels.png",
)


def training_volume_path(uri: str, *, base_dir: str | Path = ".") -> str:
    """Decode a local file URI without following the visible volume's links."""
    if not uri.lower().startswith("file:") or (Path(base_dir) / uri).exists():
        return uri
    path, _ = volume_location(uri, base_dir, resolve_local=False)
    if path is None or not urlsplit(uri).path.startswith("/"):
        raise ValueError("file URI must identify an absolute local path")
    return os.fspath(path)


def validation_label_path(val_uri: str) -> str:
    """The label file read for this volume (inklabels.png when none exists)."""
    parent = os.path.dirname(training_volume_path(val_uri).rstrip("/"))
    for name in VALIDATION_LABEL_FILES:
        path = os.path.join(parent, name)
        if os.path.exists(path):
            return path
    return path


def validation_input_paths(val_uri: str) -> dict[str, str]:
    """The files beside the volume that validation reads, by role. The one
    definition build_validation_dataset and the fingerprint both use."""
    volume = training_volume_path(val_uri)
    parent = os.path.dirname(volume.rstrip("/"))
    return {
        "labels": validation_label_path(volume),
        "mask": os.path.join(parent, "mask.png"),
        "patches_json": os.path.join(parent, "patches.json"),
    }


def training_pseudo_label_path(
    uri: str, directory: str | Path, *, base_dir: str | Path = "."
) -> str:
    volume = training_volume_path(uri, base_dir=base_dir)
    segment = os.path.basename(os.path.dirname(volume.rstrip("/")))
    return os.path.join(directory, f"{segment}_pseudo.png")


def training_label_path(uri: str, config: ExperimentConfig) -> str:
    """The label file training reads for a labeled volume.

    A `<segment>_pseudo.png` in pseudo_label_dir takes precedence over the
    volume's own labels (docs/PSEUDO_LABEL_HANDOFF.md). Its uncertain band (PNG
    128) is a target like any other unless use_confidence_weight excludes it
    from the post-augmentation ink BCE/Dice losses,
    so a pseudo-label from pseudo_label_dir without it is refused rather than
    trained as ink 128/255.
    """
    if config.pseudo_label_dir:
        pseudo = training_pseudo_label_path(uri, config.pseudo_label_dir)
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
