"""The amended villa patch (ends kept at the border of the box the zone's blocks read, not only at the volume's) trims
exactly as the registered patch does whenever the zone is the whole volume, as on every cube of the held-out test, and
leaves a one-block zone inside a larger volume alone, where the registered patch trims."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402

FIBERS = ROOT / "repro/fibers"
AMENDMENT = (
    ROOT / "docs/preregistration/2026-11-06_afv_generator_block_seams_amendment.md"
)
RECORD = ROOT / "reports/afv_generator_block_seams.json"
REGISTERED = FIBERS / "villa_fiber_generator_trim_cut_ends_7e6b82164.patch"
AMENDED = FIBERS / "villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch"
STITCH = "vesuvius/src/vesuvius/fiber_spline_generator/extend/stitch.py"


def trim_function(patch: Path):
    """``trim_cut_ends`` as the patch leaves villa's stitch.py, run from the new side of the patch's stitch.py hunks."""
    lines, inside = [], False
    for line in patch.read_text().splitlines():
        if line.startswith("diff --git"):
            inside = line.endswith(f"b/{STITCH}")
        elif inside and line[:1] in (" ", "+") and not line.startswith("+++"):
            lines.append(line[1:])
    tree = ast.parse("\n".join(lines))
    wanted = [node for node in tree.body
              if isinstance(node, ast.FunctionDef) and node.name in ("_length", "trim_cut_ends")
              or isinstance(node, ast.Assign) and {getattr(t, "id", None) for t in node.targets} & {"CUT_END", "MIN_LENGTH"}]  # fmt: skip
    namespace = {"np": np, "Iterable": Iterable, "Sequence": Sequence}
    exec(compile(ast.Module(wanted, []), str(patch), "exec"), namespace)
    assert (namespace["CUT_END"], namespace["MIN_LENGTH"]) == (16.0, 8.0)
    return namespace["trim_cut_ends"]


def random_blocks(seed: int, n: int):
    """Random blocks of random volumes, each with splines of which about half start within 20 voxels of a border."""
    rng = np.random.default_rng(seed)
    for _ in range(n):
        shape = rng.integers(96, 600, 3)
        low = np.array(
            [0 if rng.random() < 0.4 else rng.integers(1, s - 64) for s in shape]
        )
        high = np.array(
            [
                s if rng.random() < 0.4 else rng.integers(a + 64, s)
                for a, s in zip(low, shape, strict=False)
            ]
        )
        size = high - low
        traces = []
        for _ in range(6):
            a, b = rng.random(3) * size, rng.random(3) * size
            if rng.random() < 0.5:
                axis = rng.integers(3)
                a[axis] = rng.choice(
                    [rng.random() * 20, size[axis] - 1 - rng.random() * 20]
                )
            t = np.linspace(0, 1, rng.integers(2, 400))[:, None]
            points = a + (b - a) * t + rng.normal(0, 1.5, (len(t), 3)).cumsum(0) * 0.05
            traces.append(
                ("V" if rng.random() < 0.5 else "H", np.clip(points, -0.4, size - 0.6))
            )
        yield traces, low, high, shape


def same(a, b):
    return len(a) == len(b) and all(
        fa == fb and np.array_equal(pa, pb)
        for (fa, pa), (fb, pb) in zip(a, b, strict=False)
    )


def test_the_registered_patch_is_unchanged():
    digest = hashlib.sha256(REGISTERED.read_bytes()).hexdigest()
    assert digest == "48f7059b07bea0c54d6c98610c2454cc0a930660ec3844f22b4d6a7c3a68fd4b"


def test_with_the_zone_filling_the_volume_both_patches_trim_alike():
    registered, amended = trim_function(REGISTERED), trim_function(AMENDED)
    trimmed = 0
    for traces, low, high, shape in random_blocks(0, 1000):
        kept = registered(traces, low, high, shape)
        assert same(kept, amended(traces, low, high, (0, 0, 0), shape))
        trimmed += sum(map(len, (p for _, p in kept))) < sum(
            map(len, (p for _, p in traces))
        )
    assert trimmed > 900  # nearly every block had something to trim


def test_a_one_block_zone_inside_the_volume_is_trimmed_only_by_the_registered_patch():
    registered, amended = trim_function(REGISTERED), trim_function(AMENDED)
    differ = 0
    for traces, low, high, shape in random_blocks(1, 200):
        size = high - low
        # The block as a whole volume: nothing is cut.
        untrimmed = registered(traces, (0, 0, 0), size, size)
        assert same(amended(traces, low, high, low, high), untrimmed)
        differ += not same(registered(traces, low, high, shape), untrimmed)
    assert differ > 150


def test_what_the_amendment_had_seen_is_the_first_held_out_cube_s_one_block_row():
    """The chain runs bs.HELD_OUT in order; the amendment quotes the one row its first cube had written."""
    text, c = " ".join(AMENDMENT.read_text().split()), bs.HELD_OUT[0]
    one = json.loads(RECORD.read_text())["cubes"][c]["rows"]["one/main"]
    assert (f"`{c}`, had finished (main: {one['written']} fibers written; ERLpen "
            f"{one['tol2']['erl_merge_penalized']:.2f} at τ = 2 and {one['tol4']['erl_merge_penalized']:.2f} at τ = 4)"
            ) in text  # fmt: skip
