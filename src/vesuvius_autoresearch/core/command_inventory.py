"""Read declared command boundaries without importing or executing commands."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import PurePosixPath

from .file_capture import capture_bytes

STACKS = ("stdlib", "scientific", "torch", "gui")
MAX_INVENTORY_BYTES = 1024**2
FIELDS = {
    "id",
    "summary",
    "kind",
    "argv",
    "source",
    "stack",
    "layout",
    "villa",
    "guide",
    "needs",
    "effects",
}


# Control characters (C0, DEL and C1) and the Unicode line and paragraph
# separators; str.splitlines() also breaks at NEL, U+2028 and U+2029.
_NOT_SINGLE_LINE = {"Cc", "Zl", "Zp"}


def _text(value):
    return (
        isinstance(value, str)
        and bool(value.strip())
        and all(unicodedata.category(c) not in _NOT_SINGLE_LINE for c in value)
    )


def _path(value, suffix):
    if not _text(value) or not re.fullmatch(r"[A-Za-z0-9_./-]+", value):
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.suffix == suffix
        and all(part not in {".", "..", ""} for part in value.split("/"))
    )


def read_inventory(path):
    """Validate a bounded capture and bind the reported hash to its parsed bytes."""
    path, raw = capture_bytes(path, MAX_INVENTORY_BYTES)

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate inventory key: {key}")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "scope", "stacks", "commands"}
        or type(value.get("schema_version")) is not int
        or value["schema_version"] != 1
        or not _text(value["scope"])
        or not isinstance(value["stacks"], dict)
        or set(value["stacks"]) != set(STACKS)
        or not all(_text(v) for v in value["stacks"].values())
        or not isinstance(value["commands"], list)
        or not 1 <= len(value["commands"]) <= 100
    ):
        raise ValueError("unsupported command inventory")
    seen = set()
    for command in value["commands"]:
        if not isinstance(command, dict) or set(command) != FIELDS:
            raise ValueError("invalid command inventory fields")
        if any(not _text(command[key]) for key in FIELDS - {"argv"}):
            raise ValueError(
                "command metadata must contain nonempty single-line strings"
            )
        name = command["id"]
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name) or name in seen:
            raise ValueError(f"invalid or duplicate command ID: {name}")
        seen.add(name)
        if (
            command["stack"] not in STACKS
            or command["layout"] not in {"checkout", "wheel-or-checkout"}
            or command["villa"] not in {"none", "conditional", "required"}
            or command["effects"]
            not in {"observe", "artifacts", "state", "interactive"}
        ):
            raise ValueError(f"invalid command boundary classification: {name}")
        argv, source, kind = command["argv"], command["source"], command["kind"]
        if (
            not isinstance(argv, list)
            or not 2 <= len(argv) <= 16
            or not all(_text(v) for v in argv)
            or not _path(command["guide"], ".md")
        ):
            raise ValueError(f"invalid command prefix/guide: {name}")
        if kind == "script":
            valid = _path(source, ".py") and argv[:2] == ["python", source]
        elif kind == "shell":
            valid = _path(source, ".sh") and argv[:2] == ["bash", source]
        elif kind == "module":
            module = argv[2] if len(argv) >= 3 else ""
            expected = module.replace(".", "/") + ".py"
            valid = (
                _path(source, ".py")
                and bool(re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+", module))
                and argv[:2] == ["python", "-m"]
                and source in {expected, "src/" + expected}
            )
        else:
            valid = False
        if not valid:
            raise ValueError(
                f"command prefix does not match its declared source: {name}"
            )
        if command["layout"] == "wheel-or-checkout" and not (
            kind == "module" and source.startswith("src/vesuvius_autoresearch/")
        ):
            raise ValueError(f"packaged command must be a runtime module: {name}")
    return value, {
        "path": str(path),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def select_commands(inventory, *, command=None, stack=None):
    if command is not None and command not in {
        row["id"] for row in inventory["commands"]
    }:
        raise ValueError(f"unknown command ID: {command}")
    if stack is not None and stack not in STACKS:
        raise ValueError(f"unknown stack: {stack}")
    selected = [
        row
        for row in inventory["commands"]
        if (command is None or row["id"] == command)
        and (stack is None or row["stack"] == stack)
    ]
    if not selected:
        raise ValueError("no command matches the requested ID/stack")
    return selected
