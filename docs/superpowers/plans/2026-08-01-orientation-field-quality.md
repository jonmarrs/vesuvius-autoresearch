# Orientation Field Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure how accurately the `fiber_hz_vt` Hessian orientation field predicts the true fiber tangent at hand-traced ground-truth nodes, so we know whether the field or the walking algorithm is what limits run length.

**Architecture:** One read-only analysis module with three pure, separately testable pieces — ground-truth tangent extraction from the NML graph, sign-ambiguous angular error, and a per-cube driver — plus a CLI that runs all six cubes and writes a report. Nothing under `src/vesuvius_autoresearch/fibers/` changes.

**Tech Stack:** Python 3.10, numpy, pytest, `uv run`. GPU used only to build the Hessian via the existing `detection` module.

## Global Constraints

- **Repo:** `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch`, branch `feat/orientation-field-quality`. Never commit to `main`. Do not touch the sibling `scrollgt` repo.
- **Run Python via `uv run`.** System `python3` lacks `tifffile`.
- **Run the fiber suite with the GPU visible.** Do not set `CUDA_VISIBLE_DEVICES=""` — `test_cpu_gpu_vesselness_parity` and `test_cli_vesselness_roundtrip` fail under CUDA masking for unrelated reasons. Expect 91 passing before this work.
- **READ-ONLY: no file under `src/vesuvius_autoresearch/fibers/` may be modified.** This work produces a measurement, not an improvement. Success criterion 6 is exactly this.
- **Angular error is taken mod 180 degrees.** An orientation field is defined only up to sign, so errors live in [0, 90]. A signed comparison would report good tangents as ~180-degree failures.
- **`fiber_direction()` returns `(z, y, x)`** — the same frame as `Fiber.coords`. No axis conversion is needed anywhere in this work. Do not add one.
- **The field is built exactly as `bench_cli.cmd_trace` builds it:** `hessian(fiber_prob, gauss_sigma=2, sigma=3)` then `fiber_direction(J)`. Any other parameters characterise a field the tracer does not use.
- **The six cubes:** `s1_00497_01497_03997_256`, `s1_00497_02497_02997_256`, `s1_00997_02497_02997_256`, `s1_08997_02997_02497_256`, `s1_10997_02997_02997_256`, `s5_03997_01497_03997_256`. Inputs are cached at `local_data/fiber_skeletons/<stem>.nml` and `<stem>_fiberprob.npy`.
- **The reference number is `max_angle_deg = 25`**, the walker's per-step turn limit. Every error figure is reported against it.
- **No outcome is predicted.** The spec commits to a three-way fork; report whichever the data supports.
- Commit messages end with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` and no `Claude-Session:` line. No AI-authorship markers anywhere.

---

### Task 1: Ground-truth tangents from the NML graph

**Files:**
- Create: `src/vesuvius_autoresearch/fibers/field_quality.py`
- Create: `tests/test_field_quality.py`

**Interfaces:**
- Consumes: `Fiber`, `Skeleton` from `vesuvius_autoresearch.fibers.skeleton_io`.
- Produces:
  - `NodeKind` — `str` enum with members `INTERIOR = "interior"`, `ENDPOINT = "endpoint"`, `BRANCH = "branch"`, `ISOLATED = "isolated"`, `DEGENERATE = "degenerate"`.
  - `gt_tangents(fiber: Fiber) -> tuple[np.ndarray, np.ndarray, list[str]]` returning `(coords, tangents, kinds)`. `coords` is `(M, 3)` float in `(z, y, x)`; `tangents` is `(M, 3)` unit vectors; `kinds` has length `M`. **Only `INTERIOR` and `ENDPOINT` nodes appear in the returned arrays** — the others are excluded, but every node's kind is counted by the next function.
  - `count_node_kinds(fiber: Fiber) -> dict[str, int]` — counts over *all* nodes, including excluded ones.

Note this module lives under `src/vesuvius_autoresearch/fibers/` as a **new file**. Creating it does not violate the read-only constraint, which forbids modifying existing files there; do not edit `trace.py`, `detection.py`, or `skeleton_io.py`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_field_quality.py`:

