"""Coverage information and publication of one detector prediction artifact."""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vesuvius_autoresearch.core.file_modes import replacement_mode
from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths


@dataclass(frozen=True)
class InferenceResult:
    """Original-size maps: coverage distinguishes an unpredicted zero from a score.

    ``fragment_mask`` is the loaded nonzero fragment mask, not a label mask.
    Coverage does not establish model quality or input/checkpoint provenance.
    """

    probability: np.ndarray
    coverage: np.ndarray
    fragment_mask: np.ndarray

    @property
    def summary(self):
        valid = int(np.count_nonzero(self.fragment_mask))
        predicted = int(np.count_nonzero(self.coverage & self.fragment_mask))
        return {
            "valid_pixels": valid,
            "predicted_pixels": predicted,
            "uncovered_pixels": valid - predicted,
            "coverage_fraction": predicted / valid if valid else 0.0,
        }


def prediction_inputs(cfg, checkpoint, fragment_id, config_path=None):
    """Include individual input files so hard links outside the tree are caught."""
    root = Path(cfg.data_root) / fragment_id
    inputs = [(checkpoint, "checkpoint"), (root, "fragment inputs")]
    inputs.extend(
        (root / "layers" / f"{index:02d}.tif", f"layer {index}")
        for index in range(cfg.start_idx, cfg.end_idx)
    )
    inputs.append((root / f"{fragment_id}_mask.png", "fragment mask"))
    if config_path is not None:
        inputs.append((config_path, "configuration"))
    return inputs


def validate_output(output, inputs):
    """Nonmutating path preflight; callers must serialize writers and inputs."""
    output = Path(output)
    try:
        info = output.lstat()
    except FileNotFoundError:
        info = None
    if info is not None:
        if stat.S_ISLNK(info.st_mode):
            raise ValueError(f"prediction output must not be a symlink: {output}")
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"prediction output must be a regular file: {output}")
    validate_plan_paths([(output, "prediction output")], inputs)


def write_prediction(output, result: InferenceResult, output_format, inputs):
    """Replace one complete file, retaining the previous file on save failure.

    The NPZ bundle keeps probability, coverage and the fragment mask together;
    a separate sidecar could silently outlive a replaced probability map.
    This is an atomic rename, not writer locking or a power-loss durability claim.
    """
    if output_format not in {"npy", "npz"}:
        raise ValueError("output_format must be npy or npz")
    output = Path(output)
    validate_output(output, inputs)
    permissions = replacement_mode(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), permissions)
            if output_format == "npy":
                np.save(stream, result.probability, allow_pickle=False)
            else:
                np.savez_compressed(
                    stream,
                    schema_version=np.array(1, dtype=np.uint8),
                    probability=result.probability,
                    coverage=result.coverage,
                    fragment_mask=result.fragment_mask,
                )
        validate_output(output, inputs)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
