"""Read a zip checkpoint's pickle without running it, and refuse every other checkpoint.

A pickle can only call what it imports: GLOBAL and STACK_GLOBAL name a module attribute, INST and OBJ build a
class (INST names it inline), and EXT1/2/4 fetch one from the copyreg registry. This walks the opcodes with
pickletools (nothing is unpickled), lists every name imported, and refuses the file if any is outside the
allowlist or if it uses the extension registry. A file that passes can only rebuild tensors, plain containers
and the classes allowed, so a full torch.load of it runs no other code.

torch's own weights-only unpickler is the stronger check where it works; it cannot rebuild a
collections.defaultdict, which training checkpoints with optimizer state carry.

torch.load treats a file as a zip archive only when it starts with the zip local-file signature.
Anything else — the legacy non-zip pickle format, a tar, a pickle placed in front of a zip — is
refused outright. Convert that checkpoint offline to the zip format before loading it. A zip is
then audited as before: each ``.pkl`` member is walked, and a member that holds several pickles
is still read pickle by pickle, because that is the zip a current torch.save writes.

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
# torch.load's rule, not zipfile.is_zipfile's: an archive is the checkpoint only when the
# file itself starts with a local-file header. is_zipfile also accepts an archive at the end.
_ZIP_LOCAL = b"PK\x03\x04"
NON_ZIP_CHECKPOINT = (
    "refusing a non-zip checkpoint; convert it offline to zip before loading"
)
# Inside one zip member, torch still writes several pickles before raw storage.
_LEGACY_PICKLES = 5
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


class _UnreadablePickle(Exception):
    """A pickle started and did not reach STOP. The unread tail is not storage."""


def pickles(path: Path) -> list[tuple[str, bytes]]:
    """The ``.pkl`` members of a zip checkpoint.

    A file is a torch zip only when it starts with the local-file signature.
    A legacy pickle, a tar, and a pickle placed in front of a zip are refused
    before any opcode is read.
    """
    with path.open("rb") as handle:
        signature = handle.read(len(_ZIP_LOCAL))
    if signature != _ZIP_LOCAL:
        raise _NotZip(path.name)
    with zipfile.ZipFile(path) as archive:
        return [
            (name, archive.read(name))
            for name in archive.namelist()
            if name.endswith(".pkl")
        ]


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
    """Each complete pickle in ``data``, which may hold several back to back.

    pickletools stops at the first STOP. The legacy torch format writes five pickles before the
    tensor storage, which is not a pickle: the magic number, the protocol, the system
    information, the object, and the storage keys. torch.load does not unpickle that tail, so a
    parse error after those five ends the scan. Storage bytes can look like an opcode; they are
    not recorded and they do not refuse the file.

    A parse error before the fifth STOP is not that tail. torch.load runs that next pickle
    opcode by opcode, including one that never reaches STOP. Opcodes already read are yielded,
    so a name already seen is not dropped, and the error is raised so the file is refused.
    A frame whose declared end is past that STOP is refused too: the next load resumes there.
    """
    stream, limit = _stream_of(data)
    finished = 0
    while stream.tell() < limit:
        kind, ops = _read_pickle(stream, limit)
        if kind == "end":
            return
        if kind == "error":
            if finished >= _LEGACY_PICKLES:
                return
            if ops:
                yield ops
            raise _UnreadablePickle
        yield ops
        finished += 1
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

    A legacy checkpoint is several pickles in a row. Each is a separate unpickle, so the memo
    starts empty again at each STOP. Counts are added together. A buffer that never reaches
    STOP, or that holds no pickle at all, is refused."""
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