```python
"""Ground-truth tangent extraction and sign-ambiguous angular error."""

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.field_quality import (
    NodeKind,
    count_node_kinds,
    gt_tangents,
)
from vesuvius_autoresearch.fibers.skeleton_io import Fiber


def _line_fiber(n=6, axis=0, spacing=2.0):
    """A straight chain of n nodes along `axis`, spaced `spacing` voxels apart."""
    coords = np.zeros((n, 3), dtype=float)
    coords[:, axis] = np.arange(n) * spacing
    edges = np.array([[i, i + 1] for i in range(n - 1)], dtype=int)
    return Fiber(id=1, name="line", node_ids=np.arange(n), coords=coords, edges=edges)


def test_straight_line_tangents_all_point_along_the_axis():
    coords, tangents, kinds = gt_tangents(_line_fiber(axis=0))
    assert len(coords) == 6
    assert all(k in (NodeKind.INTERIOR, NodeKind.ENDPOINT) for k in kinds)
    for t in tangents:
        assert abs(abs(float(t[0])) - 1.0) < 1e-9, t
        assert abs(float(t[1])) < 1e-9 and abs(float(t[2])) < 1e-9


def test_tangents_are_unit_length():
    _, tangents, _ = gt_tangents(_line_fiber())
    np.testing.assert_allclose(np.linalg.norm(tangents, axis=1), 1.0, atol=1e-9)


def test_endpoints_and_interiors_are_labelled():
    _, _, kinds = gt_tangents(_line_fiber(n=5))
    assert kinds[0] == NodeKind.ENDPOINT
    assert kinds[-1] == NodeKind.ENDPOINT
    assert kinds[1:-1] == [NodeKind.INTERIOR] * 3


def test_branch_node_is_excluded_and_counted():
    """A Y-junction node has no single tangent; including one would fake error."""
    coords = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0],  # stem
        [3.0, 1.0, 0.0], [3.0, -1.0, 0.0],                   # two arms off node 2
    ])
    edges = np.array([[0, 1], [1, 2], [2, 3], [2, 4]], dtype=int)
    fib = Fiber(id=1, name="y", node_ids=np.arange(5), coords=coords, edges=edges)

    out_coords, _, kinds = gt_tangents(fib)
    assert len(out_coords) == 4, "the degree-3 node must be dropped"
    assert NodeKind.BRANCH not in kinds

    counts = count_node_kinds(fib)
    assert counts[NodeKind.BRANCH] == 1
    assert counts[NodeKind.ENDPOINT] == 3
    assert counts[NodeKind.INTERIOR] == 1


def test_isolated_node_is_excluded_and_counted():
    fib = Fiber(id=1, name="dot", node_ids=np.arange(1),
                coords=np.zeros((1, 3)), edges=np.zeros((0, 2), dtype=int))
    out_coords, _, _ = gt_tangents(fib)
    assert len(out_coords) == 0
    assert count_node_kinds(fib)[NodeKind.ISOLATED] == 1


def test_duplicate_coordinates_are_excluded_as_degenerate():
    """Two nodes at the same position give a zero-length tangent."""
    coords = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    edges = np.array([[0, 1], [1, 2]], dtype=int)
    fib = Fiber(id=1, name="dup", node_ids=np.arange(3), coords=coords, edges=edges)

    _, tangents, _ = gt_tangents(fib)
    assert np.all(np.isfinite(tangents))
    assert count_node_kinds(fib)[NodeKind.DEGENERATE] >= 1


def test_interior_tangent_uses_a_central_difference():
    """A corner node's tangent must bisect its two edges, not follow one of them."""
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]])
    edges = np.array([[0, 1], [1, 2]], dtype=int)
    fib = Fiber(id=1, name="corner", node_ids=np.arange(3), coords=coords, edges=edges)

    _, tangents, kinds = gt_tangents(fib)
    mid = tangents[list(kinds).index(NodeKind.INTERIOR)]
    expected = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    assert abs(abs(float(np.dot(mid, expected))) - 1.0) < 1e-9
```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
uv run python -m pytest tests/test_field_quality.py -v
```

Expected: collection error — `No module named 'vesuvius_autoresearch.fibers.field_quality'`.

- [ ] **Step 3: Implement**

Create `src/vesuvius_autoresearch/fibers/field_quality.py`:

```python
"""Characterise the orientation field against hand-traced ground truth.

Every walker-level fix attempted on this tracer -- tangent smoothing, bounded
coasting, seed non-maximum suppression -- assumed the orientation field is
accurate enough to follow. That assumption was never measured. This module
measures it: the angle between the Hessian tangent and the true fiber tangent,
at ground-truth nodes.

Read-only by construction. Nothing here changes tracer behaviour.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from .skeleton_io import Fiber


class NodeKind:
    """Why a ground-truth node was used or excluded."""

    INTERIOR = "interior"
    ENDPOINT = "endpoint"
    BRANCH = "branch"
    ISOLATED = "isolated"
    DEGENERATE = "degenerate"


def _adjacency(fiber: Fiber) -> dict[int, list[int]]:
    adj: dict[int, list[int]] = defaultdict(list)
    for a, b in np.asarray(fiber.edges, dtype=int):
        adj[int(a)].append(int(b))
        adj[int(b)].append(int(a))
    return adj


def _raw_tangent(coords: np.ndarray, i: int, nbrs: list[int]) -> np.ndarray | None:
    """Unnormalised tangent at node i, or None if it has no well-defined one.

    Interior nodes use a central difference between their two neighbours, which
    bisects the two edges. Using one edge instead would bias every tangent
    toward whichever neighbour happened to be listed first.
    """
    if len(nbrs) == 1:
        return coords[nbrs[0]] - coords[i]
    if len(nbrs) == 2:
        return coords[nbrs[1]] - coords[nbrs[0]]
    return None


def count_node_kinds(fiber: Fiber) -> dict[str, int]:
    """Count every node by kind, including the ones `gt_tangents` excludes."""
    coords = np.asarray(fiber.coords, dtype=float)
    adj = _adjacency(fiber)
    counts = {k: 0 for k in (NodeKind.INTERIOR, NodeKind.ENDPOINT, NodeKind.BRANCH,
                             NodeKind.ISOLATED, NodeKind.DEGENERATE)}
    for i in range(len(coords)):
        nbrs = adj.get(i, [])
        if len(nbrs) == 0:
            counts[NodeKind.ISOLATED] += 1
            continue
        if len(nbrs) >= 3:
            counts[NodeKind.BRANCH] += 1
            continue
        raw = _raw_tangent(coords, i, nbrs)
        if raw is None or float(np.linalg.norm(raw)) < 1e-9:
            counts[NodeKind.DEGENERATE] += 1
            continue
        counts[NodeKind.ENDPOINT if len(nbrs) == 1 else NodeKind.INTERIOR] += 1
    return counts


def gt_tangents(fiber: Fiber) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Coordinates, unit tangents and kinds for every usable node of one fiber.

    Branch nodes (degree >= 3) are excluded: a junction has no single tangent,
    and silently picking one would inject error that is not the field's fault.
    Isolated and zero-length cases are excluded for the same reason. All of them
    are still counted by `count_node_kinds`.
    """
    coords = np.asarray(fiber.coords, dtype=float)
    adj = _adjacency(fiber)

    out_c: list[np.ndarray] = []
    out_t: list[np.ndarray] = []
    kinds: list[str] = []

    for i in range(len(coords)):
        nbrs = adj.get(i, [])
        if len(nbrs) == 0 or len(nbrs) >= 3:
            continue
        raw = _raw_tangent(coords, i, nbrs)
        if raw is None:
            continue
        n = float(np.linalg.norm(raw))
        if n < 1e-9:
            continue
        out_c.append(coords[i])
        out_t.append(raw / n)
        kinds.append(NodeKind.ENDPOINT if len(nbrs) == 1 else NodeKind.INTERIOR)

    if not out_c:
        return np.zeros((0, 3)), np.zeros((0, 3)), []
    return np.asarray(out_c), np.asarray(out_t), kinds
