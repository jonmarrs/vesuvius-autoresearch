"""Read a zip checkpoint's pickle without running it, and refuse every other checkpoint.

A pickle can only call what it imports: GLOBAL and STACK_GLOBAL name a module attribute, INST and OBJ build a
class (INST names it inline), and EXT1/2/4 fetch one from the copyreg registry. This walks the opcodes with
pickletools (nothing is unpickled), lists every name imported, and refuses the file if any is outside the
allowlist or if it uses the extension registry. A file that passes can only rebuild tensors, plain containers
and the classes allowed, so a full torch.load of it runs no other code.

torch's own weights-only unpickler is the stronger check where it works; it cannot rebuild a
collections.defaultdict, which training checkpoints with optimizer state carry.

torch.load treats a file as a zip archive only when it starts with the zip local-file signature.
Anything else — an old non-zip pickle, a tar, a pickle placed in front of a zip — is refused
outright. Convert that checkpoint offline to the zip format before loading it. A zip is audited
by reading every member ``torch._C.PyTorchFileReader`` would hand to the unpickler. A suffix of
``.pkl`` matches in any case. Two members whose names match ignoring case are refused, and so is
a file whose central-directory offset was shifted or which has bytes before or after the archive.
Python's zipfile and torch's reader do not agree on those files.

``villa/deprecated/ink-detection/inference_timesformer.py`` loads with ``weights_only=False`` and
is not modified. That load is safe only through ``run_gp_timesformer.sh``: the wrapper copies the
checkpoint, then checksums, audits, and infers that copy. The SHA-256 pin is
``93f56e569e1f4c66b71112c41985b64445b5245ff1fb610e44f495c2a0aee36f`` on the exact ``$CK``
(``villa/ink-detection/timesformer_weights.ckpt``).

usage: audit_pickle.py CHECKPOINT [--allow MODULE.NAME]...
"""

from __future__ import annotations

import io
import json
import pickletools
import re
import struct
import sys
import zipfile
from pathlib import Path

from vesuvius_autoresearch.core.checkpoint_refusal import NON_ZIP_CHECKPOINT

# what torch.save writes for tensors and state dicts
BASE = {
    "torch._utils._rebuild_tensor_v2",
    "torch._utils._rebuild_parameter",
    "collections.OrderedDict",
    "builtins.dict",
    "__builtin__.dict",
}
STORAGE = re.compile(r"^torch\.[A-Za-z]*Storage$")
REFUSED_OPS = {"EXT1", "EXT2", "EXT4"}
# A torch zip starts with a local-file header. A central directory that zipfile had to
# slide into place, or any bytes before the first member or after the end record, is a
# different archive than the one torch's reader opens. Those files are refused.
_ZIP_LOCAL = b"PK\x03\x04"
_EOCD = b"PK\x05\x06"
SHIFTED_ZIP = (
    "refusing a zip checkpoint whose offsets were shifted"
    " or that has bytes before or after the archive"
)
DUPLICATE_MEMBER = (
    "refusing a zip checkpoint with more than one member of the same name"
)
# A global name is short. A longer counted string is skipped instead of copied.
_MAX_ARG_BYTES = 64 * 1024
# A counted payload this large is not a name. The scan seeks past it.
_SKIPPED = object()
# Length-prefixed arguments. The format reads the count; the body may be skipped.
_COUNTED = {
    "bytes1": ("<B", 1),
    "string1": ("<B", 1),
    "unicodestring1": ("<B", 1),
    "bytes4": ("<I", 4),
    "unicodestring4": ("<I", 4),
    "string4": ("<i", 4),
    "bytes8": ("<Q", 8),
    "bytearray8": ("<Q", 8),
    "unicodestring8": ("<Q", 8),
}
_LINE_ARGS = {"stringnl", "stringnl_noescape", "unicodestringnl"}


class _NotZip(Exception):
    """The file does not start with a zip local-file header."""


class _AmbiguousZip(Exception):
    """zipfile and torch's reader would not open the same bytes."""


class _DuplicateNames(Exception):
    """Two members compare equal when case is ignored."""


class _BadZip(Exception):
    """The leading bytes look like a zip, but the archive cannot be read."""


class _UnreadablePickle(Exception):
    """A pickle started and did not reach STOP. The unread tail is not storage."""


