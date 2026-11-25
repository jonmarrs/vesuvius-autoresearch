"""Publication of local artifacts and rollback-safe directory replacement.

Callers must serialize writers. Path checks and renames do not provide a
multi-writer transaction or a power-loss guarantee.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .file_modes import replacement_mode


def separate_paths(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if (
        source == destination
        or source in destination.parents
        or destination in source.parents
    ):
        raise ValueError("source and output paths must not overlap or alias")
    return source, destination


@contextmanager
def staged_directory(destination, *, prefix=None):
    """Publish only after success; keep an existing directory if building fails.

    Replacement uses two renames on the same filesystem and rolls back rename
    errors. Callers must serialize writers; this is not a concurrent writer API.
    """
    destination = Path(destination)
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError(
            f"output must be a directory, not a file or symlink: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}-" if prefix is None else prefix,
            dir=destination.parent,
        )
    )
    staging, backup = workspace / "new.zarr", workspace / "previous"
    staging.mkdir()
    published = False
    try:
        yield staging
        if destination.exists():
            destination.rename(backup)
        try:
            staging.rename(destination)
            published = True
        except BaseException:
            if backup.exists():
                try:
                    backup.rename(destination)
                except OSError as exc:
                    raise RuntimeError(
                        f"publication rollback failed; previous output retained at {backup}"
                    ) from exc
            raise
    finally:
        if published or not backup.exists():
            shutil.rmtree(workspace)


def new_output(output, *sources):
    """Require a separate, new local artifact; reject symlinks, including broken ones."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError(f"output already exists; choose a new artifact path: {output}")
    for source in sources:
        _, output = separate_paths(source, output)
    return output.resolve()


@contextmanager
def publish_new(output):
    """Publish a complete immutable directory. Callers must serialize writers."""
    output = new_output(output)
    with staged_directory(output) as staging:
        yield staging
        # The shared publisher supports replacement; these label tools don't.
        if output.exists() or output.is_symlink():
            raise ValueError(f"output appeared during processing: {output}")


@contextmanager
def staged_file(output, *, suffix=""):
    """Replace a local file by rename after writing its sibling successfully."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent, prefix=".staged-", suffix=suffix, delete=False
        ) as stream:
            staging = Path(stream.name)
        yield staging
        os.chmod(staging, replacement_mode(output))
        staging.replace(output)
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


@contextmanager
def publish_new_file(output, *sources):
    """Publish one validated new file by rename; serialize writers."""
    output = new_output(output, *sources)
    with staged_file(output, suffix=output.suffix) as staging:
        yield staging
        if output.exists() or output.is_symlink():
            raise ValueError(f"output appeared during processing: {output}")