```

- [ ] **Step 4: Run the tests**

```bash
uv run python -m pytest tests/test_field_quality.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/field_quality.py tests/test_field_quality.py
git commit -m "$(cat <<'EOF'
feat(fibers): ground-truth tangent extraction from the NML graph

Interior nodes use a central difference so the tangent bisects both edges.
Branch, isolated and zero-length nodes are excluded rather than guessed at --
a junction has no single tangent and inventing one would inject error that is
not the field's fault -- but every exclusion is counted.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Sign-ambiguous angular error

**Files:**
- Modify: `src/vesuvius_autoresearch/fibers/field_quality.py`
- Modify: `tests/test_field_quality.py`

**Interfaces:**
- Consumes: nothing from Task 1 at runtime.
- Produces: `angular_error_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray` — accepts `(N, 3)` arrays (or a single `(3,)` pair) and returns `(N,)` errors in degrees, in `[0, 90]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_field_quality.py`:

```python
from vesuvius_autoresearch.fibers.field_quality import angular_error_deg


def test_identical_directions_have_zero_error():
    a = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, a), 0.0, atol=1e-9)


def test_opposite_directions_have_zero_error():
    """The load-bearing property: orientation is defined only up to sign.

    A field that returns -t where the truth is +t is perfectly correct. Scoring
    that as 180 degrees would make a good field look catastrophic.
    """
    a = np.array([[1.0, 0.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, -a), 0.0, atol=1e-9)


def test_perpendicular_directions_give_ninety_degrees():
    a = np.array([[1.0, 0.0, 0.0]])
    b = np.array([[0.0, 1.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, b), 90.0, atol=1e-9)


def test_known_angle_is_recovered_and_never_exceeds_ninety():
    for deg in (10.0, 25.0, 44.0, 89.0, 91.0, 170.0):
        r = np.deg2rad(deg)
        a = np.array([[1.0, 0.0, 0.0]])
        b = np.array([[np.cos(r), np.sin(r), 0.0]])
        got = float(angular_error_deg(a, b)[0])
        expected = min(deg, 180.0 - deg)
        assert abs(got - expected) < 1e-6, (deg, got, expected)
        assert 0.0 <= got <= 90.0


def test_unnormalised_inputs_are_handled():
    a = np.array([[3.0, 0.0, 0.0]])
    b = np.array([[0.0, 7.0, 0.0]])
    np.testing.assert_allclose(angular_error_deg(a, b), 90.0, atol=1e-9)
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run python -m pytest tests/test_field_quality.py -v -k angular
```

