"""Shared stat-only discovery and drift checks for checkpoint cleanup commands."""

import stat
from pathlib import Path

CKPT = "checkpoint_fitted.ckpt"


def checkpoint_identity(path):
    path = Path(path)
    parents = [parent.lstat() for parent in (path.parent.parent, path.parent)]
    if any(not stat.S_ISDIR(info.st_mode) for info in parents):
        raise ValueError(f"checkpoint parents must be nonsymlink directories: {path}")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"checkpoint must be a regular nonsymlink file: {path}")
    return {
        "root_device": parents[0].st_dev,
        "root_inode": parents[0].st_ino,
        "arm_device": parents[1].st_dev,
        "arm_inode": parents[1].st_ino,
        "device": info.st_dev,
        "inode": info.st_ino,
        "mode": info.st_mode,
        "bytes": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
    }


def discover_checkpoints(spiral_out):
    root = Path(spiral_out).absolute()
    root = root.parent.resolve() / root.name
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise ValueError("--spiral-out must be a nonsymlink directory")
    root = root.resolve()
    rows = []
    for arm in sorted(root.iterdir()):
        if not stat.S_ISDIR(arm.lstat().st_mode):
            continue
        path = arm / CKPT
        try:
            identity = checkpoint_identity(path)
        except FileNotFoundError:
            continue
        rows.append(
            {
                "arm": arm.name,
                "path": str(path),
                "bytes": identity["bytes"],
                "identity": identity,
            }
        )
    return root, rows


def require_unchanged(row):
    if checkpoint_identity(row["path"]) != row["identity"]:
        raise ValueError(
            f"checkpoint or parent changed; refusing deletion: {row['path']}"
        )
