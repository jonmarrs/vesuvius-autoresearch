"""Publish complete detector fragments; never overwrite prior data or invent labels."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import tifffile


def resolve_float_encoding(arr, float_encoding="auto"):
    """Resolve the legacy range heuristic once for the whole selected volume."""
    if not isinstance(float_encoding, str) or float_encoding not in {
        "auto",
        "unit",
        "byte",
    }:
        raise ValueError("float_encoding must be auto, unit or byte")
    arr = np.asarray(arr)
    if not arr.size:
        raise ValueError("pixels must be nonempty and finite")
    if arr.dtype.kind != "f":
        return float_encoding
    low, high = float("inf"), -float("inf")
    for plane in arr if arr.ndim > 2 else [arr]:
        if not np.isfinite(plane).all():
            raise ValueError("pixels must be nonempty and finite")
        low, high = min(low, float(plane.min())), max(high, float(plane.max()))
    mode = (
        ("unit" if high <= 1 else "byte")
        if float_encoding == "auto"
        else float_encoding
    )
    maximum = 1 if mode == "unit" else 255
    if low < 0 or high > maximum:
        raise ValueError(
            f"float pixels must be finite and in [0,{maximum}] for {mode} encoding"
        )
    return mode


def to_uint8(arr, *, float_encoding="auto"):
    """Convert uint8, uint16, or finite floats (unit or byte range) to detector bytes."""
    arr = np.asarray(arr)
    mode = resolve_float_encoding(arr, float_encoding)
    if arr.dtype.kind == "u" and arr.dtype.itemsize == 1:
        return arr
    if arr.dtype.kind == "u" and arr.dtype.itemsize == 2:
        return (arr // 256).astype(np.uint8)
    if np.issubdtype(arr.dtype, np.floating):
        if mode == "unit":
            arr = arr * 255
        return arr.astype(np.uint8)
    raise ValueError(f"unsupported dtype {arr.dtype}; expected uint8/uint16/float")


def validate_fragment_id(frag_id):
    if (
        not isinstance(frag_id, str)
        or not frag_id.strip()
        or frag_id in (".", "..")
        or any(c in frag_id for c in ("/", "\\", "\x00"))
    ):
        raise ValueError("fragment id must be a single nonempty directory name")
    return frag_id


def write_fragment_artifact(
    layers,
    valid,
    out_root,
    frag_id,
    *,
    start_idx=17,
    label=None,
    provenance=None,
    float_encoding="auto",
    verify_sources=None,
):
    """Stage layers, mask, optional *supplied* label, and metadata beside the destination.

    Publish with one directory rename only after every write succeeds. Existing fragment
    ids are refused, including labeled fragments and broken symlinks. Use a fresh id/root
    for reruns. A crash may leave a hidden staging directory, never a final fragment.
    """
    validate_fragment_id(frag_id)
    layers = np.asarray(layers)
    valid = np.asarray(valid)
    if layers.ndim != 3 or min(layers.shape) == 0:
        raise ValueError("layers must have nonempty shape (depth, height, width)")
    if valid.dtype != np.bool_ or valid.shape != layers.shape[1:]:
        raise ValueError("valid mask must be boolean and match the layer grid")
    if (
        not isinstance(start_idx, (int, np.integer))
        or isinstance(start_idx, (bool, np.bool_))
        or start_idx < 0
    ):
        raise ValueError("start_idx must be a nonnegative integer")
    # Resolve once across the selected volume, then validate before opening files.
    mode = resolve_float_encoding(layers, float_encoding)
    for layer in layers:
        to_uint8(layer, float_encoding=mode)
    if label is not None:
        label = np.asarray(label)
        if label.dtype != np.uint8 or label.shape != valid.shape:
            raise ValueError("supplied label must be uint8 and match the layer grid")
    metadata = (
        json.dumps(provenance, indent=2, allow_nan=False, default=float) + "\n"
        if provenance is not None
        else None
    )
    root = Path(out_root)
    destination = root / frag_id
    if os.path.lexists(destination):
        raise FileExistsError(
            f"fragment already exists: {destination}; use a fresh id/root"
        )
    root.mkdir(parents=True, exist_ok=True)

    def record(path):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}

    with tempfile.TemporaryDirectory(prefix=f".{frag_id}-", dir=root) as temp:
        staged = Path(temp) / frag_id
        (staged / "layers").mkdir(parents=True)
        outputs = {}
        for k, layer in enumerate(layers):
            path = staged / "layers" / f"{start_idx + k:02d}.tif"
            encoded = to_uint8(layer, float_encoding=mode)
            tifffile.imwrite(path, encoded, photometric="minisblack")
            back = tifffile.imread(path)
            if back.dtype != np.uint8 or not np.array_equal(back, encoded):
                raise OSError(f"TIFF readback failed: {path.name}")
            outputs[path.relative_to(staged).as_posix()] = record(path)
        images = [(f"{frag_id}_mask.png", valid.astype(np.uint8) * 255)]
        if label is not None:
            images.append((f"{frag_id}_inklabels.png", label))
        for name, pixels in images:
            if not cv2.imwrite(str(staged / name), pixels):
                raise OSError(f"failed to write {name}")
            back = cv2.imread(str(staged / name), cv2.IMREAD_UNCHANGED)
            if (
                back is None
                or back.dtype != np.uint8
                or not np.array_equal(back, pixels)
            ):
                raise OSError(f"PNG readback failed: {name}")
            outputs[name] = record(staged / name)
        if metadata is not None:
            path = staged / f"{frag_id}_render_provenance.json"
            path.write_text(metadata)
            if path.read_text() != metadata:
                raise OSError("provenance readback failed")
            outputs[path.name] = record(path)
        manifest = {
            "contract": 1,
            "fragment_id": frag_id,
            "shape_zyx": list(layers.shape),
            "source_dtype": str(layers.dtype),
            "output_dtype": "uint8",
            "start_idx": int(start_idx),
            "label_present": label is not None,
            "float_encoding_requested": float_encoding,
            "float_encoding_applied": mode if layers.dtype.kind == "f" else None,
            "outputs": outputs,
            "alignment_verified": False,
            "label_quality_verified": False,
            "training_ready": False,
        }
        text = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
        (staged / "fragment.json").write_text(text)
        if json.loads((staged / "fragment.json").read_text()) != manifest:
            raise OSError("fragment manifest readback failed")
        if verify_sources is not None:
            verify_sources()
        for name, expected in outputs.items():
            if record(staged / name) != expected:
                raise ValueError(f"output changed before publication: {name}")
        if os.path.lexists(destination):
            raise FileExistsError(f"fragment already exists: {destination}")
        staged.rename(destination)
    return str(destination)