Expected: `ImportError: cannot import name 'angular_error_deg'`.

- [ ] **Step 3: Implement**

Add to `field_quality.py`:

```python
def angular_error_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Angle between two orientation fields, in degrees, modulo 180.

    Taking `abs` of the dot product is what makes this an *orientation*
    comparison rather than a *direction* one. An eigenvector field is defined
    only up to sign, so `-t` is exactly as correct as `t`; scoring the flip as
    180 degrees would make a perfectly good field look catastrophic. Errors
    therefore live in [0, 90], and 90 means "perpendicular", the worst possible.
    """
    a = np.atleast_2d(np.asarray(a, dtype=float))
    b = np.atleast_2d(np.asarray(b, dtype=float))
    na = np.linalg.norm(a, axis=1, keepdims=True)
    nb = np.linalg.norm(b, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        a = a / np.where(na < 1e-12, np.nan, na)
        b = b / np.where(nb < 1e-12, np.nan, nb)
    cos = np.abs(np.sum(a * b, axis=1))
    return np.degrees(np.arccos(np.clip(cos, 0.0, 1.0)))
```

- [ ] **Step 4: Run the tests**

```bash
uv run python -m pytest tests/test_field_quality.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/field_quality.py tests/test_field_quality.py
git commit -m "$(cat <<'EOF'
feat(fibers): sign-ambiguous angular error between orientation fields

Uses |dot| so a flipped tangent scores zero rather than 180 degrees. An
eigenvector field is defined only up to sign, so treating this as a direction
comparison would make a perfectly good field look catastrophic.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Per-cube analysis, with the synthetic sanity check

**Files:**
- Modify: `src/vesuvius_autoresearch/fibers/field_quality.py`
- Modify: `tests/test_field_quality.py`

**Interfaces:**
- Consumes: `gt_tangents`, `count_node_kinds`, `angular_error_deg`.
- Produces:
  - `sample_field(dirs, valid, coords) -> tuple[np.ndarray, np.ndarray]` returning `(sampled_dirs, defined_mask)`. Nearest-voxel lookup, matching `_direction_at`'s convention. Out-of-bounds counts as undefined.
  - `local_curvature_deg(coords, tangents, kinds) -> np.ndarray` — turn angle at each node in degrees; `nan` for endpoints.
  - `perpendicular_offsets(tangent, radius, n=6) -> np.ndarray` — `(n, 3)` unit vectors perpendicular to `tangent`, scaled by `radius`.
  - `analyse_cube(skeleton, dirs, valid, shape, offsets=(0.0, 1.0, 2.0, 3.0)) -> dict` — the per-cube result dict. Keys: `n_fibers`, `node_kinds`, `n_scored`, `field_undefined_frac`, `error_deg` (array), `curvature_deg` (array), `spacing` (array), `offset_error` (dict mapping offset float to median error), `frac_over_25`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_field_quality.py`:

