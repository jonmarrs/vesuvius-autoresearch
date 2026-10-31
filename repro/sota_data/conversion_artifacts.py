"""Header preflight, captured-byte decoding and source-bound fragment publication."""

import hashlib
import io
import json
import math
import os
import re
from pathlib import Path

import cv2
import numpy as np
import tifffile
from PIL import Image

from .convert import DEFAULT_MAX_VOXELS, SHAPE_TOLERANCE_PX
from .depth_window import depth_window
from .fragment import (
    resolve_float_encoding,
    validate_fragment_id,
    write_fragment_artifact,
)

MAX_FILE_BYTES = 512 * 1024**2
MAX_VOXELS = 512 * 1024**2


def _file(path, maximum=MAX_FILE_BYTES):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"source must be a regular nonsymlink file: {path}")
    size = path.stat().st_size
    if not 0 < size <= maximum:
        raise ValueError(f"source exceeds encoded byte limit {maximum}: {path}")
    return size


def _capture(path, maximum=MAX_FILE_BYTES):
    size = _file(path, maximum)
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) != size:
        raise ValueError(f"source changed while reading: {path}")
    return data, {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _tiff_header(source):
    with tifffile.TiffFile(source) as image:
        if len(image.series) != 1 or len(image.pages) != 1:
            raise ValueError("layer must be a single 2D grayscale TIFF")
        page = image.pages[0]
        if len(page.shape) != 2 or min(page.shape) < 1 or page.samplesperpixel != 1:
            raise ValueError("layer must be a 2D grayscale TIFF")
        dtype = np.dtype(page.dtype)
        if not (
            dtype.kind == "u"
            and dtype.itemsize in {1, 2}
            or dtype.kind == "f"
            and dtype.itemsize in {2, 4, 8}
        ):
            raise ValueError(f"unsupported layer dtype: {dtype}")
        return {"shape": list(page.shape), "dtype": dtype.str}


def _image_header(source, what):
    try:
        with Image.open(source) as image:
            if (
                image.mode not in {"1", "L"}
                or "transparency" in image.info
                or getattr(image, "n_frames", 1) != 1
            ):
                raise ValueError(f"{what} must be a single uint8 grayscale image")
            return list(reversed(image.size))
    except OSError as exc:
        raise ValueError(f"{what} file unreadable") from exc


def _selection(source, count):
    paths = [
        path
        for path in (source / "layers").glob("*.tif")
        if not path.name.startswith(".")
    ]
    if len(paths) > 4096:
        raise ValueError("too many source layers (maximum 4096)")
    try:
        paths.sort(key=lambda path: int(path.stem))
    except ValueError as exc:
        raise ValueError("layer filenames must be integer depth indices") from exc
    indices = [int(path.stem) for path in paths]
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate layer depth indices")
    if len(paths) < count:
        raise ValueError(f"found {len(paths)} source layers, need >= {count}")
    lo, hi = depth_window(len(paths), count)
    selected = indices[lo:hi]
    if any(b - a != 1 for a, b in zip(selected, selected[1:], strict=False)):
        raise ValueError("selected source depth indices must be consecutive")
    files = paths[lo:hi]
    for pattern, what, required in (
        ("*inklabels*", "label", True),
        ("*mask*", "mask", False),
    ):
        matches = sorted(
            path for path in source.glob(pattern) if not path.name.startswith(".")
        )
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous {'inklabels' if what == 'label' else what} files"
            )
        if required and not matches:
            raise ValueError(f"no *inklabels* file in {source}")
        files.extend(matches)
    if len(set(files)) != len(files):
        raise ValueError("label and mask must be distinct files")
    return files, selected


