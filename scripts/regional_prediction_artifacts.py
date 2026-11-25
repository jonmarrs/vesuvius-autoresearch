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


def _image_destination(value):
    """Bind savefig's filename and format before reserving artifacts."""
    from matplotlib import get_backend, rcParams
    from matplotlib.backend_bases import FigureCanvasBase
    from matplotlib.backends.registry import backend_registry

    path = _output_path(value)
    suffix = path.suffix
    requested_format = suffix[1:] if suffix else rcParams["savefig.format"]
    image_format = requested_format.lower()
    formats = FigureCanvasBase.get_supported_filetypes()
    if image_format not in formats:
        # An active canvas can also implement a writer for an unregistered format.
        canvas = backend_registry.load_backend_module(get_backend()).FigureCanvas
        if not hasattr(canvas, f"print_{image_format}"):
            raise ValueError(
                f"Format {image_format!r} is not supported for --output_img "
                f"(registered formats: {', '.join(sorted(formats))})"
            )

    if not suffix:
        path = path.with_name(f"{path.name.rstrip('.')}.{requested_format}")
    return path, image_format


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
    image_format: str

    @classmethod
    def create(cls, stem, image, metadata, uri, checkpoints):
        image, image_format = _image_destination(image)
        source = local_volume_path(uri).resolve()
        plan = cls(
            image.parent,
            stem,
            image,
            _output_path(metadata) if metadata else image.parent / f"{stem}_meta.json",
            source,
            local_volume_array_path(source),
            tuple(Path(path).resolve() for path in checkpoints),
            image_format=image_format,
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

    def validate_source_selection(self, uri):
        source = local_volume_path(uri).resolve()
        if source != self.source or local_volume_array_path(source) != self.source_array:
            raise RuntimeError("CT source selection changed after regional output planning")

    def validate(self, *, checkpoint_aliases=()):
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
                *((path, "current checkpoint target") for path in checkpoint_aliases),
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
