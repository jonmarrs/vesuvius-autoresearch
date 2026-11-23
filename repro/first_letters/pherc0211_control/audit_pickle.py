"""Read a checkpoint's pickle without running it, and refuse it unless every global it imports is allowed.

A pickle can only call what it imports: GLOBAL and STACK_GLOBAL name a module attribute, INST and OBJ build a
class (INST names it inline), and EXT1/2/4 fetch one from the copyreg registry. This walks the opcodes with
pickletools (nothing is unpickled), lists every name imported, and refuses the file if any is outside the
allowlist or if it uses the extension registry. A file that passes can only rebuild tensors, plain containers
and the classes allowed, so a full torch.load of it runs no other code.

torch's own weights-only unpickler is the stronger check where it works; it cannot rebuild a
collections.defaultdict, which training checkpoints with optimizer state carry.

torch.load reads a file as a zip archive only when the file starts with the zip local-file
signature. A pickle placed in front of an archive is what that load runs, so those bytes are
audited and the archive after them is not treated as the checkpoint. Before the concatenated
pickles of a later legacy file, torch.load tries the ancient tar format, so every file in that
tar is audited, and the file is streamed a second time as a pickle: a load from memory,
and a tar read that fails, unpickle those bytes. A long counted string is skipped, not
copied, so a payload after it is still seen. A tar that cannot be read is refused.
A file that is not a zip or a tar may hold several pickles in a row. torch.load runs five
before the raw storage: the magic number, the protocol, the system information, the object,
and the storage keys. A parse error before those five have finished keeps every name already
read and refuses the file. A parse error after them is the storage tail. A file that holds
no pickle is refused.

usage: audit_pickle.py CHECKPOINT [--allow MODULE.NAME]...
"""

from __future__ import annotations

import io
import json
import pickletools
import re
import struct
import sys
import tarfile
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
# A real checkpoint has a handful of members. Tens of thousands of headers are not one.
_MAX_TAR_MEMBERS = 1024
_MAX_TAR_BYTES = 512 * 1024 * 1024
# torch.load unpickles five values, then reads raw storage and does not unpickle it.
_LEGACY_PICKLES = 5
# A global name is short. A longer counted string is skipped instead of copied.
_MAX_ARG_BYTES = 64 * 1024
# Raw bytes of a tar are usually not a pickle. These mean "nothing ran", not "a pickle ran".
_RAW_TAR_IGNORE = {"unreadable pickle", "no pickle"}
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


class _UnreadableTar(Exception):
    """A tar checkpoint could not be read in full, so the audit refuses it."""


class _UnreadablePickle(Exception):
    """A pickle started and did not reach STOP. The unread tail is not storage."""


def pickles(path: Path) -> tuple[list[tuple[str, bytes]], bool]:
    """The pickles in a checkpoint, and whether every byte of each one must be a pickle.

    A file is a torch zip only when it starts with the local-file signature. Bytes in front of
    an archive are a pickle torch.load would run, so they are returned whole and audited.
    A file ``tarfile`` recognizes is the ancient tar checkpoint torch.load tries first. Every
    regular file in it is returned, because that load unpickles ``storages``, ``tensors`` and
    ``pickle``, and a pickle under any other name is not skipped. Those members interleave
    later pickles with raw storage, so a member that is not pickles from start to end is
    refused rather than passed. A member that cannot be read refuses the tar.
    """
    with path.open("rb") as handle:
        signature = handle.read(len(_ZIP_LOCAL))
    if signature == _ZIP_LOCAL:
        with zipfile.ZipFile(path) as archive:
            return [
                (n, archive.read(n)) for n in archive.namelist() if n.endswith(".pkl")
            ], False
    if tarfile.is_tarfile(path):
        return _tar_members(path), True
    return [(path.name, path.read_bytes())], False


