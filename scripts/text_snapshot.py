"""Bounded file captures and UTF-8 source snapshots for reports and planners."""

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

# Keep this stdlib-only helper usable without an editable installation.
SOURCE_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if SOURCE_ROOT not in sys.path:
    sys.path.insert(0, SOURCE_ROOT)

from vesuvius_autoresearch.core.file_capture import capture_bytes


@dataclass(frozen=True)
class Snapshot:
    path: Path
    data: bytes
    limit: int

    @classmethod
    def read(cls, path, limit):
        path, data = capture_bytes(path, limit)
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
