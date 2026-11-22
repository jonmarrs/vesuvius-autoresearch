#!/usr/bin/env python3
"""Export a local rendered crop as Studio's uint8 [16,H,W] NumPy input.

No inference, depth selection, rescaling or scientific validation is performed.
The caller supplies consecutive native-resolution planes in model depth order.
"""

import argparse
import hashlib
import json
import math
from collections import ChainMap
from pathlib import Path

import numpy as np

INTERFACE_SOURCE = (
    "https://github.com/priyankaranke/vesuvius-studio-multiscroll-cpt/"
    "blob/235e3be8a06749344862c89a1e52c81d90b15e0e/README.md"
)


def safe_zarr_metadata(array_path: Path) -> bytes:
    """Accept only unfiltered, raw/Blosc Zarr v2 before codec construction.

    Numeric dtype alone does not rule out a Pickle filter. Cache the validated
    metadata bytes so the library cannot reread a changed codec configuration.
    """
    with (array_path / ".zarray").open("rb") as handle:
        raw = handle.read(64 * 1024 + 1)
    if len(raw) > 64 * 1024:
        raise ValueError("Zarr array metadata exceeds 64 KiB")
    metadata = json.loads(raw)
    if not isinstance(metadata, dict) or metadata.get("zarr_format") != 2:
        raise ValueError("only local Zarr v2 arrays are supported")
    if metadata.get("dtype") != "|u1":
        raise ValueError("Zarr metadata must declare canonical uint8 dtype |u1")
    if metadata.get("dimension_separator", ".") not in (".", "/"):
        raise ValueError("Zarr dimension separator must be . or /")
    if metadata.get("filters") not in (None, []):
        raise ValueError("Zarr filters are unsupported; no codec will be constructed")
    compressor = metadata.get("compressor")
    if compressor is not None:
        allowed = {"id", "cname", "clevel", "shuffle", "blocksize"}
        if (
            not isinstance(compressor, dict)
            or compressor.get("id") != "blosc"
            or not set(compressor).issubset(allowed)
            or not isinstance(compressor.get("cname"), str)
            or type(compressor.get("clevel")) is not int
            or not 0 <= compressor["clevel"] <= 9
            or type(compressor.get("shuffle")) is not int
            or compressor["shuffle"] not in (0, 1, 2)
            or type(compressor.get("blocksize")) is not int
            or compressor["blocksize"] < 0
        ):
            raise ValueError("only raw or standard Blosc compression is supported")
    return raw


def open_source(source: Path, array_key: str):
    """Open only a local NPY or DirectoryStore array, never a remote store."""
    source = source.resolve(strict=True)
    if source.is_file() and source.suffix == ".npy":
        if array_key:
            raise ValueError("--array-key applies only to a Zarr directory")
        return np.load(source, mmap_mode="r", allow_pickle=False), source
    if not source.is_dir():
        raise ValueError("source must be a local .npy file or Zarr directory")
    key = Path(array_key)
    if key.is_absolute() or ".." in key.parts:
        raise ValueError("array key must stay inside the source directory")
    array_path = (source / key).resolve(strict=True)
    if not array_path.is_relative_to(source):
        raise ValueError("array key resolves outside the source directory")
    metadata = safe_zarr_metadata(array_path)
    import zarr

    # DirectoryStore avoids URL/fsspec dispatch. Overlay the validated metadata
    # rather than asking Zarr to reread potentially changed codec configuration.
    store = zarr.storage.KVStore(
        ChainMap({".zarray": metadata}, zarr.DirectoryStore(str(array_path)))
    )
    array = zarr.open_array(store=store, mode="r")
    return array, source


