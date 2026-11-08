"""Nonmutating production output planning and inspection of existing artifacts."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from vesuvius_autoresearch.core.prediction_artifacts import (
    prediction_stem,
    validate_plan_paths,
)
from volume_cartographer_wrapper.volume import (
    local_volume_array_path,
    local_volume_path,
)

MAX_OUTPUT_ENTRIES = 100_000


def _regular_file(path, info):
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(
            f"production output must be a nonsymlink regular file without hard links: {path}"
        )


def _zarr_tree(path):
    stack, count = [path], 0
    while stack:
        directory = stack.pop()
        if not stat.S_ISDIR(directory.lstat().st_mode):
            raise ValueError(
                f"production Zarr output must be a nonsymlink directory: {directory}"
            )
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > MAX_OUTPUT_ENTRIES:
                    raise ValueError(
                        f"existing production output exceeds {MAX_OUTPUT_ENTRIES} entries"
                    )
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    stack.append(Path(entry.path))
                else:
                    _regular_file(Path(entry.path), info)


@dataclass(frozen=True)
class ProductionArtifactPlan:
    directory: Path
    stem: str
    source: Path
    checkpoint: Path
    source_array: Path

    @classmethod
    def create(cls, directory, default_stem, artifact_stem, uri, checkpoint):
        source = local_volume_path(uri).resolve()
        plan = cls(
            Path(directory).resolve(),
            prediction_stem(default_stem, artifact_stem),
            source,
            Path(checkpoint).resolve(),
            local_volume_array_path(source),
        )
        plan.validate()
        return plan

    @property
    def zarr_path(self):
        return self.directory / f"{self.stem}.zarr"

    @property
    def metadata_path(self):
        return self.directory / f"{self.stem}_meta.json"

    def validate(self):
        if os.path.lexists(self.directory) and not stat.S_ISDIR(
            self.directory.lstat().st_mode
        ):
            raise ValueError(
                f"production output directory must be a nonsymlink directory: {self.directory}"
            )
        validate_plan_paths(
            [
                (self.zarr_path, "production Zarr"),
                (self.metadata_path, "production metadata"),
            ],
            [
                (self.source, "CT source"),
                (self.source_array, "selected CT array"),
                (self.checkpoint, "checkpoint"),
            ],
        )
        if os.path.lexists(self.zarr_path):
            _zarr_tree(self.zarr_path)
        if os.path.lexists(self.metadata_path):
            _regular_file(self.metadata_path, self.metadata_path.lstat())
