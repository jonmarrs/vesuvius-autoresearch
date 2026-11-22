"""A bounded, separately registered PHerc1667 renderer-v2 compatibility check.

Downloads public inputs over HTTPS, retains the exact bytes used, and compares
one fixed region with released surface slices. Historical validators are intact.
Run as a module from the checkout; this requires scientific CPU packages.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import io
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import tifffile

from repro.sota_data.render_surface import (
    ChunkCachedZarrFetch,
    pointmap_from_tifxyz,
    read_tifxyz,
    sample_layers,
    surface_normals,
)
from vesuvius_autoresearch.core.file_capture import capture_bytes
from vesuvius_autoresearch.core.new_artifacts import new_output, publish_new

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = "pherc1667-renderer-v2-compatibility/1"
BUCKET = "vesuvius-challenge-open-data"
BASE_URL = f"https://{BUCKET}.s3.amazonaws.com/"
SEGMENT = "20260108140509-w011_20260108140509268_flatboi"
PREFIX = f"{BUCKET}/PHerc1667"
GEOMETRY = (
    f"{PREFIX}/segments/{SEGMENT}/mesh/20260108140509-on-20251217075048-2.399um.tifxyz"
)
RAW = f"{PREFIX}/volumes/20251217075048-2.399um-0.2m-78keV-masked.zarr"
REFERENCE = (
    f"{PREFIX}/segments/{SEGMENT}/surface-volumes/"
    "2.399um-0.22m-78keV-volume-20251217075048.zarr"
)
DESIGN: dict[str, Any] = {
    "geometry": GEOMETRY,
    "raw": RAW,
    "reference": REFERENCE,
    "geometry_shape": [1975, 736],
    "geometry_scale": [0.05, 0.05],
    "raw_shape": [9269, 3808, 3808],
    "reference_shape": [109, 2469, 920],
    "source_dtype": "uint8",
    "raw_level": 2,
    "reference_level": 4,
    "region_yxhw": [736, 112, 128, 128],
    "normal_halo": 1,
    "reference_region_yxhw": [920, 140, 160, 160],
    "reference_depths": [50, 52, 54, 56, 58],
    "normal_sign": 1,
    "layers": 26,
    "k0": -13,
    "tile": 32,
    "group": 2,
    "minimum_supported_fraction": 0.90,
    "minimum_pixels": 1024,
    "ncc_gate": 0.60,
    "max_download_bytes": 192 * 1024**2,
    "max_object_bytes": 16 * 1024**2,
    "max_cache_bytes": 128 * 1024**2,
}
SOURCES = (
    "repro/sota_data/revalidate_render_1667_v2.py",
    "repro/sota_data/render_surface.py",
    "repro/sota_data/fragment.py",
    "src/vesuvius_autoresearch/core/file_capture.py",
    "src/vesuvius_autoresearch/core/file_modes.py",
    "src/vesuvius_autoresearch/core/new_artifacts.py",
)
DEFAULT_PLAN = ROOT / "configs/studies/render_1667_v2_2026-11-17.json"


def source_hashes():
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES
    }


def read_plan(path):
    path, raw = capture_bytes(path, 1024**2)
    plan = json.loads(raw)
    if (
        not isinstance(plan, dict)
        or set(plan) != {"protocol", "baseline_commit", "design", "source_sha256"}
        or plan["protocol"] != PROTOCOL
        or not isinstance(plan["baseline_commit"], str)
        or not re.fullmatch("[0-9a-f]{40}", plan["baseline_commit"])
        or plan["design"] != DESIGN
        or plan["source_sha256"] != source_hashes()
    ):
        raise ValueError("plan does not match the fixed design and selected sources")
    return path, plan, hashlib.sha256(raw).hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SnapshotSource:
    """Small cat-compatible HTTPS transport retaining every successfully read object.

    Missing objects are operational errors here, even if Zarr permits absent
    fill chunks. Public HTTPS digests identify retrieved bytes, not signed
    upstream provenance. Callers serialize requests and use a fresh directory.
    """

    def __init__(self, directory, *, max_total_bytes, max_object_bytes):
        self.directory = Path(directory)
        self.max_total_bytes = max_total_bytes
        self.max_object_bytes = max_object_bytes
        self.records = {}
        self.total_bytes = 0
        self.opener = urllib.request.build_opener(_NoRedirect())

    def path(self, key):
        if not key.startswith(PREFIX + "/") or any(
            part in {"", ".", ".."} for part in key.split("/")
        ):
            raise ValueError("snapshot key must remain inside the study source")
        return self.directory / key.removeprefix(BUCKET + "/")

    def _read(self, key):
        path = self.path(key)
        if key in self.records:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != self.records[key]["sha256"]:
                raise ValueError(f"captured source changed: {key}")
            return raw
        url = BASE_URL + key.removeprefix(BUCKET + "/")
        remaining = min(self.max_object_bytes, self.max_total_bytes - self.total_bytes)
        if remaining < 1:
            raise ValueError("snapshot download byte budget exhausted")
        try:
            with self.opener.open(url, timeout=30) as response:
                count = int(response.headers.get("Content-Length", "-1"))
                if response.status != 200 or not 0 < count <= remaining:
                    raise ValueError("missing or oversized source Content-Length")
                raw = response.read(count + 1)
                if len(raw) != count:
                    raise ValueError("source response length changed or is incomplete")
                headers = {
                    name: response.headers[name]
                    for name in ("ETag", "Last-Modified")
                    if name in response.headers
                }
        except (urllib.error.URLError, http.client.HTTPException) as exc:
            raise OSError(f"source fetch failed: {url}: {exc}") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        self.records[key] = {
            "url": url,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "headers": headers,
        }
        self.total_bytes += len(raw)
        print(f"Captured {key}: {len(raw)} bytes", file=sys.stderr, flush=True)
        return raw

    def cat(self, keys, on_error="raise"):
        if isinstance(keys, str):
            return self._read(keys)
        result = {}
        for key in keys:
            try:
                result[key] = self._read(key)
            except (OSError, ValueError) as exc:
                if on_error != "return":
                    raise
                result[key] = exc
        return result

    def verify(self):
        for key in self.records:
            self._read(key)


def compare_center(layers, supported, references):
    """Score the same full-depth-supported pixels in every reference comparison."""
    layers, supported, references = map(np.asarray, (layers, supported, references))
    if (
        layers.shape != (DESIGN["layers"], *supported.shape)
        or supported.ndim != 2
        or min(supported.shape) < 2
        or supported.dtype != np.bool_
        or layers.dtype.kind not in "uif"
        or references.dtype.kind not in "uif"
        or references.shape != (len(DESIGN["reference_depths"]), *supported.shape)
    ):
        raise ValueError("comparison arrays/mask have incompatible shapes or types")
    pixels = int(supported.sum())
    fraction = float(supported.mean())
    if (
        not np.isfinite(layers[:, supported]).all()
        or not np.isfinite(references[:, supported]).all()
    ):
        raise ValueError("supported render/reference pixels must be finite")
    values = []
    center = layers[-DESIGN["k0"]][supported].astype(np.float64)
    center -= center.mean() if pixels else 0
    for ref in references:
        target = ref[supported].astype(np.float64)
        target -= target.mean() if pixels else 0
        denominator = float(np.sqrt(np.dot(center, center) * np.dot(target, target)))
        values.append(
            float(np.clip(np.dot(center, target) / denominator, -1, 1))
            if denominator > 0
            else None
        )
    sufficient = (
        pixels >= DESIGN["minimum_pixels"]
        and fraction >= DESIGN["minimum_supported_fraction"]
        and all(value is not None for value in values)
    )
    best = int(np.argmax(values)) if sufficient else None
    return {
        "supported_pixels": pixels,
        "supported_fraction": fraction,
        "reference_depths": DESIGN["reference_depths"],
        "ncc_by_depth": values,
        "best_reference_depth": DESIGN["reference_depths"][best]
        if best is not None
        else None,
        "best_ncc": values[best] if best is not None else None,
        "gate": DESIGN["ncc_gate"],
        "verdict": ("PASS" if values[best] >= DESIGN["ncc_gate"] else "FAIL")
        if best is not None
        else "INDETERMINATE",
        "indeterminate_reason": None
        if sufficient
        else "insufficient full-depth support or constant comparison pixels",
    }


def measure(source):
    meta = json.loads(source.cat(GEOMETRY + "/meta.json"))
    if not np.allclose(
        meta.get("scale", []), DESIGN["geometry_scale"], rtol=0, atol=1e-8
    ):
        raise ValueError("geometry scale differs from the fixed design")
    for channel in "xyz":
        raw = source.cat(f"{GEOMETRY}/{channel}.tif")
        with tifffile.TiffFile(io.BytesIO(raw)) as tiff:
            if (
                len(tiff.series) != 1
                or list(tiff.series[0].shape) != DESIGN["geometry_shape"]
                or tiff.series[0].dtype != np.float32
            ):
                raise ValueError("geometry planes differ from the fixed design")
    xyz = read_tifxyz(source.path(GEOMETRY))
    y, x, height, width = DESIGN["region_yxhw"]
    halo = DESIGN["normal_halo"]
    pm, valid = pointmap_from_tifxyz(
        xyz[y - halo : y + height + halo, x - halo : x + width + halo],
        level_div=2 ** DESIGN["raw_level"],
    )
    normals = surface_normals(pm, valid, sign=DESIGN["normal_sign"])
    inner = (slice(halo, -halo), slice(halo, -halo))
    reader = ChunkCachedZarrFetch(
        RAW, DESIGN["raw_level"], DESIGN["max_cache_bytes"], fs=source
    )
    reference = ChunkCachedZarrFetch(
        REFERENCE, DESIGN["reference_level"], DESIGN["max_cache_bytes"], fs=source
    )
    if (
        list(reader.shape) != DESIGN["raw_shape"]
        or list(reference.shape) != DESIGN["reference_shape"]
        or reader.dtype != np.dtype(DESIGN["source_dtype"])
        or reference.dtype != np.dtype(DESIGN["source_dtype"])
    ):
        raise ValueError("source volume shapes/dtypes differ from the fixed design")
    layers, stats, supported = sample_layers(
        pm[inner],
        valid[inner],
        normals[inner],
        reader,
        n_layers=DESIGN["layers"],
        k0=DESIGN["k0"],
        tile=DESIGN["tile"],
        group=DESIGN["group"],
        max_bbox_voxels=16 * 1024**2,
        group_max_voxels=32 * 1024**2,
        volume_shape=reader.shape,
        return_valid=True,
    )
    ry, rx, rh, rw = DESIGN["reference_region_yxhw"]
    depths = DESIGN["reference_depths"]
    bbox = (min(depths), max(depths) + 1, ry, ry + rh, rx, rx + rw)
    reference.warm([bbox])
    ref = reference(*bbox)
    refs = np.stack(
        [
            cv2.resize(
                ref[d - min(depths)].astype(np.float32),
                (width, height),
                interpolation=cv2.INTER_AREA,
            )
            for d in depths
        ]
    )
    result = compare_center(layers, supported, refs)
    return layers, supported, refs, {"sampling": stats, "comparison": result}


def run(plan_path, output):
    plan_path, plan, plan_hash = read_plan(plan_path)
    output = new_output(output, ROOT, plan_path)
    with publish_new(output) as staging:
        source = SnapshotSource(
            staging / "sources",
            max_total_bytes=DESIGN["max_download_bytes"],
            max_object_bytes=DESIGN["max_object_bytes"],
        )
        layers, supported, refs, result = measure(source)
        source.verify()
        _, final_plan, final_hash = read_plan(plan_path)
        if final_hash != plan_hash or final_plan != plan:
            raise ValueError("plan changed during measurement")
        for name, values in (
            ("layers.npy", layers),
            ("supported.npy", supported),
            ("references.npy", refs),
        ):
            np.save(staging / name, values, allow_pickle=False)
        report = {
            "protocol": PROTOCOL,
            "observed_utc": datetime.now(timezone.utc).isoformat(),
            "plan": plan,
            "plan_sha256": plan_hash,
            "source_objects": source.records,
            "download_bytes": source.total_bytes,
            "runtime": {
                **{name: version(name) for name in ("numpy", "scipy", "tifffile")},
                "opencv": cv2.__version__,
            },
            "python": sys.version,
            "array_files": {
                name: hashlib.sha256((staging / name).read_bytes()).hexdigest()
                for name in ("layers.npy", "supported.npy", "references.npy")
            },
            **result,
            "scope": "One fixed interior region; compatibility with a released render, not ink accuracy, independent scan registration, whole-scroll validation or depth-direction validation.",
        }
        (staging / "report.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.plan, args.out)
    except (OSError, ValueError, TypeError, MemoryError, RuntimeError) as exc:
        print(f"renderer revalidation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report["comparison"], indent=2, allow_nan=False))
    return 0 if report["comparison"]["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