def _eocd(path: Path) -> tuple[int, int, int]:
    """The last end-of-central-directory record: its offset, the recorded
    central-directory offset, and the comment length."""
    size = path.stat().st_size
    span = min(size, 22 + 65535)
    with path.open("rb") as handle:
        handle.seek(size - span)
        tail = handle.read(span)
    index = tail.rfind(_EOCD)
    if index < 0 or index + 22 > len(tail):
        raise _AmbiguousZip(path.name)
    cd_offset, comment_len = struct.unpack_from("<IH", tail, index + 16)
    return size - span + index, cd_offset, comment_len


def _refuse_shifted(path: Path, archive: zipfile.ZipFile) -> None:
    """Refuse a zipfile that slid its offsets, or a file with extra bytes.

    ``start_dir`` is where zipfile actually found the central directory. The
    end record stores that offset before any such slide. A prepended or
    appended archive makes the two differ; bytes after the end record do not,
    so the file length is checked as well. The first member of a torch zip
    starts at offset 0.
    """
    eocd, cd_offset, comment_len = _eocd(path)
    if cd_offset == 0xFFFFFFFF or archive.start_dir != cd_offset:
        raise _AmbiguousZip(path.name)
    if eocd + 22 + comment_len != path.stat().st_size:
        raise _AmbiguousZip(path.name)
    infos = archive.infolist()
    if infos and min(info.header_offset for info in infos) != 0:
        raise _AmbiguousZip(path.name)


def _refuse_duplicates(infos) -> None:
    seen: set[str] = set()
    for info in infos:
        key = info.filename.casefold()
        if key in seen:
            raise _DuplicateNames(info.filename)
        seen.add(key)


def _torch_pickles(path: Path) -> list[tuple[str, bytes]]:
    """The pickle bytes ``PyTorchFileReader.get_record`` returns.

    Those are the bytes ``torch.load`` unpickles. The record list is also where
    a repeated name is visible: ``get_all_records`` yields it once per entry.
    """
    import torch

    try:
        reader = torch._C.PyTorchFileReader(str(path))
        records = list(reader.get_all_records())
    except (OSError, RuntimeError) as exc:
        raise _BadZip(path.name) from exc
    by_key: dict[str, str] = {}
    for record in records:
        key = record.casefold()
        if key in by_key:
            raise _DuplicateNames(record)
        by_key[key] = record
    return [
        (record, bytes(reader.get_record(record)))
        for key, record in by_key.items()
        if key.endswith(".pkl")
    ]


def pickles(path: Path) -> list[tuple[str, bytes]]:
    """Every ``.pkl`` record, in any case, as torch's reader will execute it.

    A file is a torch zip only when it starts with the local-file signature,
    zipfile did not shift the central directory, and nothing is prepended or
    appended. Duplicate names, compared without regard to case, are refused
    from the central directory and again from the reader's record list. The
    pickle bytes themselves come from ``get_record``, not from ``zipfile``.
    """
    with path.open("rb") as handle:
        signature = handle.read(len(_ZIP_LOCAL))
    if signature != _ZIP_LOCAL:
        raise _NotZip(path.name)
    try:
        with zipfile.ZipFile(path) as archive:
            _refuse_shifted(path, archive)
            _refuse_duplicates(archive.infolist())
    except _AmbiguousZip:
        raise
    except _DuplicateNames:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError) as exc:
        raise _BadZip(path.name) from exc
    return _torch_pickles(path)


def _stream_of(data: bytes | io.BufferedIOBase) -> tuple[io.BufferedIOBase, int]:
    """A seekable stream and how many bytes it holds."""
    if isinstance(data, (bytes, bytearray)):
        return io.BytesIO(data), len(data)
    pos = data.tell()
    data.seek(0, io.SEEK_END)
    end = data.tell()
    data.seek(pos)
    return data, end


def _discard_line(stream: io.BufferedIOBase, limit: int) -> None:
    """Drop the rest of a line without keeping it."""
    while stream.tell() < limit:
        chunk = stream.read(min(_MAX_ARG_BYTES, limit - stream.tell()))
        if not chunk:
            return
        newline = chunk.find(b"\n")
        if newline >= 0:
            extra = len(chunk) - newline - 1
            if extra:
                stream.seek(-extra, io.SEEK_CUR)
            return


