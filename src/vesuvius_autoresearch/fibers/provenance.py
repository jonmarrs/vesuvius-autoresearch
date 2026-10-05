"""Content identity and atomic writes for fiber benchmark artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np

# Bump when normalization, tiling, class collapse, or connectivity scoring changes.
INFERENCE_VERSION = 1
# 2: connected graph runs, independent of NML edge ordering.
# 3: zero-length edges keep their endpoints connected (2 split fibers there).
# 4: ScrollGT's definition (scrollgt v0.4.0, its scoring version 2), vendored in eval_trace.py:
#    edges walked in path order, runs ending at stretch boundaries.
SCORING_VERSION = 4


def file_sha256(path):
    with Path(path).open("rb") as f:
        return stream_sha256(f)


def stream_sha256(f):
    h = hashlib.sha256()
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
    return h.hexdigest()


def inference_identity(img, model_dir, patch, device="cuda"):
    root = Path(model_dir).resolve()
    image = np.ascontiguousarray(img)
    return {
        "version": INFERENCE_VERSION,
        "image": {
            "shape": list(image.shape),
            "dtype": image.dtype.str,
            "sha256": hashlib.sha256(memoryview(image).cast("B")).hexdigest(),
        },
        "model_dir": str(root),
        "model_files": {
            name: file_sha256(root / name)
            for name in ["plans.json", "dataset.json", "fold_0/checkpoint_final.pth"]
        },
        "recipe": {
            "configuration": "3d_fullres",
            "patch_size": [patch] * 3,
            "tile_step": 0.5,
            "use_mirroring": False,
            "amp": device.startswith("cuda"),
            "device": device,
        },
    }


@contextmanager
def atomic_file(path, mode="w"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, mode) as f:
            yield f
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, value):
    with atomic_file(path) as f:
        json.dump(value, f, indent=1, allow_nan=False)
        f.write("\n")
