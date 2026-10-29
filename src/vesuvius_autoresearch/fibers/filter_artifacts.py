"""Local file boundaries for the classical fiber-filter CLI."""

import errno
import os
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from vesuvius_autoresearch.core.file_modes import replacement_mode
from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths


def validate_paths(source, output, preview=None):
    writes = [(Path(output), "filter response")]
    if preview is not None:
        writes.append((Path(preview), "filter preview"))
    for path, _ in writes:
        try:
            info = path.lstat()
        except FileNotFoundError:
            info = None
        if info is not None:
            if stat.S_ISLNK(info.st_mode):
                raise ValueError(f"output must not be a symlink: {path}")
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"output must be a regular file: {path}")
    validate_plan_paths(writes, [(source, "input CT")])


def input_signature(path):
    info = Path(path).stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"input must be a regular NPY file: {path}")
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


@contextmanager
def mapped_input(path):
    volume = np.load(path, allow_pickle=False, mmap_mode="r")
    try:
        if (
            not isinstance(volume, np.memmap)
            or volume.ndim != 3
            or min(volume.shape) < 3
            or volume.dtype.kind not in "uif"
        ):
            raise ValueError(
                "input must be a real NPY CT array with each axis at least 3"
            )
        yield volume
    finally:
        if isinstance(volume, np.memmap):
            volume._mmap.close()
        elif hasattr(volume, "close"):
            volume.close()


@contextmanager
def staged_file(path):
    if path is None:
        yield None
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, replacement_mode(path))
        os.close(fd)
        fd = None
        yield Path(name)
    finally:
        if fd is not None:
            os.close(fd)
        Path(name).unlink(missing_ok=True)


@contextmanager
def mapped_output(path, shape):
    response = np.lib.format.open_memmap(path, mode="w+", shape=shape, dtype=np.float32)
    try:
        size = Path(path).stat().st_size
        if size > shutil.disk_usage(Path(path).parent).free:
            raise OSError(errno.ENOSPC, "insufficient space for staged filter output")
        if hasattr(os, "posix_fallocate"):
            with Path(path).open("r+b") as stream:
                try:
                    os.posix_fallocate(stream.fileno(), 0, size)
                except OSError as exc:
                    if exc.errno not in (errno.ENOSYS, errno.EOPNOTSUPP):
                        raise
        yield response
        response.flush()
    finally:
        response._mmap.close()


def write_preview(path, projection):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    with Path(path).open("wb") as stream:
        plt.imsave(stream, projection, cmap="magma", format="png")


def publish(source, signature, output, temporary, preview=None, preview_temporary=None):
    """Publish response, then requested preview; its stale PNG cannot survive.

    Inputs and writers must be serialized. Both files are prepared before this
    phase. A publication failure can leave an array without its requested PNG;
    there is no multi-file atomicity or power-loss durability guarantee.
    """
    validate_paths(source, output, preview)
    if input_signature(source) != signature:
        raise ValueError("input CT changed during filtering")
    if preview is not None:
        Path(preview).unlink(missing_ok=True)
    os.replace(temporary, output)
    if preview is not None:
        os.replace(preview_temporary, preview)