def _bounded_line(stream: io.BufferedIOBase, limit: int, reader) -> str | object:
    """One newline-terminated argument. A line past the cap is not kept."""
    start = stream.tell()
    seen = 0
    while seen <= _MAX_ARG_BYTES and stream.tell() < limit:
        byte = stream.read(1)
        if not byte:
            break
        seen += 1
        if byte == b"\n":
            stream.seek(start)
            return reader(stream)
    _discard_line(stream, limit)
    return _SKIPPED


def _read_arg(stream: io.BufferedIOBase, opcode, limit: int):
    """The argument of one opcode. A long counted body is seeked past, not copied."""
    desc = opcode.arg
    if desc is None:
        return None
    counted = _COUNTED.get(desc.name)
    if counted is not None:
        fmt, width = counted
        start = stream.tell()
        raw = stream.read(width)
        if len(raw) != width:
            raise ValueError("short argument length")
        length = struct.unpack(fmt, raw)[0]
        if length < 0 or stream.tell() + length > limit:
            raise ValueError("argument length runs past the file")
        if length > _MAX_ARG_BYTES:
            stream.seek(length, io.SEEK_CUR)
            return _SKIPPED
        stream.seek(start)
        return desc.reader(stream)
    if desc.name in _LINE_ARGS:
        return _bounded_line(stream, limit, desc.reader)
    if desc.name == "stringnl_noescape_pair":
        # GLOBAL carries the module and the attribute as one argument.
        read = pickletools.stringnl_noescape.reader
        first = _bounded_line(stream, limit, read)
        second = _bounded_line(stream, limit, read)
        if first is _SKIPPED or second is _SKIPPED:
            return _SKIPPED
        return f"{first} {second}"
    return desc.reader(stream)


def _read_pickle(stream: io.BufferedIOBase, limit: int) -> tuple[str, list]:
    """One pickle. ``overlong`` means a FRAME's declared end is past its STOP.

    pickle.load of a frame reads the whole frame before the opcodes run, so the
    next load starts at the frame's end and never sees the bytes after STOP.
    Those bytes are not a later pickle this scan can count.
    """
    ops = []
    frame_ends: list[int] = []
    start = stream.tell()
    if start >= limit:
        return "end", []
    try:
        while stream.tell() < limit:
            pos = stream.tell()
            code = stream.read(1)
            if not code:
                raise ValueError("pickle exhausted before seeing STOP")
            opcode = pickletools.code2op.get(code.decode("latin-1"))
            if opcode is None:
                raise ValueError(f"unknown opcode {code!r}")
            arg = _read_arg(stream, opcode, limit)
            ops.append((opcode, arg, pos))
            if opcode.name == "FRAME":
                frame_ends.append(stream.tell() + int(arg))
            if opcode.name == "STOP":
                if any(end > stream.tell() for end in frame_ends):
                    return "overlong", ops
                return "done", ops
        raise ValueError("pickle exhausted before seeing STOP")
    except Exception:
        if not ops and stream.tell() == start:
            return "end", []
        return "error", ops


def _pickle_streams(data: bytes | io.BufferedIOBase):
    """Each pickle in ``data``.

    pickletools stops at the first STOP, so a member that holds another pickle
    after that is walked too. A parse error refuses the member: opcodes already
    read are yielded first, so a name already seen is not dropped. A frame whose
    declared end is past its STOP is refused too, because the next load resumes
    at the frame's end.
    """
    stream, limit = _stream_of(data)
    while stream.tell() < limit:
        kind, ops = _read_pickle(stream, limit)
        if kind == "end":
            return
        if kind == "error":
            if ops:
                yield ops
            raise _UnreadablePickle
        yield ops
        if kind == "overlong":
            raise _UnreadablePickle


STRINGS = {
    "SHORT_BINUNICODE",
    "BINUNICODE",
    "BINUNICODE8",
    "UNICODE",
    "SHORT_BINSTRING",
    "BINSTRING",
    "STRING",
}
GETS = {"GET", "BINGET", "LONG_BINGET"}
PUTS = {"PUT", "BINPUT", "LONG_BINPUT"}