def _download_record(source):
    path = source / "download.json"
    if not os.path.lexists(path):
        return None, None
    data, identity = _capture(path, 4 * 1024**2)
    try:
        record = json.loads(data)
        if (
            type(record.get("contract")) is not int
            or record.get("contract") != 1
            or record.get("status") != "DOWNLOADED"
        ):
            raise ValueError("unsupported download record")
        rows = record["files"]
        if not isinstance(rows, list) or len(rows) > 1024:
            raise ValueError("invalid download files")
        expected = {}
        for row in rows:
            name = row["relative_path"]
            if (
                not isinstance(name, str)
                or name in expected
                or not name
                or any(part in {"", ".", ".."} for part in name.split("/"))
                or name.startswith("/")
                or "\\" in name
            ):
                raise ValueError("unsafe or duplicate download path")
            if (
                type(row["bytes"]) is not int
                or not 0 < row["bytes"] <= 2 * 1024**3
                or not isinstance(row["sha256"], str)
                or not re.fullmatch("[0-9a-f]{64}", row["sha256"])
            ):
                raise ValueError("invalid download file identity")
            expected[name] = {key: row[key] for key in ("bytes", "sha256")}
        return expected, identity
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"invalid download.json: {exc}") from exc


def build_plan(
    src_dir,
    seg_id,
    out_root,
    n_layers=26,
    start_idx=17,
    float_encoding="auto",
    max_voxels=DEFAULT_MAX_VOXELS,
):
    validate_fragment_id(seg_id)
    if type(n_layers) is not int or not 1 <= n_layers <= 512:
        raise ValueError("n_layers must be a positive integer <= 512")
    if type(start_idx) is not int or start_idx < 0:
        raise ValueError("start_idx must be a nonnegative integer")
    if type(max_voxels) is not int or not 1 <= max_voxels <= MAX_VOXELS:
        raise ValueError(f"max_voxels must be an integer from 1 to {MAX_VOXELS}")
    if not isinstance(float_encoding, str) or float_encoding not in {
        "auto",
        "unit",
        "byte",
    }:
        raise ValueError("float_encoding must be auto, unit or byte")
    for value in (src_dir, out_root):
        if "://" in str(value) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:/", str(value)):
            raise ValueError("use local filesystem directories")
    source = Path(src_dir).absolute()
    output = Path(out_root).absolute() / seg_id
    if os.path.lexists(output):
        raise FileExistsError(f"fragment already exists: {output}; use a fresh id/root")
    if source.is_symlink() or (source / "layers").is_symlink():
        raise ValueError("source directories must not be symlinks")
    source, output = source.resolve(), output.resolve()
    if output == source or source in output.parents:
        raise ValueError("output must be outside the raw source directory")
    files, indices = _selection(source, n_layers)
    entries = []
    first = None
    for index, path in enumerate(files):
        size = _file(path)
        if index < n_layers:
            header = _tiff_header(path)
            if math.prod(header["shape"]) * n_layers > max_voxels:
                raise ValueError(f"selected volume exceeds max_voxels={max_voxels}")
            if first is None:
                first = header
            if header["shape"] != first["shape"]:
                raise ValueError("source layer shape mismatch")
            if (
                np.dtype(header["dtype"]).kind != np.dtype(first["dtype"]).kind
                or np.dtype(header["dtype"]).itemsize
                != np.dtype(first["dtype"]).itemsize
            ):
                raise ValueError(
                    "source layer dtype mismatch; mixed encodings are refused"
                )
        else:
            what = "label" if index == n_layers else "mask"
            header = {"shape": _image_header(path, what)}
            if any(
                abs(a - b) > SHAPE_TOLERANCE_PX
                for a, b in zip(header["shape"], first["shape"], strict=True)
            ):
                raise ValueError(
                    f"{what} shape mismatch > {SHAPE_TOLERANCE_PX} px; register it to the layer grid first"
                )
        entries.append(
            {
                "relative_path": path.relative_to(source).as_posix(),
                "bytes": size,
                **header,
            }
        )
    expected, download = _download_record(source)
    if expected is not None and any(
        entry["relative_path"] not in expected
        or expected[entry["relative_path"]]["bytes"] != entry["bytes"]
        for entry in entries
    ):
        raise ValueError("consumed sources disagree with download.json")
    if expected is not None:
        recorded_supervision = {
            name
            for name in expected
            if "/" not in name
            and not name.startswith(".")
            and ("inklabels" in name or "mask" in name)
        }
        if recorded_supervision != {
            entry["relative_path"] for entry in entries[n_layers:]
        }:
            raise ValueError("supervision selection disagrees with download.json")
    return {
        "contract": 1,
        "status": "HEADER_PLAN_ONLY",
        "source": str(source),
        "output": str(output),
        "selected_depth_indices": indices,
        "files": entries,
        "shape_zyx": [n_layers, *first["shape"]],
        "max_voxels": max_voxels,
        "start_idx": start_idx,
        "float_encoding_requested": float_encoding,
        "download_record": download,
        "download_consumed_hashes_verified": False,
        "float_encoding_applied": None,
        "max_file_bytes": MAX_FILE_BYTES,
        "pixel_values_checked": False,
        "alignment_verified": False,
        "label_quality_verified": False,
        "training_ready": False,
    }


