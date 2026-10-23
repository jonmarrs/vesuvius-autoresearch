"""scripts/raw_tiff_region.py against synthetic slices served by a fake range server, offline."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import raw_tiff_region as rt  # noqa: E402


def _tiff(arr: np.ndarray, **kw) -> bytes:
    import tifffile

    buf = io.BytesIO()
    tifffile.imwrite(buf, arr, rowsperstrip=arr.shape[0], **kw)
    return buf.getvalue()


def _server(files: dict[str, bytes], multipart_from: int = 2):
    """get_ranges for FILES: one range -> a single-range 206, more -> multipart/byteranges, as nginx answers."""
    calls = []

    def get_ranges(url, ranges):
        calls.append((url, len(ranges)))
        data = files[url]
        ranges = [
            (a, min(b, len(data) - 1)) for a, b in ranges
        ]  # clipped at the end, as HTTP servers do
        if len(ranges) < multipart_from:
            ((a, b),) = ranges
            return "image/tiff", f"bytes {a}-{b}/{len(data)}", data[a : b + 1]
        boundary = "0000000000000000042"
        parts = [
            f"\r\n--{boundary}\r\nContent-Type: image/tiff\r\nContent-Range: bytes {a}-{b}/{len(data)}\r\n\r\n".encode()
            + data[a : b + 1]
            for a, b in ranges
        ]
        return (
            f"multipart/byteranges; boundary={boundary}",
            None,
            b"".join(parts) + f"\r\n--{boundary}--\r\n".encode(),
        )

    return get_ranges, calls


def test_the_header_is_parsed_and_checked():
    arr = np.arange(30 * 40, dtype="<u2").reshape(30, 40)
    info = rt.parse_header(_tiff(arr)[: rt.HEADER_BYTES])
    assert (info["width"], info["height"]) == (40, 30)
    with pytest.raises(ValueError, match="bits 8"):
        rt.parse_header(_tiff(arr.astype(np.uint8))[: rt.HEADER_BYTES])
    with pytest.raises(ValueError, match="compression 8"):
        rt.parse_header(_tiff(arr, compression="zlib")[: rt.HEADER_BYTES])
    import tifffile

    buf = io.BytesIO()
    tifffile.imwrite(buf, arr, rowsperstrip=10)
    with pytest.raises(ValueError, match="3 strips"):
        rt.parse_header(buf.getvalue()[: rt.HEADER_BYTES])
    with pytest.raises(ValueError):
        rt.parse_header(b"MM\x00*" + bytes(100))  # big-endian


def test_a_slice_window_is_exact_in_single_and_multipart_responses():
    arr = np.random.default_rng(3).integers(0, 65535, (50, 70), dtype=np.uint16)
    files = {"u/0.tif": _tiff(arr)}
    for per in (1, 7, 200):
        get, calls = _server(files)
        win = rt.read_slice_window("u/0.tif", (5, 11), (33, 60), get, per_request=per)
        assert np.array_equal(win, arr[5:33, 11:60])
        assert max(n for _, n in calls) <= max(per, 1) and calls[0] == ("u/0.tif", 1)
    with pytest.raises(ValueError):
        rt.read_slice_window("u/0.tif", (0, 0), (51, 10), _server(files)[0])


def test_parse_byteranges_refuses_a_short_single_part():
    with pytest.raises(ValueError):
        rt.parse_byteranges(b"abc", "image/tiff", "bytes 0-9/100")
    with pytest.raises(ValueError):
        rt.parse_byteranges(b"abc", "image/tiff", None)


def test_read_region_stacks_slices_and_caches_them(tmp_path, monkeypatch):
    vol = np.random.default_rng(4).integers(0, 65535, (6, 20, 30), dtype=np.uint16)
    files = {f"base/{z:04d}.tif": _tiff(vol[z]) for z in range(6)}
    monkeypatch.setitem(
        rt.VOLUMES, "sx", {"url": "base", "shape": (6, 20, 30), "digits": 4}
    )
    get, calls = _server(files)
    got = rt.read_region("sx", (1, 2, 3), (5, 19, 29), tmp_path, get)
    assert np.array_equal(got, vol[1:5, 2:19, 3:29])
    n = len(calls)
    assert np.array_equal(
        rt.read_region("sx", (1, 2, 3), (5, 19, 29), tmp_path, get), got
    )
    assert len(calls) == n  # every slice from the cache
    with pytest.raises(ValueError):
        rt.read_region("sx", (0, 0, 0), (7, 1, 1), tmp_path, get)


def test_the_volumes_are_the_7p91um_scans():
    assert rt.VOLUMES["s1"]["url"].endswith("PHercParis4.volpkg/volumes/20230205180739")
    assert rt.VOLUMES["s3"]["url"].endswith("PHerc332.volpkg/volumes/20231117143551")
    assert (
        rt.VOLUMES["s1"]["shape"] == (14376, 7888, 8096)
        and rt.VOLUMES["s1"]["digits"] == 5
    )
    assert (
        rt.VOLUMES["s3"]["shape"] == (9778, 3550, 3400)
        and rt.VOLUMES["s3"]["digits"] == 4
    )
