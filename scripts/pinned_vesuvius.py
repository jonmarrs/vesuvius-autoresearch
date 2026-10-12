"""Load single modules of villa's pinned vesuvius package under their own names.

Pinned villa source is loaded straight from the submodule so that the ML package
is not bootstrapped. Some of that source imports a sibling absolutely (`from
vesuvius.tifxyz_canvas import ...`), which would resolve to the installed
vesuvius package. That is an older snapshot: villa's package now requires Python
3.14, so it cannot be reinstalled into this environment, and it lacks the newer
modules. A leaf module, one that imports nothing from vesuvius itself, is loaded
from the submodule and registered only while the pinned source is imported.
"""

from __future__ import annotations

import contextlib
import importlib.util
import sys
from pathlib import Path

VESUVIUS_SRC = Path(__file__).resolve().parents[1] / "villa/vesuvius/src"


@contextlib.contextmanager
def pinned_vesuvius_modules(*names):
    """Register each named pinned module, e.g. "vesuvius.data.utils", for the
    duration of the block. A name with no file at this pin is skipped: source at
    that pin does not import it."""
    saved = {name: sys.modules.get(name) for name in names}
    try:
        for name in names:
            path = VESUVIUS_SRC.joinpath(*name.split(".")).with_suffix(".py")
            if not path.is_file():
                continue
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            sys.modules[name] = module
        yield
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