def _tar_members(path: Path) -> list[tuple[str, bytes]]:
    """Regular files of a legacy tar, in archive order.

    A link is not followed and a device is not read: either one refuses the tar.
    A directory counts toward the member cap. Once that cap is reached, another
    header refuses the tar before it is parsed. More declared bytes than a
    checkpoint holds refuses it too, before those bytes are read into memory.
    """
    found: list[tuple[str, bytes]] = []
    try:
        with tarfile.open(path, mode="r:", format=tarfile.PAX_FORMAT) as archive:
            files = []
            count = 0
            total = 0
            while True:
                # Directories count. The next header is refused before it is parsed
                # once the archive already holds as many members as a checkpoint.
                if count >= _MAX_TAR_MEMBERS:
                    archive.fileobj.seek(archive.offset)
                    peeked = archive.fileobj.read(tarfile.BLOCKSIZE)
                    archive.fileobj.seek(archive.offset)
                    if peeked.strip(b"\0"):
                        raise _UnreadableTar(path.name)
                    break
                member = archive.next()
                if member is None:
                    break
                count += 1
                if member.isdir():
                    continue
                if not member.isreg():
                    raise _UnreadableTar(member.name)
                total += member.size
                if total > _MAX_TAR_BYTES:
                    raise _UnreadableTar(path.name)
                files.append(member)
            for member in files:
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise _UnreadableTar(member.name)
                found.append((member.name, extracted.read()))
    except (tarfile.TarError, OSError) as exc:
        raise _UnreadableTar(str(exc)) from exc
    return found


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


def _pickle_covers(data: bytes) -> bool:
    """True when every byte of ``data`` belongs to a finished pickle."""
    if not data:
        return False
    stream = io.BytesIO(data)
    size = len(data)
    while stream.tell() < size:
        start = stream.tell()
        ops = []
        try:
            for item in pickletools.genops(stream):
                ops.append(item)
        except Exception:
            return False
        if not ops or stream.tell() == start or ops[-1][0].name != "STOP":
            return False
    return stream.tell() == size


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


def _raw_file(path: Path) -> tuple[dict[str, int], list[str]]:
    """The pickle reading of the file's own bytes.

    A tar header is not usually a pickle, so "unreadable pickle" and "no pickle"
    from that reading are not a second refusal. A name or a refused opcode in
    those bytes is: torch.load of a BytesIO, and a tar read that fails, unpickle
    the leading bytes and would run them. The scan reads the file itself and
    seeks past a long counted string, so the member bodies are not copied.
    """
    with path.open("rb") as handle:
        names, refused = imported(handle)
    return names, [item for item in refused if item not in _RAW_TAR_IGNORE]


def audit(path: Path, allow: set[str]) -> dict:
    allowed = BASE | allow
    out: dict = {
        "file": str(path),
        "pickles": {},
        "outside_allowlist": [],
        "refused_opcodes": [],
    }
    try:
        members, only_pickles = pickles(path)
    except _UnreadableTar:
        out["refused_opcodes"].append("unreadable tar")
        names, refused = _raw_file(path)
        _record(out, allowed, "<file>", names, refused)
        out["passes"] = False
        return out
    if only_pickles:
        # The member reading and the raw reading both have to pass.
        names, refused = _raw_file(path)
        _record(out, allowed, "<file>", names, refused)
    if not members:
        # A zip with no .pkl, or a tar with no files, has nothing torch.load could rebuild.
        if not out["outside_allowlist"] and not out["refused_opcodes"]:
            out["refused_opcodes"].append("no pickle")
        out["passes"] = False
        return out
    for member, data in members:
        names, refused = imported(data)
        # A tar member that stops early still has bytes torch.load can unpickle
        # after the raw storage. Refuse it instead of treating that tail as unused.
        if (
            only_pickles
            and not _pickle_covers(data)
            and "unreadable pickle" not in refused
        ):
            refused.append("unreadable pickle")
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
        print(f"REFUSED: {args[0]} imports what is not allowed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
