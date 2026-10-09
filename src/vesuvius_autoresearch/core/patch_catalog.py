"""Use the pinned Villa sampler without importing its optional ML package tree."""

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def sampler_module():
    path = (
        Path(__file__).resolve().parents[3]
        / "villa/vesuvius/src/vesuvius/models/datasets/find_valid_patches.py"
    )
    name = "_autoresearch_pinned_patch_catalog"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load pinned patch sampler: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def find_valid_patches(*args, **kwargs):
    return sampler_module().find_valid_patches(*args, **kwargs)