```python
from vesuvius_autoresearch.fibers.field_quality import (
    analyse_cube,
    local_curvature_deg,
    perpendicular_offsets,
    sample_field,
)
from vesuvius_autoresearch.fibers.skeleton_io import Skeleton


def _tube_field(shape=(32, 32, 32), axis=0, angle_deg=0.0):
    """A constant orientation field rotated `angle_deg` away from `axis`."""
    r = np.deg2rad(angle_deg)
    d = np.zeros(3)
    d[axis] = np.cos(r)
    d[(axis + 1) % 3] = np.sin(r)
    dirs = np.broadcast_to(d, shape + (3,)).copy()
    valid = np.ones(shape, dtype=bool)
    return dirs, valid


def test_perfect_field_scores_near_zero():
    """The sanity check that catches an axis-convention error.

    A wrong axis convention would produce large, plausible-looking errors and
    read as a real finding about the model. This makes that impossible to miss.
    """
    fib = _line_fiber(n=10, axis=0, spacing=2.0)
    fib.coords[:, 1] += 10.0
    fib.coords[:, 2] += 10.0
    dirs, valid = _tube_field(axis=0, angle_deg=0.0)

    res = analyse_cube(Skeleton(fibers=[fib]), dirs, valid, (32, 32, 32))
    assert res["n_scored"] == 10
    assert float(np.median(res["error_deg"])) < 1e-6
    assert res["field_undefined_frac"] == 0.0


def test_known_rotation_is_recovered():
    fib = _line_fiber(n=10, axis=0, spacing=2.0)
    fib.coords[:, 1] += 10.0
    fib.coords[:, 2] += 10.0
    dirs, valid = _tube_field(axis=0, angle_deg=17.0)

    res = analyse_cube(Skeleton(fibers=[fib]), dirs, valid, (32, 32, 32))
    assert abs(float(np.median(res["error_deg"])) - 17.0) < 1e-6


def test_negating_the_field_changes_nothing():
    fib = _line_fiber(n=10, axis=0, spacing=2.0)
    fib.coords[:, 1] += 10.0
    fib.coords[:, 2] += 10.0
    dirs, valid = _tube_field(axis=0, angle_deg=17.0)

    a = analyse_cube(Skeleton(fibers=[fib]), dirs, valid, (32, 32, 32))
    b = analyse_cube(Skeleton(fibers=[fib]), -dirs, valid, (32, 32, 32))
    np.testing.assert_allclose(a["error_deg"], b["error_deg"], atol=1e-12)


def test_undefined_field_is_reported_not_scored():
    fib = _line_fiber(n=10, axis=0, spacing=2.0)
    fib.coords[:, 1] += 10.0
    fib.coords[:, 2] += 10.0
    dirs, valid = _tube_field(axis=0)
    valid[:5] = False  # half the fiber sits where the field is undefined

    res = analyse_cube(Skeleton(fibers=[fib]), dirs, valid, (32, 32, 32))
    assert 0.0 < res["field_undefined_frac"] < 1.0
    assert res["n_scored"] < 10


def test_out_of_bounds_nodes_count_as_undefined():
    fib = _line_fiber(n=4, axis=0, spacing=2.0)
    fib.coords[:, 0] += 100.0  # entirely outside a 32^3 cube
    fib.coords[:, 1] += 10.0
    fib.coords[:, 2] += 10.0
    dirs, valid = _tube_field()

    res = analyse_cube(Skeleton(fibers=[fib]), dirs, valid, (32, 32, 32))
    assert res["field_undefined_frac"] == 1.0
    assert res["n_scored"] == 0


def test_perpendicular_offsets_are_perpendicular():
    t = np.array([1.0, 2.0, 3.0])
    t = t / np.linalg.norm(t)
    offs = perpendicular_offsets(t, radius=2.0, n=6)
    assert offs.shape == (6, 3)
    np.testing.assert_allclose(offs @ t, 0.0, atol=1e-9)
    np.testing.assert_allclose(np.linalg.norm(offs, axis=1), 2.0, atol=1e-9)


def test_local_curvature_is_zero_on_a_straight_line():
    fib = _line_fiber(n=6)
    coords, tangents, kinds = gt_tangents(fib)
    curv = local_curvature_deg(coords, tangents, kinds)
    interior = np.array([k == NodeKind.INTERIOR for k in kinds])
    np.testing.assert_allclose(curv[interior], 0.0, atol=1e-9)
    assert np.all(np.isnan(curv[~interior]))


def test_sample_field_uses_nearest_voxel():
    dirs, valid = _tube_field(shape=(8, 8, 8))
    dirs[3, 3, 3] = np.array([0.0, 1.0, 0.0])
    got, defined = sample_field(dirs, valid, np.array([[3.4, 3.4, 2.9]]))
    assert bool(defined[0]) is True
    np.testing.assert_allclose(got[0], np.array([0.0, 1.0, 0.0]), atol=1e-12)
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run python -m pytest tests/test_field_quality.py -v
```

Expected: `ImportError` for the four new names.

- [ ] **Step 3: Implement**

Add to `field_quality.py`:

