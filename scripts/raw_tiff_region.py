"""Read a (z, y, x) region of a scroll volume stored as one uncompressed 16-bit TIFF per z slice, by HTTP byte ranges.

Only each row's x-window is fetched, many rows per request (multipart/byteranges). The raw 7.91 um slices of Scroll 1
(PHercParis4 `20230205180739`, 8096 x 7888, five-digit names) and Scroll 3 (PHerc332 `20231117143551`, 3400 x 3550,
four-digit names) were stored this way on 2026-10-23: little-endian, 16 bits, no compression, one strip. Each slice's
header is read and checked before its rows; any other layout is refused, never guessed.

Converted as villa's fibers-dataset generator made ScrollGT's cubes (/ 257, clipped, truncated), a 4 x 64 x 64 corner
of `s1_00497_01497_03997_256` and of `s3_00994_00494_01994_512` read this way equals the cube exactly (`check`).

  check  --cube STEM --tif CUBE_IMAGE.tif [--corner N]    compare the cube's N-voxel corner with the raw slices
"""

from __future__ import annotations

import argparse
import struct
import sys
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

VOLUMES: dict[str, dict[str, Any]] = {
    "s1": {
        "url": "https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/volumes/20230205180739",
        "shape": (14376, 7888, 8096),
        "digits": 5,
    },
    "s3": {
        "url": "https://dl.ash2txt.org/full-scrolls/Scroll3/PHerc332.volpkg/volumes/20231117143551",
        "shape": (9778, 3550, 3400),
        "digits": 4,
    },
}
HEADER_BYTES = 4096
PER_REQUEST = 200  # ranges per request: keeps the Range header near 5 KB


def parse_header(b: bytes) -> dict:
    """The first IFD of a classic little-endian TIFF: its geometry and single strip, or ValueError."""
    if b[:4] != b"II*\x00":
        raise ValueError("not a little-endian classic TIFF")
    off = struct.unpack("<I", b[4:8])[0]
    n = struct.unpack("<H", b[off : off + 2])[0]
    tags = {}
    for i in range(n):
        tag, typ, cnt, val = struct.unpack(
            "<HHII", b[off + 2 + 12 * i : off + 14 + 12 * i]
        )
        if typ == 3 and cnt == 1:
            val = struct.unpack("<H", b[off + 10 + 12 * i : off + 12 + 12 * i])[0]
        tags[tag] = (typ, cnt, val)
    width, height = tags[256][2], tags[257][2]
    bits, compression = tags[258][2], tags.get(259, (3, 1, 1))[2]
    offsets, counts = tags[273], tags[279]
    if bits != 16 or compression != 1 or tags.get(277, (3, 1, 1))[2] != 1:
        raise ValueError(
            f"not uncompressed single-channel 16-bit: bits {bits}, compression {compression}"
        )
    if offsets[1] != 1 or counts[1] != 1:
        raise ValueError(f"{offsets[1]} strips: only one strip is read")
    if counts[2] != width * height * 2:
        raise ValueError("the strip is not the whole image")
    return {"width": width, "height": height, "data_offset": offsets[2]}


def row_ranges(lo, hi, width: int, data_offset: int) -> list[tuple[int, int]]:
    """Inclusive byte ranges of each row's x-window, rows lo[0]..hi[0]-1, columns lo[1]..hi[1]-1."""
    (y0, x0), (y1, x1) = lo, hi
    return [
        (data_offset + 2 * (r * width + x0), data_offset + 2 * (r * width + x1) - 1)
        for r in range(y0, y1)
    ]


def parse_byteranges(
    body: bytes, content_type: str, content_range: str | None
) -> dict[tuple[int, int], bytes]:
    """{(start, end): bytes} from a 206 response, single-range or multipart/byteranges."""
    if not content_type.startswith("multipart/byteranges"):
        if not content_range or not content_range.startswith("bytes "):
            raise ValueError("a single-range response without Content-Range")
        a, b = (int(v) for v in content_range.split()[1].split("/")[0].split("-"))
        if len(body) != b - a + 1:
            raise ValueError("body length differs from Content-Range")
        return {(a, b): body}
    boundary = content_type.split("boundary=", 1)[1].strip().strip('"').encode()
    out: dict[tuple[int, int], bytes] = {}
    pos = 0
    marker = b"--" + boundary
    while True:
        pos = body.index(marker, pos) + len(marker)
        if body[pos : pos + 2] == b"--":
            return out
        head_end = body.index(b"\r\n\r\n", pos)
        headers = body[pos:head_end].decode("latin-1").split("\r\n")
        cr = next(h for h in headers if h.lower().startswith("content-range:"))
        a, b = (int(v) for v in cr.split()[2].split("/")[0].split("-"))
        start = head_end + 4
        out[(a, b)] = body[start : start + b - a + 1]
        pos = start + b - a + 1