def export_input(
    source: Path,
    output: Path,
    *,
    first_plane: int,
    depth_step: int,
    crop: tuple[int, int, int, int],
    depth_order_note: str,
    array_key: str = "",
    max_output_bytes: int = 256 * 1024 * 1024,
    max_block_bytes: int = 8 * 1024 * 1024,
):
    """Write new output only; JSON describes the selected bytes, not a whole CT hash."""
    if depth_step not in (-1, 1):
        raise ValueError("depth step must be -1 or 1 (16 consecutive planes)")
    if not depth_order_note.strip():
        raise ValueError(
            "explain how the chosen render planes map to model depth order"
        )
    if max_output_bytes < 1 or max_block_bytes < 1:
        raise ValueError("byte limits must be positive")
    array, source = open_source(Path(source), array_key)
    if array.ndim != 3 or array.dtype != np.dtype("uint8"):
        raise ValueError(
            "expected a uint8 [depth,height,width] source; no implicit conversion"
        )
    if min(array.shape) < 1:
        raise ValueError("source dimensions must be positive")
    planes = [first_plane + depth_step * i for i in range(16)]
    if min(planes) < 0 or max(planes) >= array.shape[0]:
        raise ValueError("all 16 planes must be inside source depth")
    row0, row1, col0, col1 = crop
    if not (0 <= row0 < row1 <= array.shape[1] and 0 <= col0 < col1 <= array.shape[2]):
        raise ValueError("crop must be nonempty and inside source height/width")
    height, width = row1 - row0, col1 - col0
    payload_bytes = 16 * height * width
    if payload_bytes > max_output_bytes:
        raise ValueError(f"selected payload {payload_bytes} exceeds --max-output-bytes")
    if width > max_block_bytes:
        raise ValueError(
            "one output row exceeds --max-block-bytes; choose a narrower crop"
        )
    chunks = getattr(array, "chunks", None)
    if (
        chunks is not None
        and math.prod(chunks) * array.dtype.itemsize > max_block_bytes
    ):
        raise ValueError("decoded source chunk exceeds --max-block-bytes")
    # Strictly resolve the parent; the utility never creates arbitrary ancestor trees.
    output = Path(output)
    output = output.parent.resolve(strict=True) / output.name
    if output == source or (source.is_dir() and output.is_relative_to(source)):
        raise ValueError("output must be outside the source hierarchy")
    # mkdir (not exists-then-create) also refuses existing directories/dangling symlinks.
    output.mkdir()
    created = []
    try:
        path = output / "planes.npy"
        with path.open("xb") as handle:
            created.append(path)
            np.lib.format.write_array_header_2_0(
                handle,
                {"descr": "|u1", "fortran_order": False, "shape": (16, height, width)},
            )
            payload_hash = hashlib.sha256()
            plane_hashes = []
            rows_per_block = max(1, max_block_bytes // width)
            for plane in planes:
                plane_hash = hashlib.sha256()
                for start in range(row0, row1, rows_per_block):
                    stop = min(start + rows_per_block, row1)
                    block = np.asarray(array[plane, start:stop, col0:col1])
                    if block.shape != (stop - start, width) or block.dtype != np.uint8:
                        raise ValueError(
                            "source returned an unexpected block shape or dtype"
                        )
                    raw = block.tobytes(order="C")
                    handle.write(raw)
                    payload_hash.update(raw)
                    plane_hash.update(raw)
                plane_hashes.append(plane_hash.hexdigest())
        file_hash = hashlib.sha256()
        with path.open("rb") as handle:
            for block_bytes in iter(lambda: handle.read(1024 * 1024), b""):
                file_hash.update(block_bytes)
        manifest = {
            "schema": "studio-input-v1",
            "interface_source": INTERFACE_SOURCE,
            "source": {
                "path": str(source),
                "array_key": array_key,
                "shape": list(array.shape),
                "dtype": str(array.dtype),
            },
            "planes_in_model_order": planes,
            "crop_half_open": {"rows": [row0, row1], "cols": [col0, col1]},
            "depth_order_note": depth_order_note,
            "output": {
                "file": "planes.npy",
                "shape": [16, height, width],
                "dtype": "uint8",
                "payload_bytes": payload_bytes,
                "file_sha256": file_hash.hexdigest(),
            },
            "selected_payload_sha256": payload_hash.hexdigest(),
            "selected_plane_sha256_in_model_order": plane_hashes,
            "transform": "crop and depth selection only; no intensity or spatial conversion",
        }
        manifest_path = output / "input.json"
        with manifest_path.open("x") as handle:
            created.append(manifest_path)
            json.dump(manifest, handle, indent=2)
            handle.write("\n")
        return manifest
    except BaseException:
        # Remove only files created by this call; do not recursively delete a directory.
        for path in reversed(created):
            path.unlink(missing_ok=True)
        output.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--source", type=Path, required=True, help="local .npy or Zarr root"
    )
    parser.add_argument(
        "--array-key", default="", help="explicit array path under Zarr root, e.g. 0"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new directory under an existing parent",
    )
    parser.add_argument("--first-plane", type=int, required=True)
    parser.add_argument("--depth-step", type=int, choices=(-1, 1), required=True)
    parser.add_argument(
        "--crop",
        type=int,
        nargs=4,
        required=True,
        metavar=("ROW0", "ROW1", "COL0", "COL1"),
    )
    parser.add_argument(
        "--depth-order-note",
        required=True,
        help="caller explanation, not an automatic orientation check",
    )
    parser.add_argument("--max-output-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--max-block-bytes", type=int, default=8 * 1024 * 1024)
    args = parser.parse_args(argv)
    try:
        result = export_input(**vars(args))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"INPUT_PREPARATION_REFUSED: {exc}\n")
    print(
        f"Prepared {result['output']['shape']} uint8 input in {args.output}; no inference run"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