```python
def sample_field(
    dirs: np.ndarray, valid: np.ndarray, coords: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-voxel lookup of the orientation field at float coordinates.

    Nearest-neighbour, not interpolation, because that is what `_direction_at`
    does during a walk -- this must characterise the field the tracer actually
    sees. Out-of-bounds positions are reported undefined rather than clipped,
    since clipping would silently score an edge voxel against a node outside it.
    """
    coords = np.atleast_2d(np.asarray(coords, dtype=float))
    idx = np.rint(coords).astype(int)
    shape = np.asarray(valid.shape)

    inb = np.ones(len(idx), dtype=bool)
    for a in range(3):
        inb &= (idx[:, a] >= 0) & (idx[:, a] < shape[a])

    out = np.zeros((len(idx), 3), dtype=float)
    defined = np.zeros(len(idx), dtype=bool)
    if inb.any():
        sel = idx[inb]
        v = valid[sel[:, 0], sel[:, 1], sel[:, 2]]
        d = dirs[sel[:, 0], sel[:, 1], sel[:, 2]]
        out[inb] = d
        defined[inb] = v
    return out, defined


def local_curvature_deg(
    coords: np.ndarray, tangents: np.ndarray, kinds: list[str]
) -> np.ndarray:
    """Turn angle at each interior node, in degrees. NaN at endpoints.

    Measured between consecutive tangents along the node ordering, which is
    contiguous within a fiber as `gt_tangents` emits it. Separates "the field is
    noisy" from "the fiber genuinely bends more than the walker's turn limit".
    """
    n = len(coords)
    out = np.full(n, np.nan, dtype=float)
    for i in range(n):
        if kinds[i] != NodeKind.INTERIOR or i == 0 or i == n - 1:
            continue
        out[i] = float(angular_error_deg(tangents[i - 1][None, :],
                                         tangents[i + 1][None, :])[0])
    return out


def perpendicular_offsets(tangent: np.ndarray, radius: float, n: int = 6) -> np.ndarray:
    """`n` vectors of length `radius`, evenly spaced in the plane normal to `tangent`."""
    t = np.asarray(tangent, dtype=float)
    t = t / max(float(np.linalg.norm(t)), 1e-12)
    seed = np.array([1.0, 0.0, 0.0]) if abs(t[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(t, seed)
    u /= max(float(np.linalg.norm(u)), 1e-12)
    v = np.cross(t, u)
    ang = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return radius * (np.cos(ang)[:, None] * u[None, :] + np.sin(ang)[:, None] * v[None, :])


def analyse_cube(
    skeleton,
    dirs: np.ndarray,
    valid: np.ndarray,
    shape: tuple[int, int, int],
    offsets: tuple[float, ...] = (0.0, 1.0, 2.0, 3.0),
) -> dict:
    """Angular error of the orientation field against one cube's ground truth."""
    kind_counts = {k: 0 for k in (NodeKind.INTERIOR, NodeKind.ENDPOINT, NodeKind.BRANCH,
                                  NodeKind.ISOLATED, NodeKind.DEGENERATE)}
    all_err: list[np.ndarray] = []
    all_curv: list[np.ndarray] = []
    all_spacing: list[np.ndarray] = []
    n_nodes = 0
    n_undefined = 0
    off_err: dict[float, list[np.ndarray]] = {float(o): [] for o in offsets}

    for fib in skeleton.fibers:
        for k, v in count_node_kinds(fib).items():
            kind_counts[k] += v

        coords, tangents, kinds = gt_tangents(fib)
        if len(coords) == 0:
            continue

        sampled, defined = sample_field(dirs, valid, coords)
        n_nodes += len(coords)
        n_undefined += int((~defined).sum())
        if defined.any():
            all_err.append(angular_error_deg(tangents[defined], sampled[defined]))
            curv = local_curvature_deg(coords, tangents, kinds)
            all_curv.append(curv[defined])

        seg = np.linalg.norm(np.diff(np.asarray(fib.coords, dtype=float), axis=0), axis=1)
        if len(seg):
            all_spacing.append(seg)

        # Secondary cut: does the field degrade away from the centreline? The
        # true tangent inside a fiber's cross-section is the centreline's.
        for o in offsets:
            if o == 0.0:
                if defined.any():
                    off_err[0.0].append(
                        angular_error_deg(tangents[defined], sampled[defined]))
                continue
            pts, tgt = [], []
            for c, t in zip(coords, tangents):
                for d in perpendicular_offsets(t, o):
                    pts.append(c + d)
                    tgt.append(t)
            if not pts:
                continue
            s2, d2 = sample_field(dirs, valid, np.asarray(pts))
            if d2.any():
                off_err[float(o)].append(
                    angular_error_deg(np.asarray(tgt)[d2], s2[d2]))

    err = np.concatenate(all_err) if all_err else np.zeros(0)
    curv = np.concatenate(all_curv) if all_curv else np.zeros(0)
    spacing = np.concatenate(all_spacing) if all_spacing else np.zeros(0)

    return {
        "n_fibers": len(skeleton.fibers),
        "node_kinds": kind_counts,
        "n_scored": int(len(err)),
        "field_undefined_frac": (float(n_undefined / n_nodes) if n_nodes else 0.0),
        "error_deg": err,
        "curvature_deg": curv,
        "spacing": spacing,
        "offset_error": {
            o: (float(np.median(np.concatenate(v))) if v else float("nan"))
            for o, v in off_err.items()
        },
        "frac_over_25": (float((err > 25.0).mean()) if len(err) else float("nan")),
    }
```

- [ ] **Step 4: Run the tests**

```bash
uv run python -m pytest tests/test_field_quality.py -v
uv run python -m pytest tests/ -q -k fiber
```

Expected: 20 passed in the new file; the wider fiber suite still passes (91 before this work, plus the new tests).