def _get_ranges(
    url: str, ranges: list[tuple[int, int]]
) -> tuple[str, str | None, bytes]:
    spec = ",".join(f"{a}-{b}" for a, b in ranges)
    req = urllib.request.Request(url, headers={"Range": f"bytes={spec}"})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (fixed https URLs)
        if r.status != 206:
            raise ValueError(f"{url}: HTTP {r.status}, not a partial response")
        return (
            r.headers.get("Content-Type", ""),
            r.headers.get("Content-Range"),
            r.read(),
        )


def read_slice_window(
    url: str, lo, hi, get_ranges=_get_ranges, per_request: int = PER_REQUEST
) -> np.ndarray:
    """Rows lo[0]..hi[0]-1 and columns lo[1]..hi[1]-1 of one slice, as uint16."""
    ctype, crange, head = get_ranges(url, [(0, HEADER_BYTES - 1)])
    # A server clips a range past the end of a short file, so take the one part whatever its end.
    info = parse_header(next(iter(parse_byteranges(head, ctype, crange).values())))
    if hi[0] > info["height"] or hi[1] > info["width"] or min(lo) < 0:
        raise ValueError(
            f"{lo}-{hi} leaves the {info['height']} x {info['width']} slice"
        )
    ranges = row_ranges(lo, hi, info["width"], info["data_offset"])
    got: dict[tuple[int, int], bytes] = {}
    for i in range(0, len(ranges), per_request):
        ctype, crange, body = get_ranges(url, ranges[i : i + per_request])
        got.update(parse_byteranges(body, ctype, crange))
    rows = [np.frombuffer(got[r], "<u2") for r in ranges]
    return np.stack(rows)


def read_region(volume: str, lo, hi, cache: Path, get_ranges=_get_ranges) -> np.ndarray:
    """[lo, hi) (z, y, x) of VOLUMES[volume] as uint16, each slice's window cached in CACHE."""
    v = VOLUMES[volume]
    if any(a < 0 or b > s for a, b, s in zip(lo, hi, v["shape"], strict=True)):
        raise ValueError(f"{lo}-{hi} leaves the volume {v['shape']}")
    cache.mkdir(parents=True, exist_ok=True)
    out = np.empty(tuple(b - a for a, b in zip(lo, hi, strict=True)), "<u2")
    for i, z in enumerate(range(lo[0], hi[0])):
        f = cache / f"{z}_{lo[1]}_{lo[2]}_{hi[1]}_{hi[2]}.npy"
        if f.exists():
            out[i] = np.load(f)
            continue
        win = read_slice_window(
            f"{v['url']}/{z:0{v['digits']}d}.tif", lo[1:], hi[1:], get_ranges
        )
        tmp = f.with_suffix(".part.npy")
        np.save(tmp, win)
        tmp.rename(f)
        out[i] = win
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--cube", required=True)
    p.add_argument("--tif", type=Path, required=True)
    p.add_argument("--corner", type=int, default=64)
    p.add_argument("--depth", type=int, default=4)
    p.add_argument("--cache", type=Path, required=True)
    args = ap.parse_args(argv)
    import tifffile

    z, y, x = (int(v) for v in args.cube.split("_")[1:4])
    n, d = args.corner, args.depth
    raw = read_region(
        args.cube.split("_")[0], (z, y, x), (z + d, y + n, x + n), args.cache
    )
    got = np.clip(raw.astype(np.float64) / 257, 0, 255).astype(np.uint8)
    ref = tifffile.imread(args.tif)[:d, :n, :n]
    same = bool(np.array_equal(got, ref))
    print(
        f"{args.cube}: {'identical' if same else 'DIFFERS'} ({int((got != ref).sum())} of {ref.size} voxels differ)"
    )
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
