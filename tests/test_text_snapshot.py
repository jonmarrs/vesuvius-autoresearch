"""Bounded source captures keep their bytes and reject unsafe file replacements."""

import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.text_snapshot import Snapshot

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("limit", [-2, 0, True, 1.5, "128"])
def test_invalid_limits_are_refused_before_any_path_access(
    tmp_path, monkeypatch, limit
):
    monkeypatch.setattr(
        Path, "resolve", lambda *a, **k: pytest.fail("validate the limit before I/O")
    )
    with pytest.raises(ValueError, match="positive integer"):
        Snapshot.read(tmp_path / "source.txt", limit)


def test_capture_preserves_raw_utf8_bom_bytes_and_existing_verification(tmp_path):
    path = tmp_path / "source.txt"
    raw = b"\xef\xbb\xbf" + "κ".encode()
    path.write_bytes(raw)
    source = Snapshot.read(path, len(raw))
    assert source.text() == "κ"
    assert source.provenance() == {
        "path": str(path.resolve()),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    with pytest.raises(ValueError, match="exceeds"):
        Snapshot.read(path, len(raw) - 1)
    source.copy_into(tmp_path / "copy", path.name)
    assert (tmp_path / "copy/sources/source.txt").read_bytes() == raw
    source.verify()
    path.write_bytes(b"\xef\xbb\xbf" + "ω".encode())
    with pytest.raises(ValueError, match="changed"):
        source.verify()


def test_growth_after_descriptor_size_check_cannot_exceed_the_capture_limit(
    tmp_path, monkeypatch
):
    path = tmp_path / "source.txt"
    path.write_bytes(b"small")
    fstat = os.fstat
    changed = []

    def inspect(descriptor):
        info = fstat(descriptor)
        path.write_bytes(b"larger than the original file")
        changed.append(True)
        return info

    monkeypatch.setattr(os, "fstat", inspect)
    with pytest.raises(ValueError, match="exceeds"):
        Snapshot.read(path, 5)
    assert changed == [True]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_a_fifo_replacing_a_regular_source_cannot_block_capture(tmp_path):
    path = tmp_path / "source.txt"
    path.write_text("source")
    code = """
import os, sys
from pathlib import Path
from scripts.text_snapshot import Snapshot

path = Path(sys.argv[1])
original = Path.is_file
swapped = []

def is_file(self):
    regular = original(self)
    if self == path and regular:
        self.unlink()
        os.mkfifo(self)
        swapped.append(True)
    return regular

Path.is_file = is_file
try:
    Snapshot.read(path, 64)
except ValueError as exc:
    assert "regular file" in str(exc), exc
else:
    raise AssertionError("a FIFO was read as a text source")
assert swapped == [True]
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert stat.S_ISFIFO(path.stat().st_mode)


def test_the_descriptor_size_is_checked_before_any_bytes_are_read(
    tmp_path, monkeypatch
):
    """The descriptor's size refuses an oversized file before reading. Here `fstat` reports one byte over the limit
    while the file's bytes would fit, so only that size check can refuse it; the read-length check cannot."""
    path = tmp_path / "source.txt"
    path.write_bytes(b"small")
    fstat = os.fstat

    def oversized(descriptor):
        info = list(fstat(descriptor))
        info[stat.ST_SIZE] = 6
        return os.stat_result(info)

    monkeypatch.setattr(os, "fstat", oversized)
    with pytest.raises(ValueError, match="exceeds 5 bytes"):
        Snapshot.read(path, 5)
