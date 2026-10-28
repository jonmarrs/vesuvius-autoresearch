"""Bounded UTF-8 source captures shared by reports and command planners."""

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Snapshot:
    path: Path
    data: bytes
    limit: int

    @classmethod
    def read(cls, path, limit):
        path = Path(path).resolve()
        if not path.is_file():
            raise ValueError(f"input must be a regular file: {path}")
        with path.open("rb") as stream:
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