def _imported_ops(ops) -> tuple[dict[str, int], list[str]]:
    """Names and refused opcodes in one pickle.

    GLOBAL and INST carry their names inline. STACK_GLOBAL takes them from the stack, so it is resolved only when
    the two values pushed right before it (memo stores in between allowed) are strings, pushed literally or
    fetched from the memo where a string was stored; otherwise it is refused, never guessed."""
    names: dict[str, int] = {}
    refused: list[str] = []
    memo: dict[int, str | None] = {}
    last: str | None = None  # the value of the most recent push, if it was a string
    run: list[
        str
    ] = []  # strings pushed since the last opcode that was not a string push or a memo store
    for op, arg, _ in ops:
        name = None
        if op.name in STRINGS:
            if arg is _SKIPPED or not isinstance(arg, str):
                last = None
                run = []
                continue
            last = arg
            run.append(last)
            continue
        if op.name in GETS:
            last = memo.get(int(arg))
            if last is None:
                run = []
            else:
                run.append(last)
            continue
        if op.name in PUTS:
            memo[int(arg)] = last
            continue
        if op.name == "MEMOIZE":
            memo[len(memo)] = last
            continue
        if op.name == "STACK_GLOBAL":
            if len(run) < 2:
                refused.append(
                    "STACK_GLOBAL whose names are not two strings pushed just before it"
                )
            else:
                name = f"{run[-2]}.{run[-1]}"
        elif op.name in ("GLOBAL", "INST"):
            name = str(arg).replace(" ", ".")
        elif op.name in REFUSED_OPS:
            refused.append(op.name)
        if name is not None:
            names[name] = names.get(name, 0) + 1
        last = None
        run = []
    return names, refused


def imported(data: bytes | io.BufferedIOBase) -> tuple[dict[str, int], list[str]]:
    """Every name imported by every pickle in ``data``, and the refused opcodes they use.

    Pickles one after another are separate unpickles, so the memo starts empty again at each
    STOP. Counts are added together. A buffer that never reaches STOP, or that holds no pickle
    at all, is refused."""
    names: dict[str, int] = {}
    refused: list[str] = []
    saw_stop = False
    try:
        for ops in _pickle_streams(data):
            if ops[-1][0].name == "STOP":
                saw_stop = True
            found, bad = _imported_ops(ops)
            for name, count in found.items():
                names[name] = names.get(name, 0) + count
            refused += bad
    except _UnreadablePickle:
        refused.append("unreadable pickle")
    if not saw_stop and "unreadable pickle" not in refused:
        refused.append("no pickle")
    return names, refused


def _record(
    out: dict, allowed: set[str], member: str, names: dict, refused: list[str]
) -> None:
    """Fold one reading into the report. A disallowed name or a refused opcode fails it."""
    out["pickles"][member] = names
    out["outside_allowlist"] += sorted(
        n for n in names if n not in allowed and not STORAGE.match(n)
    )
    out["refused_opcodes"] += refused


def audit(path: Path, allow: set[str]) -> dict:
    allowed = BASE | allow
    out: dict = {
        "file": str(path),
        "pickles": {},
        "outside_allowlist": [],
        "refused_opcodes": [],
    }
    try:
        members = pickles(path)
    except _NotZip:
        out["refused_opcodes"].append("not a zip checkpoint")
        out["message"] = NON_ZIP_CHECKPOINT
        out["passes"] = False
        return out
    except _AmbiguousZip:
        out["refused_opcodes"].append("shifted zip")
        out["message"] = SHIFTED_ZIP
        out["passes"] = False
        return out
    except _DuplicateNames:
        out["refused_opcodes"].append("duplicate member")
        out["message"] = DUPLICATE_MEMBER
        out["passes"] = False
        return out
    except _BadZip:
        out["refused_opcodes"].append("not a zip checkpoint")
        out["message"] = NON_ZIP_CHECKPOINT
        out["passes"] = False
        return out
    if not members:
        # A zip with no .pkl has nothing torch.load could rebuild.
        out["refused_opcodes"].append("no pickle")
        out["passes"] = False
        return out
    for member, data in members:
        names, refused = imported(data)
        _record(out, allowed, member, names, refused)
    out["passes"] = not out["outside_allowlist"] and not out["refused_opcodes"]
    return out


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    allow: set[str] = set()
    while "--allow" in args:
        i = args.index("--allow")
        if i + 1 >= len(args):
            print(__doc__, file=sys.stderr)
            return 2
        allow.add(args[i + 1])
        del args[i : i + 2]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    result = audit(Path(args[0]), allow)
    print(json.dumps(result, indent=1))
    if not result["passes"]:
        detail = result.get("message", "imports what is not allowed")
        print(f"REFUSED: {args[0]} {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