If `test_known_rotation_is_recovered` fails while `test_perfect_field_scores_near_zero` passes, the error metric is wrong. If both fail, suspect an axis convention — but note that `fiber_direction` already returns `(z, y, x)`, so no conversion should be needed anywhere. **Do not add one to make a test pass**; report instead.

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/field_quality.py tests/test_field_quality.py
git commit -m "$(cat <<'EOF'
feat(fibers): per-cube orientation field analysis

Nearest-voxel sampling to match what a walk actually sees, out-of-bounds
reported undefined rather than clipped, plus the off-centreline and curvature
cuts. Includes the synthetic sanity check that a perfect field scores ~0 and a
known 17-degree rotation comes back as 17 -- an axis-convention error would
otherwise produce large, plausible numbers and read as a real finding.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Run all six cubes and write the verdict

**Files:**
- Create: `scripts/analyze_orientation_field.py`
- Create: `reports/fiber_orientation_field_quality.md`

**Interfaces:**
- Consumes: `analyse_cube` and friends from Task 3; `parse_nml`, `origin_from_stem`, `size_from_stem` from `skeleton_io`; `hessian`, `fiber_direction` from `detection`.

- [ ] **Step 1: Write the driver**

Create `scripts/analyze_orientation_field.py`:

```python
"""Characterise the fiber_hz_vt orientation field against hand-traced ground truth.

Builds the field exactly as `bench_cli.cmd_trace` does -- hessian(P, gauss_sigma=2,
sigma=3) then fiber_direction -- so this measures the field the tracer consumes,
not a reimplementation.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from vesuvius_autoresearch.fibers.detection import fiber_direction, hessian
from vesuvius_autoresearch.fibers.field_quality import analyse_cube
from vesuvius_autoresearch.fibers.skeleton_io import (
    origin_from_stem,
    parse_nml,
    size_from_stem,
)

SRC = pathlib.Path("local_data/fiber_skeletons")
TURN_LIMIT_DEG = 25.0

CUBES = [
    "s1_00497_01497_03997_256",
    "s1_00497_02497_02997_256",
    "s1_00997_02497_02997_256",
    "s1_08997_02997_02497_256",
    "s1_10997_02997_02997_256",
    "s5_03997_01497_03997_256",
]


def run(stem: str) -> dict:
    size = size_from_stem(stem)
    shape = (size, size, size)
    skel = parse_nml(SRC / f"{stem}.nml", origin_zyx=origin_from_stem(stem))
    prob = np.load(SRC / f"{stem}_fiberprob.npy")
    if prob.shape != shape:
        raise SystemExit(f"{stem}: expected {shape}, got {prob.shape}")

    J, _ = hessian(prob.copy(), gauss_sigma=2, sigma=3)
    dirs, valid = fiber_direction(J)
    res = analyse_cube(skel, np.asarray(dirs), np.asarray(valid), shape)

    err = res["error_deg"]
    q = (lambda p: float(np.percentile(err, p))) if len(err) else (lambda p: float("nan"))
    row = {
        "cube": stem,
        "n_fibers": res["n_fibers"],
        "n_scored": res["n_scored"],
        "field_undefined_frac": round(res["field_undefined_frac"], 4),
        "median_deg": round(q(50), 2),
        "p90_deg": round(q(90), 2),
        "p99_deg": round(q(99), 2),
        "frac_over_25": round(res["frac_over_25"], 4),
        "median_curvature_deg": (
            round(float(np.nanmedian(res["curvature_deg"])), 2)
            if len(res["curvature_deg"]) else float("nan")
        ),
        "median_spacing_vox": (
            round(float(np.median(res["spacing"])), 2) if len(res["spacing"]) else float("nan")
        ),
        "node_kinds": res["node_kinds"],
        "offset_median_deg": {str(k): round(v, 2) for k, v in res["offset_error"].items()},
    }
    print(
        f"{stem}: median {row['median_deg']}deg  p90 {row['p90_deg']}deg  "
        f"over-{int(TURN_LIMIT_DEG)}deg {row['frac_over_25']:.1%}  "
        f"undefined {row['field_undefined_frac']:.1%}  n={row['n_scored']}"
    )
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cube", default=None, help="run one cube instead of all six")
    ap.add_argument("--json-out", default="reports/fiber_orientation_field_quality.json")
    args = ap.parse_args()

    stems = [args.cube] if args.cube else CUBES
    rows = [run(s) for s in stems]
    pathlib.Path(args.json_out).write_text(
        json.dumps({"turn_limit_deg": TURN_LIMIT_DEG, "cubes": rows}, indent=2) + "\n"
    )
    print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke one cube**

```bash
uv run python scripts/analyze_orientation_field.py --cube s1_00497_01497_03997_256
```

Expected: one summary line and a JSON file. Sanity-check before trusting it: `n_scored` should be in the low thousands (the cube has 87 usable fibers), and `field_undefined_frac` should be well under 1.0. If median error is ~90 degrees, stop — that is the signature of an axis or convention error, not a finding.

- [ ] **Step 3: Run all six**

```bash
uv run python scripts/analyze_orientation_field.py
```

- [ ] **Step 4: Write the report**

Create `reports/fiber_orientation_field_quality.md`. It must contain, with every value measured and no placeholders:

1. **One-paragraph statement of why**: three walker-level fixes are spent, the one gain they produced was abstention rather than tracing (`high_curvature` rose 750 → 876 and 664 → 738 at the shipped window), and every one of those fixes assumed a field nobody had measured.
2. **The method**, including that the field is built exactly as `cmd_trace` builds it, that error is mod 180, and that branch/isolated/degenerate nodes are excluded — with the counts.
3. **The main table**: per cube and pooled — `n_scored`, `field_undefined_frac`, median, p90, p99, `frac_over_25`.
4. **The three secondary cuts**: error versus offset from the centreline; median local curvature against the 25-degree turn limit; and the per-cube spread, with the cross-scroll cube called out.
5. **The node-spacing caveat**, stated plainly: the ground-truth tangent is estimated from annotation spacing, so if spacing is large relative to curvature the measured error is an **upper bound**.
6. **The verdict**, naming which of the three forks the data supports:
   - median well above 25 degrees → the field cannot support any walker; multi-scale orientation is the target;
   - median a few degrees with a thin tail → the field is fine; greedy sequential walking is the wrong algorithm and global assembly is the target;
   - small median with a fat tail → isolated bad voxels dominate, which is what coasting was meant to fix and did not.

Write the verdict from the numbers. **Do not soften a finding that the field is bad, and do not inflate one that it is good.** If the data sits between forks, say that rather than forcing a choice.

- [ ] **Step 5: Confirm nothing under fibers/ was modified**

```bash
git status --short
git diff --stat HEAD -- src/vesuvius_autoresearch/fibers/trace.py \
    src/vesuvius_autoresearch/fibers/detection.py \
    src/vesuvius_autoresearch/fibers/skeleton_io.py
