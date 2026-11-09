"""Bounded captures of regular files for parsing and content identification."""

import os
import stat
from pathlib import Path


def _nonblocking_open(path, flags):
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))


def capture_bytes(path, limit):
    """Capture one regular file without reserving the entire allowed byte budget."""
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
        data = stream.read(before.st_size + 1)
        if len(data) > limit:
            raise ValueError(f"input exceeds {limit} bytes: {path}")
        after = os.fstat(stream.fileno())
        if len(data) != before.st_size or (
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError(f"input changed while capturing: {path}")
    return path, data
