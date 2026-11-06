"""Scratch pytest plugin (-p stub_native): stand-ins for villa's native vc_reader / vc_object_store, which are not built
here. Any attribute is a permissive dummy class, so modules that import names from them load; nothing native runs.
Only for checking tests that replace every native call they reach."""

import importlib.abc
import importlib.machinery
import sys
import types

STUBBED = ("vc_reader", "vc_object_store")


class _Meta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Dummy


class Dummy(metaclass=_Meta):
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return Dummy()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Dummy


class _Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in STUBBED:
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None

    def create_module(self, spec):
        m = types.ModuleType(spec.name)
        m.__path__ = []
        m.__getattr__ = (
            lambda attr: (_ for _ in ()).throw(AttributeError(attr))
            if attr.startswith("__")
            else Dummy
        )
        m.STUBBED_NATIVE = True
        return m

    def exec_module(self, module):
        pass


for mod in list(sys.modules):
    if mod.split(".")[0] in STUBBED:
        del sys.modules[mod]
sys.meta_path.insert(0, _Finder())
