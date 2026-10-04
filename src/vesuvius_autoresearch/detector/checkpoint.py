"""Persist the detector input contract in Lightning checkpoints.

Tensor shapes alone cannot identify the through-surface layer interval. Legacy
weights remain loadable with an explicit configuration and a visible warning.
"""

import warnings
from dataclasses import asdict, fields

from .config import DetectorConfig


class DetectorCheckpointMixin:
    cfg: DetectorConfig

    def on_save_checkpoint(self, checkpoint):
        checkpoint["detector_config"] = asdict(self.cfg)
        checkpoint["detector_config_version"] = 1

    def on_load_checkpoint(self, checkpoint):
        if "detector_config" not in checkpoint:
            if "detector_config_version" in checkpoint:
                raise ValueError("checkpoint detector configuration is missing")
            warnings.warn(
                "legacy detector checkpoint has no recorded input configuration; "
                "verify the supplied configuration against its training recipe",
                UserWarning,
                stacklevel=2,
            )
            return
        if (
            type(checkpoint.get("detector_config_version")) is not int
            or checkpoint["detector_config_version"] != 1
        ):
            raise ValueError("checkpoint detector configuration version is unsupported")
        record = checkpoint["detector_config"]
        if not isinstance(record, dict) or set(record) != {
            f.name for f in fields(DetectorConfig)
        }:
            raise ValueError(
                "checkpoint detector configuration is incomplete or malformed"
            )
        try:
            saved = DetectorConfig(**record)
            saved.validate()
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"checkpoint detector configuration is invalid: {exc}"
            ) from exc

        names = ["architecture", "in_chans", "size", "start_idx", "end_idx"]
        if saved.architecture == "resenc":
            names += ["resenc_n_stages", "resenc_base_feat"]
        mismatches = [
            f"{name}: checkpoint={getattr(saved, name)!r}, requested={getattr(self.cfg, name)!r}"
            for name in names
            if getattr(saved, name) != getattr(self.cfg, name)
        ]
        if mismatches:
            raise ValueError(
                "checkpoint input configuration mismatch: " + "; ".join(mismatches)
            )
