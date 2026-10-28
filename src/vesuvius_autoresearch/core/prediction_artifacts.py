"""Shared names and path checks for regional prediction artifacts (stdlib only)."""

from pathlib import Path


def prediction_stem(default: str, override: str | None = None) -> str:
    stem = default if override is None else override
    if (
        not isinstance(stem, str)
        or not stem.strip()
        or stem in {".", ".."}
        or Path(stem).name != stem
        or "\\" in stem
        or any(ord(c) < 32 or ord(c) == 127 for c in stem)
    ):
        raise ValueError(
            "artifact_stem must be a filename without directory components or control characters"
        )
    return stem


def prediction_paths(directory, stem):
    """Reserve the full family, including optional fiber and shard outputs."""
    prediction_stem(stem)
    return [
        Path(directory) / f"{stem}{suffix}"
        for suffix in (
            ".png",
            "_meta.json",
            "_ink.npy",
            "_fiber.npy",
            "_weight.npy",
            "_ink.png",
            "_fiber.png",
            "_ink.zarr",
            "_fiber.zarr",
            "_uncertain",
        )
    ]


def validate_plan_paths(writes, reads):
    """Reject conflicting outputs and output/input aliases before any writes.

    Inputs may overlap each other. Compare resolved paths, ancestors and
    existing inode identities so symlinks and hard links cannot hide collisions.
    Each item is (path, human-readable owner). This is a preflight snapshot.
    """
    entries, inodes = [], {}
    for writing, paths in ((False, reads), (True, writes)):
        for path, owner in paths:
            try:
                resolved = Path(path).resolve()
                try:
                    info = resolved.stat()
                except FileNotFoundError:
                    info = None
            except (OSError, RuntimeError) as exc:
                raise ValueError(f"cannot inspect {owner}: {path}: {exc}") from exc
            entry = (resolved, owner, writing)
            entries.append(entry)
            if info is not None:
                key = (info.st_dev, info.st_ino)
                previous = inodes.get(key)
                if previous is not None and (writing or previous[2]):
                    raise ValueError(
                        f"artifact collision: {owner} and {previous[1]} alias {resolved}"
                    )
                inodes[key] = entry
    ancestors = []
    for entry in sorted(entries, key=lambda item: item[0].parts):
        path, owner, writing = entry
        while ancestors and not path.is_relative_to(ancestors[-1][0]):
            ancestors.pop()
        for parent, parent_owner, parent_writing in ancestors:
            if writing or parent_writing:
                raise ValueError(
                    f"artifact collision: {owner} ({path}) overlaps {parent_owner} ({parent}); choose distinct artifact_stem values or output paths"
                )
        ancestors.append(entry)