def convert(src_dir, seg_id, out_root, n_layers, start_idx, float_encoding, max_voxels):
    plan = build_plan(
        src_dir, seg_id, out_root, n_layers, start_idx, float_encoding, max_voxels
    )
    source = Path(plan["source"])
    expected, download = _download_record(source)
    if download != plan["download_record"]:
        raise ValueError("download.json changed after preflight")
    layers = np.empty(plan["shape_zyx"], dtype=np.dtype(plan["files"][0]["dtype"]))
    images, inputs = [], {}
    for index, entry in enumerate(plan["files"]):
        name = entry["relative_path"]
        data, identity = _capture(source / name)
        if (
            identity["bytes"] != entry["bytes"]
            or expected is not None
            and identity != expected[name]
        ):
            raise ValueError(f"source disagrees with preflight/download.json: {name}")
        inputs[name] = identity
        if index < n_layers:
            header = _tiff_header(io.BytesIO(data))
            if header != {key: entry[key] for key in ("shape", "dtype")}:
                raise ValueError(f"layer header changed: {name}")
            pixels = tifffile.imread(io.BytesIO(data))
            if (
                list(pixels.shape) != entry["shape"]
                or pixels.dtype.str != entry["dtype"]
            ):
                raise ValueError(f"decoded layer disagrees with header: {name}")
            layers[index] = pixels
        else:
            shape = _image_header(io.BytesIO(data), "label/mask")
            if shape != entry["shape"]:
                raise ValueError(f"label/mask header changed: {name}")
            pixels = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_UNCHANGED)
            if (
                pixels is None
                or pixels.dtype != np.uint8
                or list(pixels.shape) != shape
            ):
                raise ValueError(f"label/mask file unreadable: {name}")
            images.append(pixels)
    mode = resolve_float_encoding(layers, float_encoding)
    h, w = layers.shape[1:]
    label = np.zeros((h, w), np.uint8)
    label[: min(h, images[0].shape[0]), : min(w, images[0].shape[1])] = images[0][
        :h, :w
    ]
    mask = np.ones((h, w), bool)
    if len(images) == 2:
        mask[:] = False
        mh, mw = images[1].shape
        mask[: min(h, mh), : min(w, mw)] = images[1][:h, :w] > 0
    mask[images[0].shape[0] :, :] = False
    mask[:, images[0].shape[1] :] = False

    def verify():
        current = build_plan(
            src_dir, seg_id, out_root, n_layers, start_idx, float_encoding, max_voxels
        )
        if current != plan:
            raise ValueError("source selection or headers changed during conversion")
        for name, identity in inputs.items():
            if _capture(source / name)[1] != identity:
                raise ValueError(f"source changed during conversion: {name}")

    provenance = {
        **plan,
        "status": "CONVERTED",
        "inputs": inputs,
        "float_encoding_applied": mode if layers.dtype.kind == "f" else None,
        "download_consumed_hashes_verified": expected is not None,
        "pixel_values_checked": True,
    }
    return write_fragment_artifact(
        layers,
        mask,
        out_root,
        seg_id,
        start_idx=start_idx,
        label=label,
        provenance=provenance,
        float_encoding=float_encoding,
        verify_sources=verify,
    )
