"""Measure one published canvas against the CT sampled on its tifxyz grid.

This is the check behind ScrollPrize/villa#2370, without retraining. A 512 px
level-0 window is read at level-2 spacing (4 px), the CT is sampled at those
tifxyz cells, and the shift is reported in level-0 pixels. The search is
±128 level-0 px except for the held-out w01 centre, whose shift is about
208 px, so that one window searches ±256.

    python scripts/probe_canvas_frame_shift.py w018
    python scripts/probe_canvas_frame_shift.py w01
    python scripts/probe_canvas_frame_shift.py w01-heldout

Nothing here is fetched from upstream Villa. The bytes come from the public
Hugging Face ink bucket and the public CT zarr used in that issue.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from repro.sota_data.canvas_shift import (  # noqa: E402
    fit_shift,
    level0_centers,
    measure_shift,
    resample_to_tifxyz,
    sample_tifxyz,
    sample_volume_trilinear,
)

CACHE = Path(os.environ.get("CANVAS_SHIFT_CACHE", "/tmp/canvas_shift_cache"))
HF = "https://huggingface.co/buckets/scrollprize/datasets/resolve/"
S3 = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
STRIDE = 4  # level-2 lattice, in level-0 pixels

# Published fits, level-0 canvas pixels: d = a + b*y + c*x.
# stantheman0128/vesuvius-hf65-alignment, the measurements cited by villa#2370.
W01_DY = (11.5100, 0.0042631, 0.0000060)
W01_DX = (11.8180, 0.0000025, -0.0038761)


def _fetch(url: str, rng: tuple[int, int] | None = None) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{url}|{rng}".encode()).hexdigest()
    path = CACHE / key[:2] / key
    if path.exists():
        return path.read_bytes()
    headers = {"Range": f"bytes={rng[0]}-{rng[1]}"} if rng else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
        if rng is not None and len(payload) != rng[1] - rng[0] + 1:
            raise RuntimeError(f"short read {len(payload)} for {url} {rng}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def _json(url: str) -> dict:
    return json.loads(_fetch(url))


class _Tiff:
    """Uncompressed float32 strips, read by HTTP range."""

    def __init__(self, url: str):
        self.url = url
        head = _fetch(url, (0, 15))
        bo = "<" if head[:2] == b"II" else ">"
        big = struct.unpack(bo + "H", head[2:4])[0] == 43
        offset = struct.unpack(
            bo + ("Q" if big else "I"), head[8:16] if big else head[4:8]
        )[0]
        ifd = _fetch(url, (offset, offset + 4095))
        if big:
            count, start, entry, value_at, pointer = (
                struct.unpack(bo + "Q", ifd[:8])[0],
                8,
                20,
                12,
                8,
            )
        else:
            count, start, entry, value_at, pointer = (
                struct.unpack(bo + "H", ifd[:2])[0],
                2,
                12,
                8,
                4,
            )
        kinds = {3: ("H", 2), 4: ("I", 4), 16: ("Q", 8)}
        tags = {}
        for index in range(count):
            raw = ifd[start + index * entry : start + (index + 1) * entry]
            tag, typ = struct.unpack(bo + "HH", raw[:4])
            if typ not in kinds:
                continue
            fmt, size = kinds[typ]
            nvals = struct.unpack(bo + ("Q" if big else "I"), raw[4:value_at])[0]
            if nvals * size <= pointer:
                tags[tag] = struct.unpack(
                    bo + fmt * nvals, raw[value_at : value_at + nvals * size]
                )
            else:
                pointer_at = struct.unpack(
                    bo + ("Q" if big else "I"), raw[value_at : value_at + pointer]
                )[0]
                blob = _fetch(url, (pointer_at, pointer_at + nvals * size - 1))
                tags[tag] = struct.unpack(bo + fmt * nvals, blob)
        self.bo = bo
        self.width, self.height = tags[256][0], tags[257][0]
        self.rows_per_strip = tags.get(278, (self.height,))[0]
        self.strip_offsets = tags[273]
        self.dtype = np.dtype(bo + "f4")

    def rows(self, r0: int, r1: int, c0: int, c1: int) -> np.ndarray:
        out = np.full((r1 - r0, c1 - c0), np.nan, np.float32)
        rr0, rr1 = max(r0, 0), min(r1, self.height)
        cc0, cc1 = max(c0, 0), min(c1, self.width)
        if rr0 >= rr1 or cc0 >= cc1:
            return out
        span = (cc1 - cc0) * 4
        runs: list[list] = []
        for row in range(rr0, rr1):
            strip = row // self.rows_per_strip
            start = (
                self.strip_offsets[strip]
                + ((row - strip * self.rows_per_strip) * self.width + cc0) * 4
            )
            if runs and start == runs[-1][1]:
                runs[-1][1] = start + span
                runs[-1][2].append(row)
            else:
                runs.append([start, start + span, [row]])
        for start, stop, rows in runs:
            blob = _fetch(self.url, (start, stop - 1))
            for index, row in enumerate(rows):
                out[row - r0, cc0 - c0 : cc1 - c0] = np.frombuffer(
                    blob[index * span : (index + 1) * span], self.dtype
                )
        return out


def _zarr_region(
    base: str, level: int, y0: int, y1: int, x0: int, x1: int, z: int
) -> np.ndarray:
    import numcodecs

    meta = _json(f"{base}/{level}/.zarray")
    depth, height, width = meta["shape"]
    ch_z, ch_y, ch_x = meta["chunks"]
    sep = meta.get("dimension_separator", ".")
    codec = numcodecs.get_codec(meta["compressor"]) if meta["compressor"] else None
    out = np.zeros((y1 - y0, x1 - x0), np.float32)
    cz, lz = divmod(z, ch_z)
    for cy in range(
        max(0, y0 // ch_y), min((height - 1) // ch_y, (y1 - 1) // ch_y) + 1
    ):
        for cx in range(
            max(0, x0 // ch_x), min((width - 1) // ch_x, (x1 - 1) // ch_x) + 1
        ):
            raw = _fetch(f"{base}/{level}/{cz}{sep}{cy}{sep}{cx}")
            decoded = codec.decode(raw) if codec else raw
            chunk = np.frombuffer(decoded, np.uint8).reshape(meta["chunks"])
            gy0, gx0 = cy * ch_y, cx * ch_x
            sy0, sy1 = max(y0, gy0), min(y1, gy0 + ch_y, height)
            sx0, sx1 = max(x0, gx0), min(x1, gx0 + ch_x, width)
            out[sy0 - y0 : sy1 - y0, sx0 - x0 : sx1 - x0] = chunk[
                lz, sy0 - gy0 : sy1 - gy0, sx0 - gx0 : sx1 - gx0
            ]
    del depth, width
    return out


def _canvas_on_level2(
    base: str, canvas_level: int, i0: int, i1: int, j0: int, j1: int
) -> np.ndarray:
    """Slice 32 on the level-2 lattice. Level 1 is averaged 2x2, as w018 requires."""
    if canvas_level == 2:
        return _zarr_region(base, 2, i0, i1, j0, j1, 32)
    if canvas_level != 1:
        raise ValueError(f"canvas level {canvas_level} is not 1 or 2")
    fine = _zarr_region(base, 1, 2 * i0, 2 * i1, 2 * j0, 2 * j1, 32)
    height, width = i1 - i0, j1 - j0
    return (
        fine[: height * 2, : width * 2].reshape(height, 2, width, 2).mean(axis=(1, 3))
    )


def _volume_at(base: str, points: np.ndarray) -> np.ndarray:
    """Trilinear level-2 samples. ``points`` is level-0 ZYX, shape (N, 3)."""
    meta = _json(f"{base}/2/.zarray")
    assert meta["compressor"] is None and tuple(meta["chunks"]) == (128, 128, 128)
    factor = 4
    continuous = (points - (factor - 1) / 2.0) / factor
    finite = np.all(np.isfinite(points), axis=1)
    base_i = np.floor(continuous).astype(np.int64)
    corners = np.array([(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)])
    wanted = base_i[finite][:, None, :] + corners[None, :, :]
    wanted = wanted.reshape(-1, 3)
    depth, height, width = meta["shape"]
    inside = np.all((wanted >= 0) & (wanted < (depth, height, width)), axis=1)
    wanted = wanted[inside]
    if len(wanted) == 0:
        return np.full(len(points), np.nan, np.float32)
    lo = wanted.min(0)
    hi = wanted.max(0)
    box = np.zeros(tuple(hi - lo + 1), np.uint8)
    cz, cy, cx = (wanted // 128).T
    lz, ly = wanted[:, 0] % 128, wanted[:, 1] % 128
    nc = (np.array(meta["shape"]) + 127) // 128
    key = ((cz * nc[1] + cy) * nc[2] + cx) * 128 + lz
    order = np.argsort(key, kind="stable")
    keys, starts = np.unique(key[order], return_index=True)
    ys = ly[order]
    ymin = np.minimum.reduceat(ys, starts)
    ymax = np.maximum.reduceat(ys, starts)
    sep = meta.get("dimension_separator", "/")
    for ck, zslice, y_a, y_b in zip(keys // 128, keys % 128, ymin, ymax, strict=True):
        x = int(ck) % nc[2]
        y = (int(ck) // nc[2]) % nc[1]
        z = int(ck) // (nc[2] * nc[1])
        url = f"{base}/2/{z}{sep}{y}{sep}{x}"
        start = int(zslice) * 16384 + int(y_a) * 128
        stop = int(zslice) * 16384 + (int(y_b) + 1) * 128 - 1
        blob = _fetch(url, (start, stop))
        flat = np.arange(start, start + len(blob))
        vz, vy, vx = flat // 16384, (flat // 128) % 128, flat % 128
        gz = z * 128 + vz - lo[0]
        gy = y * 128 + vy - lo[1]
        gx = x * 128 + vx - lo[2]
        ok = (
            (gz >= 0)
            & (gy >= 0)
            & (gx >= 0)
            & (gz < box.shape[0])
            & (gy < box.shape[1])
            & (gx < box.shape[2])
        )
        box[gz[ok], gy[ok], gx[ok]] = np.frombuffer(blob, np.uint8)[ok]
    # The cropped box's voxel 0 is full-volume voxel ``lo``. Shift the level-0
    # points so sample_volume_trilinear indexes the crop.
    return sample_volume_trilinear(box, points - lo * factor, level=2)


def _surface(
    segment: dict, i0: int, i1: int, j0: int, j1: int
) -> tuple[np.ndarray, np.ndarray]:
    ii = np.arange(i0, i1)
    jj = np.arange(j0, j1)
    rows = level0_centers(ii, STRIDE)
    cols = level0_centers(jj, STRIDE)
    meta = _json(segment["tifxyz"] + "/meta.json")
    scale_y = float(np.float32(meta["scale"][1]))
    scale_x = float(np.float32(meta["scale"][0]))
    stored_r = rows * scale_y
    stored_c = cols * scale_x
    r0, r1 = int(np.floor(stored_r.min())) - 1, int(np.floor(stored_r.max())) + 3
    c0, c1 = int(np.floor(stored_c.min())) - 1, int(np.floor(stored_c.max())) + 3
    planes = {
        axis: _Tiff(segment["tifxyz"] + f"/{axis}.tif").rows(r0, r1, c0, c1)
        for axis in "xyz"
    }
    zyx = sample_tifxyz(
        planes["z"],
        planes["y"],
        planes["x"],
        stored_r - r0,
        stored_c - c0,
        1.0,
        1.0,
    )
    # The crop is indexed from 0, and sample_tifxyz with scale 1 treats ``rows``
    # as stored-grid coordinates. ``stored_r - r0`` is that index.
    values = _volume_at(segment["volume"], zyx.reshape(-1, 3))
    surface = values.reshape(len(ii), len(jj))
    finite = np.isfinite(zyx).all(axis=-1) & np.isfinite(surface)
    return surface, finite


def _published_w01(y0: float, x0: float) -> tuple[float, float]:
    ay, by, cy = W01_DY
    ax, bx, cx = W01_DX
    return ay + by * y0 + cy * x0, ax + bx * y0 + cx * x0


def measure_window(
    segment: dict, y0: int, x0: int, size: int = 512, margin: int = 128
) -> dict:
    """``y0, x0, size, margin`` are level-0 pixels. ``margin`` is the search radius."""
    if size % STRIDE or margin % STRIDE or y0 % STRIDE or x0 % STRIDE:
        raise ValueError("window edges must sit on the level-2 lattice")
    height = size // STRIDE
    radius = margin // STRIDE
    i0 = y0 // STRIDE
    j0 = x0 // STRIDE
    canvas = _canvas_on_level2(
        segment["canvas"],
        segment["canvas_level"],
        i0 - radius,
        i0 + height + radius,
        j0 - radius,
        j0 + height + radius,
    )
    surface, finite = _surface(
        segment, i0 - radius, i0 + height + radius, j0 - radius, j0 + height + radius
    )
    surface = np.where(finite, surface, np.nan).astype(np.float32)
    origin = level0_centers(np.array([i0 - radius, j0 - radius]), STRIDE)
    found = measure_shift(
        surface,
        canvas.astype(np.float32),
        (radius, radius, height, height),
        max_shift=radius,
        px_scale=STRIDE,
        origin=(float(origin[0]), float(origin[1])),
    )
    corrected = resample_to_tifxyz(
        np.where(np.isfinite(canvas), canvas, 0).astype(np.float32),
        ay=float(found["dy"]),
        sy=0.0,
        ax=float(found["dx"]),
        sx=0.0,
    )
    again = measure_shift(
        surface,
        corrected,
        (radius, radius, height, height),
        max_shift=radius,
        px_scale=STRIDE,
        origin=(float(origin[0]), float(origin[1])),
    )
    centre_y = float(found["y0"])
    centre_x = float(found["x0"])
    return {
        "y0": y0,
        "x0": x0,
        "centre": (centre_y, centre_x),
        "dy0": float(found["dy0"]),
        "dx0": float(found["dx0"]),
        "ncc": float(found["ncc"]),
        "after_dy0": float(again["dy0"]),
        "after_dx0": float(again["dx0"]),
        "after_ncc": float(again["ncc"]),
        "finite": float(finite.mean()),
        "canvas": canvas,
        "surface": np.where(finite, surface, 0),
        "corrected": corrected,
        "radius": radius,
        "height": height,
    }


def _checker(canvas: np.ndarray, surface: np.ndarray, block: int = 8) -> np.ndarray:
    def _norm(image: np.ndarray) -> np.ndarray:
        finite = image[np.isfinite(image)]
        if finite.size:
            pct = np.percentile(finite, [2, 98])
            lo, hi = float(pct[0]), float(pct[1])
        else:
            lo, hi = 0.0, 1.0
        scaled = np.clip((image - lo) / max(hi - lo, 1e-6), 0, 1)
        return (scaled * 255).astype(np.uint8)

    left, right = _norm(canvas), _norm(surface)
    yy, xx = np.indices(left.shape)
    pick = ((yy // block) + (xx // block)) % 2 == 0
    return np.where(pick, left, right)


def _write_overlay(path: Path, before: np.ndarray, after: np.ndarray) -> None:
    import cv2

    path.parent.mkdir(parents=True, exist_ok=True)
    gap = np.full((before.shape[0], 8), 255, np.uint8)
    cv2.imwrite(str(path), np.concatenate([before, gap, after], axis=1))


W018 = {
    "canvas": HF + "ink/1667/w018_20240304144031_2um/w018_20240304144031_2um.zarr",
    "tifxyz": HF + "ink/1667/w018_20240304144031_2um",
    "volume": S3 + "PHerc1667/volumes/20251217075048-2.399um-0.2m-78keV-masked.zarr",
    "canvas_level": 1,
}
W01 = {
    "canvas": HF + "ink/phercparis4/w01_20230702185753_r15/w01_20230702185753_r15.zarr",
    "tifxyz": HF + "ink/phercparis4/w01_20230702185753_r15",
    "volume": S3 + "PHercParis4/volumes/20260411134726-2.400um-0.2m-78keV-masked.zarr",
    "canvas_level": 2,
}

# Centres whose published w01 shift stays inside ±128, plus the held-out centre.
W01_WINDOWS = (
    ("inside-a", 14080 - 256, 16128 - 256, 128),
    ("inside-b", 18000 - 256, 16128 - 256, 128),
    ("inside-c", 22000 - 256, 16128 - 256, 128),
    ("inside-d", 18000 - 256, 28000 - 256, 128),
)
W01_HELDOUT = ("heldout", 46016 - 256, 27008 - 256, 256)


def _report(name: str, row: dict, expected: tuple[float, float] | None) -> dict:
    print(
        f"{name} centre ({row['centre'][0]:.1f}, {row['centre'][1]:.1f}) "
        f"measured ({row['dy0']:.2f}, {row['dx0']:.2f}) ncc {row['ncc']:.3f} "
        f"after ({row['after_dy0']:.2f}, {row['after_dx0']:.2f}) ncc {row['after_ncc']:.3f} "
        f"finite {row['finite']:.3f}"
        + (f" expected ({expected[0]:.2f}, {expected[1]:.2f})" if expected else ""),
        flush=True,
    )
    return {
        "name": name,
        "centre_y": row["centre"][0],
        "centre_x": row["centre"][1],
        "dy0": row["dy0"],
        "dx0": row["dx0"],
        "ncc": row["ncc"],
        "after_dy0": row["after_dy0"],
        "after_dx0": row["after_dx0"],
        "after_ncc": row["after_ncc"],
        "expected_dy": None if expected is None else expected[0],
        "expected_dx": None if expected is None else expected[1],
    }


def _overlay(row: dict, path: Path) -> None:
    r, h = row["radius"], row["height"]
    core = np.s_[r : r + h, r : r + h]
    before = _checker(row["canvas"][core], row["surface"][core])
    after = _checker(row["corrected"][core], row["surface"][core])
    _write_overlay(path, before, after)


def main(argv: list[str] | None = None) -> int:
    choice = (argv or sys.argv[1:])[:1] or ["all"]
    which = choice[0]
    artifact = Path(os.environ.get("CANVAS_SHIFT_ARTIFACTS", "/opt/cursor/artifacts"))
    rows = []
    if which in ("w018", "all"):
        row = measure_window(W018, 16896, 36352, 512, 128)
        rows.append(_report("w018 r0", row, (-19.7, -19.7)))
        _overlay(row, artifact / "w018_before_after.png")
    if which in ("w01", "all"):
        measured = []
        first = None
        for name, y0, x0, margin in W01_WINDOWS:
            row = measure_window(W01, y0, x0, 512, margin)
            expected = _published_w01(*row["centre"])
            rows.append(_report(f"w01 {name}", row, expected))
            measured.append(
                {
                    "y": row["centre"][0],
                    "x": row["centre"][1],
                    "dy": row["dy0"],
                    "dx": row["dx0"],
                }
            )
            if first is None:
                first = row
        fitted = fit_shift(measured)
        print(
            "w01 fit "
            f"dy = {fitted['ay']:.4f} + {fitted['sy']:.6g}*y + {fitted['cy']:.6g}*x, "
            f"dx = {fitted['ax']:.4f} + {fitted['cx']:.6g}*y + {fitted['sx']:.6g}*x "
            f"model {fitted['model']}",
            flush=True,
        )
        print(
            "w01 published slopes dy/dy "
            f"{W01_DY[1]:.6g} (cross {W01_DY[2]:.6g}), dx/dx {W01_DX[2]:.6g} (cross {W01_DX[1]:.6g})",
            flush=True,
        )
        if first is not None:
            _overlay(first, artifact / "w01_before_after.png")
        rows.append(
            {
                "name": "w01-fit",
                **{
                    key: fitted[key]
                    for key in ("model", "ay", "sy", "cy", "ax", "cx", "sx")
                },
            }
        )
    if which in ("w01-heldout", "all"):
        name, y0, x0, margin = W01_HELDOUT
        row = measure_window(W01, y0, x0, 512, margin)
        rows.append(_report("w01 held-out", row, (207.68, -92.86)))
        _overlay(row, artifact / "w01_heldout_before_after.png")
    if which not in ("w018", "w01", "w01-heldout", "all"):
        print(
            "usage: probe_canvas_frame_shift.py [w018|w01|w01-heldout|all]",
            file=sys.stderr,
        )
        return 2
    out = artifact / "canvas_shift_real.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = []
    if out.exists() and which != "all":
        previous = json.loads(out.read_text()).get("rows", [])
        previous = [
            item
            for item in previous
            if item.get("name") != which
            and not str(item.get("name", "")).startswith(which + " ")
            and not str(item.get("name", "")).startswith(which + "-")
        ]
    out.write_text(json.dumps({"rows": previous + rows}, indent=2))
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
