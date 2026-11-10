"""Nonmutating path planning shared by the regional prediction commands."""

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from vesuvius_autoresearch.core.prediction_artifacts import (
    prediction_paths,
    validate_output_file,
    validate_output_tree,
    validate_plan_paths,
)
from volume_cartographer_wrapper.volume import (
    local_volume_array_path,
    local_volume_path,
)


def _output_path(value):
    if not str(value).strip() or "://" in str(value):
        raise ValueError("prediction output must be a nonempty local path")
    path = Path(value).absolute()
    return path.parent.resolve() / path.name


def validate_checkpoint_metadata(config):
    """Refuse unrecordable checkpoint settings before overwriting any outputs."""
    try:
        json.dumps(config, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("checkpoint config cannot be recorded as finite JSON") from exc


@dataclass(frozen=True)
class RegionalArtifactPlan:
    directory: Path
    stem: str
    image: Path
    metadata: Path
    source: Path
    source_array: Path
    checkpoints: tuple[Path, ...]

    @classmethod
    def create(cls, stem, image, metadata, uri, checkpoints):
        image = _output_path(image)
        source = local_volume_path(uri).resolve()
        plan = cls(
            image.parent,
            stem,
            image,
            _output_path(metadata) if metadata else image.parent / f"{stem}_meta.json",
            source,
            local_volume_array_path(source),
            tuple(Path(path).resolve() for path in checkpoints),
        )
        plan.validate()
        return plan

    @property
    def paths(self):
        paths = prediction_paths(self.directory, self.stem)
        # An explicit canonical path names the same artifact once. Other custom
        # names remain separate entries, so aliasing an array/preview is refused.
        if self.image != self.directory / f"{self.stem}.png":
            paths.append(self.image)
        if self.metadata != self.directory / f"{self.stem}_meta.json":
            paths.append(self.metadata)
        return paths

    def validate(self):
        if os.path.lexists(self.directory) and not stat.S_ISDIR(
            self.directory.lstat().st_mode
        ):
            raise ValueError(
                "prediction output directory must be a nonsymlink directory"
            )
        validate_plan_paths(
            [(path, f"prediction output {path.name}") for path in self.paths],
            [
                (self.source, "CT source"),
                (self.source_array, "selected CT array"),
                *((path, "checkpoint") for path in self.checkpoints),
            ],
        )
        trees = {
            self.directory / f"{self.stem}{suffix}"
            for suffix in ("_ink.zarr", "_fiber.zarr", "_uncertain")
        }
        for path in self.paths:
            if os.path.lexists(path):
                if path in trees:
                    validate_output_tree(path)
                else:
                    validate_output_file(path)
