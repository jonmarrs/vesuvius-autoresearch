"""Our fiber scorer IS ScrollGT's: the scoring core in eval_trace.py is vendored verbatim from it.

Two copies of a metric drift. This one had already drifted three times: ScrollGT read runs in stored row order;
our PR #7 scored graph components; our version 3 fixed a zero-length-edge bug that ScrollGT never had. Since
2026-10-04 both use ScrollGT's definition (scrollgt v0.4.0), and this test fails if the vendored functions stop
matching ScrollGT's source. It needs a ScrollGT checkout beside this repo (../scrollgt) and skips without one.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from vesuvius_autoresearch.fibers import eval_trace as ours
from vesuvius_autoresearch.fibers.skeleton_io import Fiber, Skeleton

SCROLLGT = (
    Path(__file__).resolve().parents[2] / "scrollgt" / "src" / "scrollgt" / "fibers"
)
VENDORED = ("ConnectivityScores", "_dilate_labels", "_edge_walk", "_resample_fiber", "_runs_along_fiber",
            "_fiber_runs", "floor_single_instance", "floor_voxel_instances", "floor_connected_components",
            "floor_random_instances", "oracle_from_skeleton")  # fmt: skip

pytestmark = pytest.mark.skipif(
    not (SCROLLGT / "eval_trace.py").exists(), reason="no ../scrollgt checkout"
)


def _defs(path: Path) -> dict[str, str]:
    src = path.read_text()
    return {n.name: ast.get_source_segment(src, n) or "" for n in ast.parse(src).body
            if isinstance(n, ast.FunctionDef | ast.ClassDef)}  # fmt: skip


def _norm(s: str) -> str:
    return s.replace(
        "from vesuvius_autoresearch.fibers.skeleton_io import",
        "from .skeleton_io import",
    )


@pytest.mark.parametrize("name", VENDORED)
def test_vendored_function_matches_scrollgt(name):
    mine, theirs = _defs(Path(ours.__file__)), _defs(SCROLLGT / "eval_trace.py")
    assert _norm(mine[name]) == theirs[name], f"{name} has drifted from ScrollGT's"


def test_scoring_core_is_scrollgts_score_tracing():
    mine, theirs = _defs(Path(ours.__file__)), _defs(SCROLLGT / "eval_trace.py")
    assert (
        mine["_score_tracing_scrollgt"].replace(
            "def _score_tracing_scrollgt(", "def score_tracing(", 1
        )
        == theirs["score_tracing"]
    )


def _scrollgt_module():
    pkg = types.ModuleType("_scrollgt_fibers")
    pkg.__path__ = [str(SCROLLGT)]
    sys.modules.setdefault("_scrollgt_fibers", pkg)
    spec = importlib.util.spec_from_file_location(
        "_scrollgt_fibers.eval_trace", SCROLLGT / "eval_trace.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_scrollgt_fibers.eval_trace"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_scores_are_identical_to_scrollgts_on_a_branched_fiber():
    theirs = _scrollgt_module()
    coords = np.array(
        [[2, 2, 2], [2, 2, 6], [2, 6, 2], [6, 2, 2], [2, 2, 9]], dtype=float
    )
    f = Fiber(
        1,
        "f",
        np.arange(5),
        coords,
        np.array([[0, 1], [0, 2], [0, 3], [1, 4]], dtype=np.int64),
    )
    inst = np.zeros((10, 10, 12), dtype=np.int64)
    inst[2, 2, 2:6] = 1
    inst[2, 2, 6:10] = 2
    inst[2, 2:7, 2] = 1
    a = ours.score_tracing(Skeleton([f]), inst, tolerance=1.0).as_row()
    b = theirs.score_tracing(Skeleton([f]), inst, tolerance=1.0).as_row()
    a.pop("scoring_version"), b.pop("scoring_version")
    assert a == b
