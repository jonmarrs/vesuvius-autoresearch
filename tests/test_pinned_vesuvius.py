"""The pinned-module loader must leave sys.modules as it found it."""

import sys
import types

import pytest

from scripts.pinned_vesuvius import VESUVIUS_SRC, pinned_vesuvius_modules

requires_villa = pytest.mark.skipif(
    not (VESUVIUS_SRC / "vesuvius/data/utils.py").is_file(),
    reason="villa submodule not checked out",
)


@requires_villa
def test_a_pinned_module_is_registered_only_inside_the_block(monkeypatch):
    # Another test may already have imported the installed package's copy.
    monkeypatch.delitem(sys.modules, "vesuvius.data.utils", raising=False)
    with pinned_vesuvius_modules("vesuvius.data.utils"):
        loaded = sys.modules["vesuvius.data.utils"]
        assert loaded.__file__ == str(VESUVIUS_SRC / "vesuvius/data/utils.py")
    assert "vesuvius.data.utils" not in sys.modules


@requires_villa
def test_an_existing_entry_is_restored(monkeypatch):
    sentinel = types.ModuleType("vesuvius.data.utils")
    monkeypatch.setitem(sys.modules, "vesuvius.data.utils", sentinel)
    with pinned_vesuvius_modules("vesuvius.data.utils"):
        assert sys.modules["vesuvius.data.utils"] is not sentinel
    assert sys.modules["vesuvius.data.utils"] is sentinel


def test_a_name_with_no_file_at_this_pin_is_skipped():
    with pinned_vesuvius_modules("vesuvius.no_such_module_here"):
        assert "vesuvius.no_such_module_here" not in sys.modules
