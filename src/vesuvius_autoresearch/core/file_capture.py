"""Bounded captures of regular files for parsing and content identification."""

import hashlib
import os
import stat
from contextlib import contextmanager
from pathlib import Path

MAX_VALIDATION_IMAGE_BYTES = 512 * 1024**2


def _nonblocking_open(path, flags):
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))


@contextmanager
def _open_bounded_file(path, limit):
    """Bound reads by the opened file's size plus one byte to detect growth."""
    if type(limit) is not int or limit < 1:
        raise ValueError("capture limit must be a positive integer")
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"input must be a regular file: {path}")
    with open(path, "rb", opener=_nonblocking_open) as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"input must be a regular file: {path}")
        if before.st_size > limit:
            raise ValueError(f"input exceeds {limit} bytes: {path}")
        yield path, stream, before.st_size + 1
        size = stream.tell()
        if size > limit:
            raise ValueError(f"input exceeds {limit} bytes: {path}")
        after = os.fstat(stream.fileno())
        if size != before.st_size or (
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError(f"input changed while capturing: {path}")


def capture_bytes(path, limit):
    """Capture one regular file without reserving the entire allowed byte budget."""
    with _open_bounded_file(path, limit) as (path, stream, read_limit):
        data = stream.read(read_limit)
    return path, data


def capture_sha256(path, limit) -> str:
    """Hash a bounded regular file with a fixed-size read buffer."""
    digest = hashlib.sha256()
    with _open_bounded_file(path, limit) as (_, stream, remaining):
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            if not block:
                break
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()
