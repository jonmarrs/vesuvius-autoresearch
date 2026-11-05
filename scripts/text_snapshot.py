"""Bounded UTF-8 source captures shared by reports and command planners."""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path


def _nonblocking_open(path, flags):
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))


@dataclass(frozen=True)
class Snapshot:
    path: Path
    data: bytes
    limit: int

    @classmethod
    def read(cls, path, limit):
        if type(limit) is not int or limit < 1:
            raise ValueError("capture limit must be a positive integer")
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError(f"input must be a regular file: {path}")
        # A path can become a FIFO after is_file(). Open nonblocking on POSIX
        # and validate the actual descriptor before reading any bytes.
        with open(path, "rb", opener=_nonblocking_open) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"input must be a regular file: {path}")
            if info.st_size > limit:
                raise ValueError(f"input exceeds {limit} bytes: {path}")
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f"input exceeds {limit} bytes: {path}")
        data.decode("utf-8-sig")
        return cls(path, data, limit)

    def text(self):
        return self.data.decode("utf-8-sig")

    def provenance(self):
        return {
            "path": str(self.path),
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "bytes": len(self.data),
        }

    def verify(self):
        if Snapshot.read(self.path, self.limit).data != self.data:
            raise ValueError(f"input changed before publication: {self.path}")

    def copy_into(self, directory, name):
        path = directory / "sources" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.data)
        if path.read_bytes() != self.data:
            raise ValueError("source snapshot copy verification failed")
        return {
            f"sources/{name}": {
                "sha256": self.provenance()["sha256"],
                "bytes": len(self.data),
            }
        }