```

Expected: the second command prints nothing. `field_quality.py` is a new file and is fine; the three existing modules must be untouched.

- [ ] **Step 6: Commit**

```bash
git add scripts/analyze_orientation_field.py reports/fiber_orientation_field_quality.md \
        reports/fiber_orientation_field_quality.json
git commit -m "$(cat <<'EOF'
report(fibers): orientation field quality against hand-traced ground truth

First direct measurement of whether the fiber_hz_vt Hessian tangent is accurate
enough to follow. Six cubes, every in-bounds ground-truth node, error mod 180,
read against the walker's 25-degree turn limit.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage.** Measurement definition → Tasks 1-3. Mod-180 handling → Task 2, with the flip test as its load-bearing case. Field-undefined reported separately → Task 3 (`field_undefined_frac`, plus the out-of-bounds test). Three-way fork verdict → Task 4 Step 4 item 6. Secondary cut 1 (off-centreline) → `perpendicular_offsets` + `offset_error`. Cut 2 (curvature) → `local_curvature_deg`. Cut 3 (per-cube incl. cross-scroll) → Task 4's table. Branch/endpoint handling with counts → Task 1, `count_node_kinds`. Node-spacing caveat → Task 4 Step 4 item 5. Synthetic known-answer test → Task 3 (`test_perfect_field_scores_near_zero`, `test_known_rotation_is_recovered`). Sign test → Task 3 (`test_negating_the_field_changes_nothing`). Read-only constraint → Task 4 Step 5 verifies it explicitly. All six success criteria are covered.

**Type consistency.** `gt_tangents` returns `(coords, tangents, kinds)` in Task 1 and is unpacked that way in Task 3's `analyse_cube` and in `test_local_curvature_is_zero_on_a_straight_line`. `angular_error_deg` takes and returns 2-D/1-D arrays consistently and is called with `[None, :]` slices in `local_curvature_deg`. `sample_field` returns `(dirs, defined)` and is unpacked that way in both call sites. `NodeKind` members are referenced by the same names throughout. The result-dict keys produced by `analyse_cube` match exactly those read by `run()` in Task 4.

**One deliberate deviation from the spec, flagged.** The spec calls this a "read-only analysis script"; the plan puts the reusable logic in a new module `src/vesuvius_autoresearch/fibers/field_quality.py` rather than inside `scripts/`, so it can be unit-tested. The read-only constraint is preserved in the sense that matters — no existing file under `fibers/` is modified, and Task 4 Step 5 checks this — but a reviewer should know the choice was made knowingly.
