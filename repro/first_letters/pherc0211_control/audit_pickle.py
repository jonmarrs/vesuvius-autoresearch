"""Read a checkpoint's pickle without running it, and refuse it unless every global it imports is allowed.

A pickle can only call what it imports: GLOBAL and STACK_GLOBAL name a module attribute, INST and OBJ build a
class (INST names it inline), and EXT1/2/4 fetch one from the copyreg registry. This walks the opcodes with
pickletools (nothing is unpickled), lists every name imported, and refuses the file if any is outside the
allowlist or if it uses the extension registry. A file that passes can only rebuild tensors, plain containers
and the classes allowed, so a full torch.load of it runs no other code.

torch's own weights-only unpickler is the stronger check where it works; it cannot rebuild a
collections.defaultdict, which training checkpoints with optimizer state carry.

usage: audit_pickle.py CHECKPOINT [--allow MODULE.NAME]...
"""

from __future__ import annotations

import json
import pickletools
import re
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


def pickles(path: Path) -> list[tuple[str, bytes]]:
    """The pickles in a checkpoint: every .pkl member of a torch zip archive, or the file itself."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return [
                (n, archive.read(n)) for n in archive.namelist() if n.endswith(".pkl")
            ]
    return [(Path(path).name, Path(path).read_bytes())]


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


def imported(data: bytes) -> tuple[dict[str, int], list[str]]:
    """Every name the pickle imports, with counts, and the refused opcodes it uses.

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
    for op, arg, _ in pickletools.genops(data):
        name = None
        if op.name in STRINGS:
            last = str(arg)
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


def audit(path: Path, allow: set[str]) -> dict:
    allowed = BASE | allow
    out: dict = {
        "file": str(path),
        "pickles": {},
        "outside_allowlist": [],
        "refused_opcodes": [],
    }
    for member, data in pickles(path):
        names, refused = imported(data)
        out["pickles"][member] = names
        out["outside_allowlist"] += sorted(
            n for n in names if n not in allowed and not STORAGE.match(n)
        )
        out["refused_opcodes"] += refused
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
