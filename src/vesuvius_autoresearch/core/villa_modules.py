"""Load single-file "leaf" modules from the pinned villa submodule by file path.

Putting a villa directory on ``sys.path`` makes module resolution depend on import
order and the working directory. ``villa/vesuvius/src`` competes with the older
installed ``vesuvius`` package: whichever is imported first wins for the rest of the
process, so "villa's TTA" could silently be the installed snapshot, or could replace
``vesuvius`` for every later import. ``villa/lasagna`` holds ~90 top-level modules
with generic names (``model``, ``common``, ``optimizer``), and a relative entry only
resolves from the repository root.

A leaf module (one that imports nothing from its own directory or from
``vesuvius``) needs neither. It is executed from its absolute path under a private
module name; ``sys.path`` and ``sys.modules["vesuvius"]`` are never touched. A module
that is not a leaf is refused instead of being loaded with imports that would
resolve against whatever happens to be importable.

``scripts/pinned_vesuvius.py`` covers the other case: pinned source that must be
importable under its real ``vesuvius.*`` name for the duration of a block.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import sys
from pathlib import Path
from threading import Lock, RLock
from types import ModuleType

VILLA_ROOT = Path(__file__).resolve().parents[3] / "villa"
_MODULE_LOCKS: dict[str, RLock] = {}
_MODULE_LOCKS_LOCK = Lock()


def non_leaf_imports(path: Path) -> list[str]:
    """Imports in ``path`` that would resolve outside the file when loaded by path."""
    path = Path(path)
    siblings = {
        p.stem
        for p in path.parent.iterdir()
        if p != path and (p.suffix == ".py" or p.is_dir())
    }
    found = []
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.ImportFrom) and node.level:
            found.append("." * node.level + (node.module or ""))
            continue
        if isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        else:
            continue
        for name in names:
            top = name.split(".")[0]
            if top == "vesuvius" or top in siblings:
                found.append(name)
    return found


def load_villa_leaf(
    relative_path: str, *, villa_root: str | Path | None = None
) -> ModuleType:
    """Return the module at ``villa/<relative_path>``, executed once per process.

    Raises FileNotFoundError when the pinned checkout lacks the file and ImportError
    when the file imports a sibling or ``vesuvius`` (see the module docstring).
    Concurrent callers for the same file wait until initialization completes.
    Different files can initialize independently; failed initialization is retried
    by the next caller.
    """
    root = Path(villa_root) if villa_root is not None else VILLA_ROOT
    path = (root / relative_path).resolve()
    if path.suffix != ".py" or not path.is_file():
        raise FileNotFoundError(
            f"{relative_path} is not in the villa checkout at {root}; "
            "run `git submodule update --init villa`"
        )
    digest = hashlib.sha1(str(path).encode()).hexdigest()[:12]
    name = f"_villa_leaf_{path.stem}_{digest}"
    with _MODULE_LOCKS_LOCK:
        lock = _MODULE_LOCKS.setdefault(name, RLock())
    with lock:
        cached = sys.modules.get(name)
        if cached is not None:
            return cached
        if outside := non_leaf_imports(path):
            raise ImportError(
                f"{relative_path} imports {', '.join(sorted(set(outside)))}, which would "
                "resolve outside the pinned file; it cannot be loaded as a leaf module"
            )
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        # Registration before execution is required by decorators such as
        # dataclass. Keep the lock through execution so another caller cannot
        # mistake this partially initialized module for a completed cache entry.
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        return module
