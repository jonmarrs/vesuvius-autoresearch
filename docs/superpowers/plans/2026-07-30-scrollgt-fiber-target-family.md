# ScrollGT Fiber Connectivity Target Family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the fiber connectivity benchmark as a second target family inside ScrollGT, scoreable with no GPU, no model download, and no network.

**Architecture:** Two modules (`eval_trace.py`, `skeleton_io.py`) port from `vesuvius_autoresearch.fibers` into a new `scrollgt/fibers/` subpackage. Ground-truth skeletons and the reference fiber mask are pre-extracted into `data/fibers_<cube>/` as compressed arrays, so scoring and the anti-gaming floors reproduce from shipped data alone. The baseline tracer and `fiber_hz_vt` inference stay in `vesuvius-autoresearch` as the benchmark's *entrant*, never as part of the benchmark.

**Tech Stack:** Python 3.10+, numpy, scipy (`ndimage`), pytest, hatchling. No torch anywhere in ScrollGT.

## Global Constraints

- **Two repositories.** Tasks 1-7 commit in `/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt`. Tasks 0 and 8 commit in `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch`. Every task states its repo. Never mix the two in one commit.
- **ScrollGT stays lean.** Declared dependencies after this work: `numpy>=1.26`, `scipy>=1.11`, `scikit-learn>=1.4`, `pillow>=10.0`. **No torch, no GPU, no network on any ScrollGT code path.** Adding any other dependency is a plan violation.
- **Both ERL variants always print together**, never one alone. Raw ERL is gameable to within 23% of the oracle by labelling everything once.
- **Tolerance is part of every scorecard.** Default `2.0` voxels. A number without its tolerance is meaningless.
- **Splits and merges are reported separately and never summed.**
- **No 128³ sub-volume number is carried into ScrollGT.** Every published figure derives from the Task 0 full-cube run.
- **Voxel size is 7.91 um.** Cube shape is 256³ for all six targets.
- **No AI-authorship markers** in README, `BASELINES.md`, or any user-facing copy. Commits use a `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailer and no `Claude-Session:` line.
- **The six cubes:** `s1_00497_01497_03997_256` (87 GT fibers), `s1_00497_02497_02997_256` (109), `s1_00997_02497_02997_256` (128), `s1_08997_02997_02497_256` (105), `s1_10997_02997_02997_256` (91), `s5_03997_01497_03997_256` (68, the designated cross-scroll split).

---

### Task 0: Full-cube floor re-run (prerequisite)

**Repo:** `vesuvius-autoresearch`

The published headline currently mixes scales: the five-labelling gaming table was measured on a 128³ sub-volume, while the baselines table is full 256³, and only two of the four floors were ever run at full-cube scale. Everything downstream reads from one full-cube run produced here.

**Files:**
- Modify: `src/vesuvius_autoresearch/fibers/bench_cli.py`
- Output: `reports/fiber_benchmark_all_cubes.json`

**Interfaces:**
- Consumes: nothing.
- Produces: `reports/fiber_benchmark_all_cubes.json` with, for every one of the six cubes, a `rows` dict containing keys `oracle`, `floor_single_instance`, `floor_connected_components`, `floor_voxel_instances`, `floor_random_instances`, `tracer_strict_relink`. Each row is `ConnectivityScores.as_row()` output. Task 3 and Task 7 read this file.

- [ ] **Step 1: Confirm which floors the current report is missing**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
python3 -c "
import json
d = json.load(open('reports/fiber_benchmark_all_cubes.json'))
for cube, v in d['cubes'].items():
    print(cube, sorted(v['rows']))
"
```

Expected: every cube lists only `oracle`, `floor_single_instance`, `floor_connected_components`, `tracer_strict_relink`. The two missing floors are `floor_voxel_instances` and `floor_random_instances`.

- [ ] **Step 2: Locate where bench_cli builds the floor rows**

```bash
grep -n "floor_single_instance\|floor_connected_components\|floor_voxel\|floor_random" \
  src/vesuvius_autoresearch/fibers/bench_cli.py
```

The floors come from `eval_trace.floor_single_instance`, `floor_voxel_instances`, `floor_connected_components`, `floor_random_instances` — all four already exist and are already tested. Only the benchmark driver omits two of them.

- [ ] **Step 3: Add the two missing floors to the driver**

In the function that assembles `rows` for a cube, alongside the existing floor entries add:

```python
rows["floor_voxel_instances"] = score_tracing(
    gt, floor_voxel_instances(mask), tolerance=tolerance
).as_row()
rows["floor_random_instances"] = score_tracing(
    gt, floor_random_instances(mask, n=50, seed=0), tolerance=tolerance
).as_row()
```

Import `floor_voxel_instances` and `floor_random_instances` from `.eval_trace` if they are not already imported.

`floor_voxel_instances` assigns a distinct id to every foreground voxel, so on a 256³ cube at 6.0% density it produces ~1.0M instances. Verify it completes in reasonable time on one cube before running all six.

- [ ] **Step 4: Run one cube and check the two new rows appear**

```bash
python -m vesuvius_autoresearch.fibers.bench_cli floors --cube s1_00497_01497_03997_256
```

Expected: five floor/oracle rows print. `floor_voxel_instances` must show ERL near 1.0 and `floor_random_instances` must show merge-penalized ERL near 0.00. All four floors must show **identical** coverage and precision to each other (0.9177 / 0.2194 on this cube) — that identity is the finding this benchmark exists to publish, so if it does not hold, stop and investigate rather than proceeding.

- [ ] **Step 5: Run all six cubes and refresh the report**

```bash
python -m vesuvius_autoresearch.fibers.bench_cli floors --all-cubes \
  --json-out reports/fiber_benchmark_all_cubes.json
```

(If `--all-cubes` is not the actual flag, read `bench_cli.py --help` and use the flag that iterates every cube.)

- [ ] **Step 6: Verify the shared-metric identity holds on all six cubes**

```bash
python3 -c "
import json
d = json.load(open('reports/fiber_benchmark_all_cubes.json'))
for cube, v in d['cubes'].items():
    floors = [k for k in v['rows'] if k.startswith('floor_')]
    covs = {round(v['rows'][k]['coverage'], 4) for k in floors}
    precs = {round(v['rows'][k]['precision'], 4) for k in floors}
    assert len(floors) == 4, (cube, floors)
    assert len(covs) == 1 and len(precs) == 1, (cube, covs, precs)
    print(f'{cube}: 4 floors, coverage={covs.pop()}, precision={precs.pop()}')
print('OK: coverage and precision cannot rank a labelling, on every cube')
"
```

Expected: six lines then `OK`. An `AssertionError` means the finding does not replicate at full-cube scale — stop and report, do not proceed to Task 1.

- [ ] **Step 7: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/bench_cli.py reports/fiber_benchmark_all_cubes.json
git commit -m "$(cat <<'EOF'
bench(fibers): all four floors at full-cube scale on all six cubes

The gaming finding (coverage and precision are properties of the mask, not
the labelling) was only ever measured on a 128^3 sub-volume. Runs the voxel
-instances and random-instances floors at full 256^3 so every published
number sits on one scale.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1: `scrollgt.fibers.skeleton_io`

**Repo:** `scrollgt`

**Files:**
- Create: `src/scrollgt/fibers/__init__.py`
- Create: `src/scrollgt/fibers/skeleton_io.py`
- Create: `tests/test_fiber_skeleton_io.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class Fiber` — dataclass with `id: int`, `name: str`, `node_ids: np.ndarray` (N,), `coords: np.ndarray` (N,3) float ordered `(z, y, x)`, `edges: np.ndarray` (E,2) int indexing into `coords`. Methods `__len__()`, `segment_lengths(voxel_size_um=None) -> np.ndarray`, `total_length(voxel_size_um=None) -> float`, `in_bounds_mask(shape) -> np.ndarray`.
  - `class Skeleton` — dataclass with `fibers: list[Fiber]`, `scale_um: tuple[float,float,float] | None`, `origin_zyx: tuple[int,int,int] | None`. Properties `n_nodes`, `n_edges`; methods `__len__()`, `total_length(voxel_size_um=None)`.
  - `origin_from_stem(stem: str) -> tuple[int, int, int]`
  - `size_from_stem(stem: str) -> int`
  - `parse_nml(path, origin_zyx=None) -> Skeleton`
  - `rasterize(skeleton: Skeleton, shape, dilate: int = 0) -> np.ndarray`

- [ ] **Step 1: Copy the module verbatim and rewrite only its imports**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/scrollgt
mkdir -p src/scrollgt/fibers
cp ../vesuvius-autoresearch/src/vesuvius_autoresearch/fibers/skeleton_io.py \
   src/scrollgt/fibers/skeleton_io.py
grep -n "vesuvius_autoresearch" src/scrollgt/fibers/skeleton_io.py
```

Expected: no matches — this module imports only `re`, `dataclasses`, `pathlib`, `numpy`, and `scipy.ndimage` (inside `rasterize`). If any match appears, rewrite it to the `scrollgt.fibers` equivalent.

Preserve the module docstring in full. It records the coordinate conventions — NML `x,y,z` against volume `z,y,x`, the origin encoded in the filename as `<scroll>_<z>_<y>_<x>_<size>`, and the empirical 1.000 landing rate that pins them. That provenance is the reason the reader can be trusted; deleting it to "clean up" would be a defect.

Amend only the docstring's report cross-reference, which points at a path that does not exist in this repo:

```
(see `reports/fiber_tracing_step0_gt_survey.md`)
```

becomes

```
(established in jonmarrs/vesuvius-autoresearch, reports/fiber_tracing_step0_gt_survey.md)
```

- [ ] **Step 2: Create the subpackage `__init__.py`**

```python
"""Fiber connectivity evaluation: hand-traced ground truth, ERL, and anti-gaming floors."""

from .eval_trace import (
    ConnectivityScores,
    floor_connected_components,
    floor_random_instances,
    floor_single_instance,
    floor_voxel_instances,
    oracle_from_skeleton,
    score_tracing,
)
from .skeleton_io import (
    Fiber,
    Skeleton,
    origin_from_stem,
    parse_nml,
    rasterize,
    size_from_stem,
)

__all__ = [
    "ConnectivityScores",
    "Fiber",
    "Skeleton",
    "score_tracing",
    "oracle_from_skeleton",
    "floor_single_instance",
    "floor_voxel_instances",
    "floor_connected_components",
    "floor_random_instances",
    "parse_nml",
    "rasterize",
    "origin_from_stem",
    "size_from_stem",
]
```

This imports `eval_trace`, which does not exist until Task 2. That is expected — the import error is what Task 2 Step 2 resolves. Do not stub it.

- [ ] **Step 3: Copy the synthetic tests only**

```bash
cp ../vesuvius-autoresearch/tests/test_fiber_skeleton_io.py tests/test_fiber_skeleton_io.py
```

Then edit `tests/test_fiber_skeleton_io.py`:

1. Change the import block from `vesuvius_autoresearch.fibers.skeleton_io` to `scrollgt.fibers.skeleton_io`.
2. **Delete** `test_real_nodes_land_exactly_on_semantic_label` and `test_real_rasterization_stays_inside_semantic_label`, together with the `DATA`, `CUBES`, and `pytestmark_data` module-level definitions they depend on. Those tests require the 17 MB raw cubes in `local_data/fiber_skeletons/`, which ScrollGT deliberately does not ship. They stay in `vesuvius-autoresearch`, where the cubes exist; Task 3 carries their guarantee across the repo boundary by recording the measured landing rate into each target's `meta.json`.

The nine synthetic tests that remain — including `test_coords_are_zyx_not_xyz` and `test_stem_parsing_is_zyx_order`, which pin the convention without needing real data — all keep running.

- [ ] **Step 4: Add scipy to the declared dependencies**

In `pyproject.toml`, change:

```toml
dependencies = [
    "numpy>=1.26",
    "scikit-learn>=1.4",
    "pillow>=10.0",
]
```

to:

```toml
dependencies = [
    "numpy>=1.26",
    "scipy>=1.11",
    "scikit-learn>=1.4",
    "pillow>=10.0",
]
```

`scipy` is already installed transitively — `scikit-learn` requires it — so the resolved environment does not change. Declaring it explicitly is correct because `scrollgt.fibers` imports `scipy.ndimage` directly rather than through sklearn.

Also register the subpackage for the wheel build. Confirm the existing block reads:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/scrollgt"]
```

`packages = ["src/scrollgt"]` includes subpackages automatically, so no change is needed there. Verify rather than assume.

- [ ] **Step 5: Run the tests**

```bash
python -m pytest tests/test_fiber_skeleton_io.py -v
```

Expected: 9 passed. A `ModuleNotFoundError` for `scrollgt.fibers.eval_trace` means `__init__.py` is being imported — that is Task 2's job. To confirm this module is sound in isolation before then, run:

```bash
python -c "
import sys; sys.path.insert(0, 'src')
import importlib.util
spec = importlib.util.spec_from_file_location('sio', 'src/scrollgt/fibers/skeleton_io.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.origin_from_stem('s1_00497_01497_03997_256'))
"
```

Expected: `(497, 1497, 3997)` — origin in `(z, y, x)` order.

- [ ] **Step 6: Commit**

```bash
git add src/scrollgt/fibers/__init__.py src/scrollgt/fibers/skeleton_io.py \
        tests/test_fiber_skeleton_io.py pyproject.toml
git commit -m "$(cat <<'EOF'
feat(fibers): NML skeleton reader for hand-traced fiber ground truth

Ports skeleton_io from vesuvius-autoresearch. Keeps the synthetic convention
tests (NML x,y,z against volume z,y,x; origin from filename); drops the two
tests requiring the raw 17 MB cubes, whose guarantee Task 3 carries over as
recorded provenance in each target's meta.json.

Declares scipy explicitly: scrollgt.fibers imports scipy.ndimage directly
rather than through scikit-learn.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `scrollgt.fibers.eval_trace`

**Repo:** `scrollgt`

**Files:**
- Create: `src/scrollgt/fibers/eval_trace.py`
- Create: `tests/test_fiber_eval_trace.py`

**Interfaces:**
- Consumes: `Skeleton` from Task 1.
- Produces:
  - `class ConnectivityScores` — dataclass with fields `erl`, `erl_merge_penalized`, `coverage`, `precision`, `n_gt_fibers`, `n_pred_instances`, `splits`, `merges`, `merged_instances`, `gt_length`, `pred_length`, `tolerance`, `run_lengths`. Method `as_row() -> dict` returning the flat leaderboard dict (excludes `run_lengths`).
  - `score_tracing(gt: Skeleton, instances: np.ndarray, tolerance: float = 2.0, step: float = 0.5, restrict_to_bounds: bool = True) -> ConnectivityScores`
  - `floor_single_instance(mask) -> np.ndarray`
  - `floor_voxel_instances(mask) -> np.ndarray`
  - `floor_connected_components(mask, connectivity: int = 3) -> np.ndarray`
  - `floor_random_instances(mask, n: int = 50, seed: int = 0) -> np.ndarray`
  - `oracle_from_skeleton(gt: Skeleton, shape, radius: float = 1.0) -> np.ndarray`

- [ ] **Step 1: Copy the module and rewrite its one internal import**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/scrollgt
cp ../vesuvius-autoresearch/src/vesuvius_autoresearch/fibers/eval_trace.py \
   src/scrollgt/fibers/eval_trace.py
```

Change the single internal import:

```python
from vesuvius_autoresearch.fibers.skeleton_io import Skeleton
```

to:

```python
from .skeleton_io import Skeleton
```

Verify nothing else references the old package:

```bash
grep -n "vesuvius_autoresearch" src/scrollgt/fibers/eval_trace.py
```

Expected: no output.

Preserve the module docstring in full — it is the argument for why ERL and the merge count replace voxel precision, and it is quoted by the README.

Amend the one cross-repo reference, `(see `reports/fiber_semantic_inference.md`)`, to `(established in jonmarrs/vesuvius-autoresearch, reports/fiber_semantic_inference.md)`.

- [ ] **Step 2: Verify the subpackage now imports cleanly**

```bash
python -c "import sys; sys.path.insert(0,'src'); import scrollgt.fibers as f; print(sorted(f.__all__))"
```

Expected: the 12 exported names print. This is the step that resolves the deferred import from Task 1 Step 2.

- [ ] **Step 3: Copy the tests and repoint their import**

```bash
cp ../vesuvius-autoresearch/tests/test_fiber_eval_trace.py tests/test_fiber_eval_trace.py
sed -i 's/vesuvius_autoresearch\.fibers/scrollgt.fibers/g' tests/test_fiber_eval_trace.py
grep -n "vesuvius_autoresearch" tests/test_fiber_eval_trace.py
```

Expected: no output. All 13 tests are synthetic — they build small skeletons and instance arrays in-process and need no data files.

- [ ] **Step 4: Run the tests**

```bash
python -m pytest tests/test_fiber_eval_trace.py -v
```

Expected: 13 passed. These cover the oracle ceiling, all four floors, split behaviour, gap handling, both tolerance directions (rescues a 1-voxel offset; does *not* silently merge neighbours), the empty prediction, out-of-bounds GT exclusion, and `as_row` serialisability.

- [ ] **Step 5: Run the whole suite to confirm nothing regressed**

```bash
python -m pytest tests/ -q
```

Expected: the pre-existing ink and column tests still pass, plus 22 new fiber tests.

- [ ] **Step 6: Commit**

```bash
git add src/scrollgt/fibers/eval_trace.py tests/test_fiber_eval_trace.py
git commit -m "$(cat <<'EOF'
feat(fibers): ERL, split/merge counts, and the four anti-gaming floors

Ports eval_trace from vesuvius-autoresearch. Both ERL variants are computed
together because the gap between them is the merge cost, and raw ERL alone
is gameable by labelling everything as one instance.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Target extraction

**Repo:** `vesuvius-autoresearch` for the script; the generated data is committed in `scrollgt`.

Produces the six shipped targets. This is the task that makes scoring GPU-free and network-free.

**Files:**
- Create: `scripts/export_fiber_targets.py` (in `vesuvius-autoresearch`)
- Create (generated, in `scrollgt`): `data/fibers_<cube>/skeleton.npz`, `data/fibers_<cube>/mask.npz`, `data/fibers_<cube>/meta.json` for each of the six cubes

**Interfaces:**
- Consumes: `parse_nml`, `origin_from_stem`, `size_from_stem` from `vesuvius_autoresearch.fibers.skeleton_io`; `reports/fiber_benchmark_all_cubes.json` from Task 0.
- Produces: the on-disk target format that Task 4's `load_fiber_target` reads. The `skeleton.npz` keys are exactly `coords`, `edges`, `fiber_offsets`, `edge_offsets`, `fiber_ids`, `fiber_names`, `scale_um`, `origin_zyx`, `shape`. The `mask.npz` keys are exactly `packed`, `shape`.

- [ ] **Step 1: Write the extraction script**

Create `scripts/export_fiber_targets.py`:

```python
"""Export fiber-skeleton cubes as self-contained ScrollGT targets.

Reads the raw cubes in local_data/fiber_skeletons/ (NML traces, the shipped
semantic label, and the fiber_hz_vt probability volume) and writes, per cube,
a directory that ScrollGT can score with no GPU, no model, and no network.

The semantic label is used here for one purpose only: to measure the rate at
which in-bounds NML nodes land on fiber-positive voxels. That rate is the
empirical proof of the coordinate convention (NML x,y,z against volume z,y,x,
origin from the filename), and it is recorded into meta.json so the guarantee
survives into a repo that does not ship the raw cubes.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import tifffile

from vesuvius_autoresearch.fibers.skeleton_io import (
    origin_from_stem,
    parse_nml,
    size_from_stem,
)

SRC = pathlib.Path("local_data/fiber_skeletons")
VOXEL_UM = 7.91
THRESHOLD = 0.5
CROSS_SCROLL_SPLIT = "s5_03997_01497_03997_256"

CUBES = [
    "s1_00497_01497_03997_256",
    "s1_00497_02497_02997_256",
    "s1_00997_02497_02997_256",
    "s1_08997_02997_02497_256",
    "s1_10997_02997_02997_256",
    "s5_03997_01497_03997_256",
]


def pack_skeleton(skel, shape) -> dict:
    """Flatten a Skeleton into fixed-key arrays with per-fiber offsets."""
    coords, edges, fiber_offsets, edge_offsets = [], [], [0], [0]
    fiber_ids, fiber_names = [], []
    for fib in skel.fibers:
        coords.append(np.asarray(fib.coords, dtype=np.float32))
        # rebase local edge indices onto the concatenated coords array
        edges.append(np.asarray(fib.edges, dtype=np.int32) + fiber_offsets[-1])
        fiber_offsets.append(fiber_offsets[-1] + len(fib.coords))
        edge_offsets.append(edge_offsets[-1] + len(fib.edges))
        fiber_ids.append(fib.id)
        fiber_names.append(fib.name)
    return {
        "coords": np.concatenate(coords) if coords else np.zeros((0, 3), np.float32),
        "edges": np.concatenate(edges) if edges else np.zeros((0, 2), np.int32),
        "fiber_offsets": np.asarray(fiber_offsets, dtype=np.int64),
        "edge_offsets": np.asarray(edge_offsets, dtype=np.int64),
        "fiber_ids": np.asarray(fiber_ids, dtype=np.int64),
        "fiber_names": np.asarray(fiber_names, dtype=object),
        "scale_um": np.asarray(skel.scale_um or (VOXEL_UM,) * 3, dtype=np.float64),
        "origin_zyx": np.asarray(skel.origin_zyx, dtype=np.int64),
        "shape": np.asarray(shape, dtype=np.int64),
    }


def landing_rate(skel, semantic) -> float:
    """Fraction of in-bounds NML nodes landing on a fiber-positive voxel."""
    hits = total = 0
    for fib in skel.fibers:
        ok = fib.in_bounds_mask(semantic.shape)
        if not ok.any():
            continue
        idx = np.rint(fib.coords[ok]).astype(int)
        idx = np.clip(idx, 0, np.asarray(semantic.shape) - 1)
        hits += int((semantic[idx[:, 0], idx[:, 1], idx[:, 2]] > 0).sum())
        total += int(ok.sum())
    return hits / total if total else 0.0


def export(stem: str, out_root: pathlib.Path, bench: dict) -> None:
    size = size_from_stem(stem)
    shape = (size, size, size)
    skel = parse_nml(SRC / f"{stem}.nml", origin_zyx=origin_from_stem(stem))
    prob = np.load(SRC / f"{stem}_fiberprob.npy")
    semantic = tifffile.imread(SRC / f"{stem}_semantic.tif")

    if prob.shape != shape or semantic.shape != shape:
        raise SystemExit(f"{stem}: expected {shape}, got prob={prob.shape} semantic={semantic.shape}")

    rate = landing_rate(skel, semantic)
    if rate < 0.999:
        raise SystemExit(
            f"{stem}: node landing rate {rate:.4f} < 0.999 — the coordinate "
            f"convention does not hold for this cube; do not ship it"
        )

    mask = prob >= THRESHOLD
    n_in_bounds = sum(int(f.in_bounds_mask(shape).sum()) for f in skel.fibers)

    out = out_root / f"fibers_{stem}"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "skeleton.npz", **pack_skeleton(skel, shape))
    np.savez_compressed(
        out / "mask.npz",
        packed=np.packbits(mask),
        shape=np.asarray(shape, dtype=np.int64),
    )

    meta = {
        "target_id": f"fibers_{stem}",
        "family": "fiber_connectivity",
        "cube": stem,
        "scroll": "Scroll 5" if stem.startswith("s5_") else "Scroll 1 (PHerc. Paris 4)",
        "split": "cross_scroll" if stem == CROSS_SCROLL_SPLIT else "primary",
        "shape": list(shape),
        "origin_zyx": list(origin_from_stem(stem)),
        "voxel_size_um": VOXEL_UM,
        "tolerance": bench["tolerance"],
        "ground_truth": {
            "origin": (
                "villa fiber-skeletons dataset, dl.ash2txt.org/datasets/fiber-skeletons/ — "
                "every papyrus fiber in the cube hand-traced in WEBKNOSSOS at 7.91 um"
            ),
            "source_file": f"nml/{stem}.nml",
            "n_fibers": len(skel.fibers),
            "n_nodes_in_bounds": n_in_bounds,
            "note": (
                "Annotators traced beyond the cube boundary, so a substantial "
                "fraction of nodes fall outside and are excluded from scoring."
            ),
        },
        "convention_check": {
            "claim": (
                "NML nodes are x,y,z in absolute scroll space; volumes index z,y,x; "
                "the cube origin is encoded in the filename as <scroll>_<z>_<y>_<x>_<size>"
            ),
            "measured_node_landing_rate_on_semantic_label": round(rate, 6),
            "verified_against": f"labelsTr/{stem}.tif (shipped semantic label)",
        },
        "mask": {
            "model": "scrollprize/fiber_hz_vt (Apache-2.0)",
            "threshold": THRESHOLD,
            "density": round(float(mask.mean()), 6),
            "note": (
                "Every entrant is scored against this identical mask, so scorecard "
                "differences come from the instance labelling rather than from a "
                "better or worse segmentation."
            ),
        },
        "floors": bench["cubes"][stem]["rows"],
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    kb = (out / "mask.npz").stat().st_size / 1e3
    print(f"{stem}: {len(skel.fibers)} fibers, landing {rate:.4f}, mask {kb:.0f} KB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-root", required=True, help="scrollgt data/ directory")
    ap.add_argument("--bench", default="reports/fiber_benchmark_all_cubes.json")
    args = ap.parse_args()

    bench = json.loads(pathlib.Path(args.bench).read_text())
    for stem in CUBES:
        export(stem, pathlib.Path(args.out_root), bench)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the export**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
python scripts/export_fiber_targets.py \
  --out-root ../scrollgt/data
```

Expected: six lines, each reporting a landing rate of `1.0000` and a mask around 250 KB. A `SystemExit` about the landing rate means the convention does not hold for that cube — stop and investigate; do not lower the threshold to make it pass.

- [ ] **Step 3: Check the total shipped size**

```bash
du -sh ../scrollgt/data/fibers_* | sort -h && du -sh ../scrollgt/data
```

Expected: roughly 250-350 KB per cube directory, and a `data/` total under 5 MB. If any single cube exceeds 1 MB, the mask is not being packed — check that `np.packbits` is applied before `savez_compressed`.

- [ ] **Step 4: Verify a target round-trips**

```bash
cd ../scrollgt
python3 -c "
import numpy as np
d = np.load('data/fibers_s1_00497_01497_03997_256/skeleton.npz', allow_pickle=True)
print('keys:', sorted(d.files))
print('fibers:', len(d['fiber_ids']), 'nodes:', len(d['coords']))
m = np.load('data/fibers_s1_00497_01497_03997_256/mask.npz')
shape = tuple(m['shape'])
mask = np.unpackbits(m['packed'])[:int(np.prod(shape))].astype(bool).reshape(shape)
print('mask', mask.shape, 'density', round(float(mask.mean()), 4))
"
```

Expected: 9 keys, 87 fibers, mask `(256, 256, 256)` with density `0.0599`.

- [ ] **Step 5: Commit the script in vesuvius-autoresearch**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add scripts/export_fiber_targets.py
git commit -m "$(cat <<'EOF'
feat(fibers): export cubes as self-contained ScrollGT targets

Packs hand-traced skeletons and the fiber_hz_vt reference mask (packbits,
~250 KB per 256^3 cube) so connectivity scoring needs no GPU, no model, and
no network. Records the measured node landing rate into meta.json, carrying
the coordinate-convention proof into a repo that does not ship raw cubes;
refuses to export a cube whose rate falls below 0.999.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Commit the data in scrollgt**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/scrollgt
git add data/fibers_*
git commit -m "$(cat <<'EOF'
data: six fiber connectivity targets (5x Scroll 1, 1x Scroll 5)

Hand-traced ground truth from villa's fiber-skeletons dataset plus the
reference fiber_hz_vt mask, ~250 KB per cube. s5_03997_01497_03997_256 is
designated the cross-scroll reporting split; the ground truth is public, so
this is a labelled convention and not a claim of held-out secrecy.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Target loader and the zero-GPU reproduction guarantee

**Repo:** `scrollgt`

**Files:**
- Create: `src/scrollgt/fibers/target.py`
- Create: `tests/test_fiber_target.py`
- Modify: `src/scrollgt/fibers/__init__.py`

**Interfaces:**
- Consumes: the on-disk format from Task 3; `Fiber`, `Skeleton` from Task 1; the floors and `score_tracing` from Task 2.
- Produces:
  - `load_fiber_target(target_dir) -> tuple[Skeleton, np.ndarray, dict]` returning `(skeleton, mask_bool_3d, meta)`.
  - `score_fiber_prediction(labels_path, target_dir, with_floors: bool = True) -> dict` returning `{"target": str, "prediction": str, "split": str, "tolerance": float, "metrics": dict, "floors": dict, "below_baseline": bool}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fiber_target.py`:

```python
"""The shipped targets must be scoreable with no GPU, no model, and no network."""

import json
import pathlib

import numpy as np
import pytest

from scrollgt.fibers import score_tracing
from scrollgt.fibers.target import load_fiber_target, score_fiber_prediction

TARGETS = sorted(pathlib.Path("data").glob("fibers_*"))


def test_six_targets_are_shipped():
    assert len(TARGETS) == 6, [t.name for t in TARGETS]


@pytest.mark.parametrize("target", TARGETS, ids=lambda p: p.name)
def test_loads_skeleton_and_mask(target):
    skel, mask, meta = load_fiber_target(target)
    assert len(skel) == meta["ground_truth"]["n_fibers"]
    assert mask.shape == tuple(meta["shape"])
    assert mask.dtype == bool
    assert 0.0 < mask.mean() < 0.5


@pytest.mark.parametrize("target", TARGETS, ids=lambda p: p.name)
def test_convention_proof_is_recorded(target):
    _, _, meta = load_fiber_target(target)
    rate = meta["convention_check"]["measured_node_landing_rate_on_semantic_label"]
    assert rate >= 0.999, f"{target.name}: landing rate {rate}"


@pytest.mark.parametrize("target", TARGETS, ids=lambda p: p.name)
def test_published_floors_reproduce_from_shipped_data(target):
    """The regression that keeps the zero-GPU path real.

    Recomputes the connected-components floor from the shipped mask alone and
    requires it to match the number published in meta.json. A data packaging
    mistake would otherwise be silent.
    """
    from scrollgt.fibers import floor_connected_components

    skel, mask, meta = load_fiber_target(target)
    published = meta["floors"]["floor_connected_components"]
    got = score_tracing(skel, floor_connected_components(mask),
                        tolerance=meta["tolerance"]).as_row()
    assert got["erl"] == pytest.approx(published["erl"], rel=1e-3)
    assert got["erl_merge_penalized"] == pytest.approx(
        published["erl_merge_penalized"], rel=1e-3)
    assert got["coverage"] == pytest.approx(published["coverage"], rel=1e-3)


def test_scoring_an_empty_labelling_is_zero_not_an_error(tmp_path):
    target = TARGETS[0]
    _, mask, _ = load_fiber_target(target)
    p = tmp_path / "empty.npy"
    np.save(p, np.zeros(mask.shape, dtype=np.int32))
    card = score_fiber_prediction(p, target, with_floors=False)
    assert card["metrics"]["erl"] == 0.0
    assert card["metrics"]["coverage"] == 0.0


def test_shape_mismatch_names_the_expected_shape(tmp_path):
    target = TARGETS[0]
    p = tmp_path / "wrong.npy"
    np.save(p, np.zeros((64, 64, 64), dtype=np.int32))
    with pytest.raises(ValueError, match="256"):
        score_fiber_prediction(p, target, with_floors=False)


def test_below_baseline_flag_is_set_when_entry_trails_connected_components(tmp_path):
    target = TARGETS[0]
    _, mask, _ = load_fiber_target(target)
    labels = np.zeros(mask.shape, dtype=np.int32)
    labels[mask] = np.arange(1, int(mask.sum()) + 1)  # one instance per voxel
    p = tmp_path / "voxels.npy"
    np.save(p, labels)
    card = score_fiber_prediction(p, target, with_floors=True)
    assert card["below_baseline"] is True
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
python -m pytest tests/test_fiber_target.py -v
```

Expected: collection error — `ModuleNotFoundError: No module named 'scrollgt.fibers.target'`.

- [ ] **Step 3: Write the loader**

Create `src/scrollgt/fibers/target.py`:

```python
"""Load and score the shipped fiber connectivity targets.

Everything here reads from files committed in this repository. No model, no
GPU, and no network access is used or required.
"""

from __future__ import annotations

import json
import os

import numpy as np

from .eval_trace import (
    floor_connected_components,
    floor_random_instances,
    floor_single_instance,
    floor_voxel_instances,
    score_tracing,
)
from .skeleton_io import Fiber, Skeleton


def _unpack_skeleton(npz) -> Skeleton:
    coords = npz["coords"]
    edges = npz["edges"]
    f_off = npz["fiber_offsets"]
    e_off = npz["edge_offsets"]
    ids = npz["fiber_ids"]
    names = npz["fiber_names"]

    fibers = []
    for i in range(len(ids)):
        c0, c1 = int(f_off[i]), int(f_off[i + 1])
        e0, e1 = int(e_off[i]), int(e_off[i + 1])
        fibers.append(
            Fiber(
                id=int(ids[i]),
                name=str(names[i]),
                node_ids=np.arange(c0, c1, dtype=np.int64),
                coords=coords[c0:c1].astype(float),
                # edges were stored global; rebase to this fiber's local indices
                edges=(edges[e0:e1].astype(np.int64) - c0),
            )
        )
    return Skeleton(
        fibers=fibers,
        scale_um=tuple(float(v) for v in npz["scale_um"]),
        origin_zyx=tuple(int(v) for v in npz["origin_zyx"]),
    )


def load_fiber_target(target_dir):
    """Load one fiber target: (Skeleton, mask bool (Z,Y,X), meta dict)."""
    target_dir = str(target_dir)
    with open(os.path.join(target_dir, "meta.json")) as f:
        meta = json.load(f)

    with np.load(os.path.join(target_dir, "skeleton.npz"), allow_pickle=True) as npz:
        skeleton = _unpack_skeleton(npz)

    with np.load(os.path.join(target_dir, "mask.npz")) as npz:
        shape = tuple(int(v) for v in npz["shape"])
        n = int(np.prod(shape))
        mask = np.unpackbits(npz["packed"])[:n].astype(bool).reshape(shape)

    return skeleton, mask, meta


def _floor_rows(skeleton, mask, tolerance) -> dict:
    return {
        "floor_single_instance": score_tracing(
            skeleton, floor_single_instance(mask), tolerance=tolerance).as_row(),
        "floor_connected_components": score_tracing(
            skeleton, floor_connected_components(mask), tolerance=tolerance).as_row(),
        "floor_voxel_instances": score_tracing(
            skeleton, floor_voxel_instances(mask), tolerance=tolerance).as_row(),
        "floor_random_instances": score_tracing(
            skeleton, floor_random_instances(mask, n=50, seed=0),
            tolerance=tolerance).as_row(),
    }


def score_fiber_prediction(labels_path, target_dir, with_floors: bool = True) -> dict:
    """Score an instance labelling (.npy of ints, 0 = background) against a target."""
    skeleton, mask, meta = load_fiber_target(target_dir)
    labels = np.load(str(labels_path))
    if labels.shape != mask.shape:
        raise ValueError(
            f"prediction shape {labels.shape} != cube shape {mask.shape}; "
            f"label exactly the cube described in meta.json (origin_zyx="
            f"{meta.get('origin_zyx')}, shape={meta.get('shape')})"
        )
    if not np.issubdtype(labels.dtype, np.integer):
        raise ValueError(
            f"prediction dtype {labels.dtype} is not integer; supply instance ids "
            f"(0 = background), not probabilities"
        )

    tolerance = float(meta["tolerance"])
    row = score_tracing(skeleton, labels, tolerance=tolerance).as_row()

    floors = meta.get("floors", {}) if not with_floors else _floor_rows(
        skeleton, mask, tolerance)
    cc = floors.get("floor_connected_components", {})
    below = bool(cc) and row["erl"] < cc["erl"]

    return {
        "target": meta.get("target_id", os.path.basename(os.path.normpath(target_dir))),
        "prediction": os.path.basename(str(labels_path)),
        "split": meta.get("split", "primary"),
        "tolerance": tolerance,
        "metrics": row,
        "floors": floors,
        "below_baseline": below,
    }
```

- [ ] **Step 4: Export the new names**

In `src/scrollgt/fibers/__init__.py`, add to the imports and to `__all__`:

```python
from .target import load_fiber_target, score_fiber_prediction
```

and append `"load_fiber_target"`, `"score_fiber_prediction"` to `__all__`.

- [ ] **Step 5: Run the tests**

```bash
python -m pytest tests/test_fiber_target.py -v
```

Expected: all pass. `test_published_floors_reproduce_from_shipped_data` is the important one — it proves the shipped mask regenerates the published connected-components floor exactly, so the zero-GPU claim is enforced rather than asserted.

If `test_below_baseline_flag_is_set_when_entry_trails_connected_components` is slow, note that one-instance-per-voxel creates ~1M instances on a 256³ cube; it is expected to take tens of seconds and is the same cost Task 0 Step 3 flagged.

- [ ] **Step 6: Commit**

```bash
git add src/scrollgt/fibers/target.py src/scrollgt/fibers/__init__.py tests/test_fiber_target.py
git commit -m "$(cat <<'EOF'
feat(fibers): target loader + the zero-GPU reproduction guarantee

load_fiber_target reads shipped skeletons and the packed reference mask;
score_fiber_prediction scores an instance labelling against them. A test
recomputes the connected-components floor from shipped data and requires it
to match the published number, so a packaging mistake cannot be silent.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: `scrollgt score-fibers`

**Repo:** `scrollgt`

**Files:**
- Create: `src/scrollgt/fibers/report.py`
- Modify: `src/scrollgt/cli.py`
- Create: `tests/test_fibers_cli.py`

**Interfaces:**
- Consumes: `score_fiber_prediction` from Task 4.
- Produces: `fiber_markdown_report(card: dict) -> str`; the `score-fibers` subcommand.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fibers_cli.py`:

```python
"""The scorecard contract: both ERL variants, tolerance, floors, and the flag."""

import json
import pathlib

import numpy as np
import pytest

from scrollgt.cli import main
from scrollgt.fibers.report import fiber_markdown_report

TARGET = "data/fibers_s1_00497_01497_03997_256"


@pytest.fixture
def cc_labels(tmp_path):
    """A real entry: the connected-components labelling of the shipped mask."""
    from scrollgt.fibers import floor_connected_components
    from scrollgt.fibers.target import load_fiber_target

    _, mask, _ = load_fiber_target(TARGET)
    p = tmp_path / "cc.npy"
    np.save(p, floor_connected_components(mask).astype(np.int32))
    return p


def test_report_prints_both_erl_variants_and_tolerance(cc_labels):
    from scrollgt.fibers.target import score_fiber_prediction

    text = fiber_markdown_report(score_fiber_prediction(cc_labels, TARGET))
    assert "ERL" in text
    assert "ERLpen" in text, "merge-penalized ERL must never be omitted"
    assert "tolerance" in text.lower()
    assert "splits" in text.lower() and "merges" in text.lower()


def test_report_lists_all_four_floors(cc_labels):
    from scrollgt.fibers.target import score_fiber_prediction

    text = fiber_markdown_report(score_fiber_prediction(cc_labels, TARGET))
    for floor in ("single instance", "connected components",
                  "one instance per voxel", "50 random"):
        assert floor in text, floor


def test_cli_writes_json(tmp_path, cc_labels, capsys):
    out = tmp_path / "card.json"
    main(["score-fibers", str(cc_labels), TARGET, "--json-out", str(out)])
    card = json.loads(out.read_text())
    assert card["tolerance"] == 2.0
    assert "erl" in card["metrics"] and "erl_merge_penalized" in card["metrics"]
    assert set(card["floors"]) == {
        "floor_single_instance", "floor_connected_components",
        "floor_voxel_instances", "floor_random_instances",
    }


def test_cli_reports_cross_scroll_split(tmp_path, capsys):
    from scrollgt.fibers import floor_connected_components
    from scrollgt.fibers.target import load_fiber_target

    target = "data/fibers_s5_03997_01497_03997_256"
    _, mask, _ = load_fiber_target(target)
    p = tmp_path / "cc5.npy"
    np.save(p, floor_connected_components(mask).astype(np.int32))
    main(["score-fibers", str(p), target])
    assert "cross-scroll" in capsys.readouterr().out.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
python -m pytest tests/test_fibers_cli.py -v
```

Expected: collection error — `No module named 'scrollgt.fibers.report'`.

- [ ] **Step 3: Write the report formatter**

Create `src/scrollgt/fibers/report.py`:

```python
"""Scorecard formatting for fiber connectivity.

Two rules are enforced by construction rather than left to the caller: both
ERL variants always appear together, and the tolerance always appears. Raw ERL
alone is gameable -- labelling an entire cube as one instance scores within
23% of the oracle -- so a card showing one number without the other would be
actively misleading.
"""

from __future__ import annotations

FLOOR_LABELS = {
    "floor_single_instance": "floor: one instance for everything",
    "floor_connected_components": "floor: connected components",
    "floor_voxel_instances": "floor: one instance per voxel",
    "floor_random_instances": "floor: 50 random instances",
}

COLUMNS = ["ERL", "ERLpen", "coverage", "precision", "splits", "merges", "n inst"]


def _row(name: str, r: dict) -> str:
    return (
        f"| {name} | {r['erl']:.2f} | {r['erl_merge_penalized']:.2f} | "
        f"{r['coverage']:.4f} | {r['precision']:.4f} | "
        f"{r['splits']} | {r['merges']} | {r['n_pred_instances']} |"
    )


def fiber_markdown_report(card: dict) -> str:
    lines = [
        f"| {card['prediction']} vs {card['target']} | " + " | ".join(COLUMNS) + " |",
        "|---|" + "|".join(["---"] * len(COLUMNS)) + "|",
        _row("**your labelling**", card["metrics"]),
    ]
    for key, label in FLOOR_LABELS.items():
        if key in card.get("floors", {}):
            lines.append(_row(label, card["floors"][key]))

    split = "cross-scroll split" if card.get("split") == "cross_scroll" else "primary split"
    lines += [
        "",
        f"tolerance {card['tolerance']} voxels ({split}). "
        f"Splits and merges are reported separately and are never summed: a split "
        f"fails to help, a merge corrupts the U/V parameterization.",
    ]

    if card.get("below_baseline"):
        cc = card["floors"]["floor_connected_components"]["erl"]
        lines.append(
            f"\n**BELOW the naive baseline.** Raw ERL {card['metrics']['erl']:.2f} "
            f"trails connected components at {cc:.2f}."
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Wire the subcommand into the CLI**

In `src/scrollgt/cli.py`, add the import at the top alongside the existing ones:

```python
from .fibers.report import fiber_markdown_report
from .fibers.target import score_fiber_prediction
```

Register the parser after the existing `p_cols` block:

```python
    p_fib = sub.add_parser(
        "score-fibers",
        help="score a fiber instance labelling against hand-traced ground truth "
             "(ERL, splits, merges, and the anti-gaming floors)",
    )
    p_fib.add_argument("prediction",
                       help="instance labels (.npy of ints, 0 = background, cube-shaped)")
    p_fib.add_argument("target", help="fiber target directory (data/fibers_<cube>)")
    p_fib.add_argument("--no-floors", action="store_true",
                       help="skip recomputing the floors and use the published values")
    p_fib.add_argument("--json-out", default=None, help="write the scorecard JSON here")
```

And add the dispatch branch alongside the existing `if args.cmd == ...` chain:

```python
    if args.cmd == "score-fibers":
        card = score_fiber_prediction(args.prediction, args.target,
                                      with_floors=not args.no_floors)
        print(fiber_markdown_report(card))
        if args.json_out:
            with open(args.json_out, "w") as f:
                json.dump(card, f, indent=2, default=float)
```

- [ ] **Step 5: Run the tests**

```bash
python -m pytest tests/test_fibers_cli.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Run it by hand to check the output reads well**

```bash
python -c "
import numpy as np
from scrollgt.fibers import floor_connected_components
from scrollgt.fibers.target import load_fiber_target
_, mask, _ = load_fiber_target('data/fibers_s1_00497_01497_03997_256')
np.save('/tmp/cc.npy', floor_connected_components(mask).astype(np.int32))
"
python -m scrollgt.cli score-fibers /tmp/cc.npy data/fibers_s1_00497_01497_03997_256
```

Expected: a markdown table with the entry and four floor rows, the tolerance line, and no `BELOW` flag (connected components cannot trail itself).

- [ ] **Step 7: Commit**

```bash
git add src/scrollgt/fibers/report.py src/scrollgt/cli.py tests/test_fibers_cli.py
git commit -m "$(cat <<'EOF'
feat(fibers): scrollgt score-fibers

Scores an instance labelling against hand-traced ground truth and prints the
four floors alongside it. Both ERL variants and the tolerance are emitted by
construction rather than at the caller's discretion, and an entry trailing
connected components on raw ERL is flagged BELOW the naive baseline.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Pin the finding as an executable claim

**Repo:** `scrollgt`

The benchmark's reason to exist is that coverage and precision cannot rank a labelling. That claim should fail loudly if a future change breaks it.

**Files:**
- Create: `tests/test_fiber_gaming.py`

**Interfaces:**
- Consumes: `load_fiber_target` from Task 4, the floors from Task 2.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the test**

Create `tests/test_fiber_gaming.py`:

```python
"""The finding this benchmark exists to publish, pinned as an executable claim.

Coverage and precision are properties of the fiber *mask*, not of the instance
*labelling*, so four wildly different labellings score identically on them. Only
ERL and the merge count separate a correct tracer from numpy.random.
"""

import numpy as np
import pytest

from scrollgt.fibers import (
    floor_connected_components,
    floor_random_instances,
    floor_single_instance,
    floor_voxel_instances,
    score_tracing,
)
from scrollgt.fibers.target import load_fiber_target

TARGET = "data/fibers_s1_00497_01497_03997_256"


@pytest.fixture(scope="module")
def rows():
    skel, mask, meta = load_fiber_target(TARGET)
    tol = meta["tolerance"]
    return {
        "single": score_tracing(skel, floor_single_instance(mask), tolerance=tol).as_row(),
        "cc": score_tracing(skel, floor_connected_components(mask), tolerance=tol).as_row(),
        "voxel": score_tracing(skel, floor_voxel_instances(mask), tolerance=tol).as_row(),
        "random": score_tracing(skel, floor_random_instances(mask, n=50, seed=0),
                                tolerance=tol).as_row(),
    }


def test_coverage_and_precision_cannot_rank_a_labelling(rows):
    covs = {round(r["coverage"], 4) for r in rows.values()}
    precs = {round(r["precision"], 4) for r in rows.values()}
    assert len(covs) == 1, f"coverage should be identical across labellings, got {covs}"
    assert len(precs) == 1, f"precision should be identical across labellings, got {precs}"


def test_erl_does_separate_them(rows):
    erls = sorted(r["erl"] for r in rows.values())
    assert erls[-1] / max(erls[0], 1e-9) > 50, (
        f"ERL must separate these labellings by orders of magnitude, got {erls}")


def test_raw_erl_alone_is_gameable(rows):
    """Labelling everything once scores near the oracle on raw ERL."""
    _, _, meta = load_fiber_target(TARGET)
    oracle = meta["floors"]["oracle"]["erl"]
    assert rows["single"]["erl"] > 0.6 * oracle, (
        "the single-instance floor is supposed to look deceptively good on raw ERL")


def test_the_merge_penalty_is_what_catches_it(rows):
    assert rows["single"]["erl_merge_penalized"] == 0.0
    assert rows["random"]["erl_merge_penalized"] == 0.0


def test_merges_are_never_summed_into_splits(rows):
    for name, r in rows.items():
        assert "splits" in r and "merges" in r, name
        assert r["splits"] >= 0 and r["merges"] >= 0
```

- [ ] **Step 2: Run it**

```bash
python -m pytest tests/test_fiber_gaming.py -v
```

Expected: 5 passed. A failure in `test_coverage_and_precision_cannot_rank_a_labelling` would mean the headline claim does not hold on the shipped data — stop and report, do not weaken the assertion.

- [ ] **Step 3: Commit**

```bash
git add tests/test_fiber_gaming.py
git commit -m "$(cat <<'EOF'
test(fibers): pin the gaming finding as an executable claim

Four different labellings of the same mask must score identical coverage and
precision while ERL separates them by orders of magnitude, and the single-
instance floor must look near-oracle on raw ERL while its merge-penalized ERL
is exactly zero. If a change breaks this, the benchmark has lost its point.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Documentation, baselines, and CI

**Repo:** `scrollgt`

**Files:**
- Modify: `README.md`
- Modify: `baselines/BASELINES.md`
- Modify: `CONTRIBUTING.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: everything above; `reports/fiber_benchmark_all_cubes.json` from Task 0 for the published numbers.

- [ ] **Step 1: Regenerate the baselines table from the Task 0 report**

```bash
python3 - <<'PY'
import json, pathlib
src = pathlib.Path("../vesuvius-autoresearch/reports/fiber_benchmark_all_cubes.json")
d = json.loads(src.read_text())
print("| cube | tracer ERL | cc ERL | tracer ERLpen | cc ERLpen |")
print("|---|---|---|---|---|")
for cube, v in d["cubes"].items():
    t, c = v["rows"]["tracer_strict_relink"], v["rows"]["floor_connected_components"]
    label = cube.rsplit("_", 1)[0] + (" (cross-scroll)" if cube.startswith("s5_") else "")
    print(f"| {label} | {t['erl']:.1f} | {c['erl']:.1f} | "
          f"{t['erl_merge_penalized']:.1f} | {c['erl_merge_penalized']:.1f} |")
PY
```

Paste the emitted table into `baselines/BASELINES.md` under a new `## Fiber connectivity` heading. **Use the emitted numbers, not the numbers written in this plan** — Task 0 re-ran the floors and its output is authoritative.

- [ ] **Step 2: Write the baselines section**

Under the new heading, above the table, state the result plainly in the repo's existing house style of publishing its own negatives:

> Six 256³ cubes from villa's `fiber-skeletons` dataset, tolerance 2.0 voxels, every row scored
> against the identical `fiber_hz_vt` mask shipped with each target.
>
> **Connected components is a strong baseline, and our own tracer does not beat it** — losing on
> raw ERL and on merge-penalized ERL, on every cube. Fragmentation is the cause: the tracer finds
> the fibers (coverage 0.62-0.88) but cannot hold one identity along them.

Below the table, record what the floors establish:

> All four floors score identical coverage and precision, because those metrics are properties of
> the mask rather than of the labelling. The single-instance floor is the sharpest illustration:
> near-oracle on raw ERL and exactly 0.00 once merges are penalized. A benchmark reporting
> coverage and precision alone cannot distinguish a correct tracer from `numpy.random`.

- [ ] **Step 3: Add the README section**

Add a `## Fiber connectivity targets` section after the existing ink target documentation. It must cover, in the README's existing voice:

- What villa asked for, quoted: *"a tracer that confidently follows fewer fibers correctly is more useful than one that follows more fibers with a higher error rate."*
- The headline finding, with the full-cube numbers from Task 0.
- The quickstart:

```bash
scrollgt score-fibers my_labels.npy data/fibers_s1_00497_01497_03997_256 --json-out card.json
```

- That `my_labels.npy` is a cube-shaped int array, 0 = background, one distinct id per predicted fiber instance.
- That scoring needs no GPU, no model download, and no network — the ground truth and the reference mask ship in the repo.
- That `s5_03997_01497_03997_256` is the designated cross-scroll reporting split, and that because the ground truth is a public villa dataset this is a labelled convention rather than a claim of held-out secrecy.
- That the ground truth is villa's `fiber-skeletons` dataset and the reference mask comes from `scrollprize/fiber_hz_vt` (Apache-2.0).

Also update the one-line description near the top of the README so it covers the suite rather than ink alone.

- [ ] **Step 4: Document the contribution flow**

In `CONTRIBUTING.md`, add a short subsection mirroring the existing target-family flow: how to produce a labelling, how to score it against all six cubes, and that a submitted result must report both ERL variants together with the tolerance.

- [ ] **Step 5: Add the fiber suite to CI**

In `.github/workflows/ci.yml`, confirm the test step runs the whole `tests/` directory. If it enumerates files individually, add `tests/test_fiber_skeleton_io.py`, `tests/test_fiber_eval_trace.py`, `tests/test_fiber_target.py`, `tests/test_fibers_cli.py`, and `tests/test_fiber_gaming.py`.

Add a smoke step mirroring the existing `score-columns` smoke:

```yaml
      - name: score-fibers smoke
        run: |
          python -c "
          import numpy as np
          from scrollgt.fibers import floor_connected_components
          from scrollgt.fibers.target import load_fiber_target
          _, mask, _ = load_fiber_target('data/fibers_s1_00497_01497_03997_256')
          np.save('/tmp/cc.npy', floor_connected_components(mask).astype(np.int32))
          "
          scrollgt score-fibers /tmp/cc.npy data/fibers_s1_00497_01497_03997_256
```

- [ ] **Step 6: Verify the full suite and a clean install**

```bash
python -m pytest tests/ -q
pip install -e . && scrollgt score-fibers --help
```

Expected: all tests pass; the help text prints. Confirm torch is absent from the environment's requirements:

```bash
python -c "import scrollgt.fibers, sys; print('torch' in sys.modules)"
```

Expected: `False`.

- [ ] **Step 7: Commit**

```bash
git add README.md baselines/BASELINES.md CONTRIBUTING.md .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
docs: fiber connectivity target family

Documents the six cube targets, the quickstart, and the cross-scroll split.
Publishes our own tracer's loss to connected components on all six cubes, in
the same house style as the ink baselines.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Correct the stale claim upstream

**Repo:** `vesuvius-autoresearch`

Two documents state the tracer is "marginally ahead of connected components" on merge-penalized ERL. That held on a 128³ sub-volume (24.27 vs 22.47) and does not survive at full-cube scale, where connected components wins on both metrics on all six cubes.

**Files:**
- Modify: `docs/FIBER_TRACING.md`
- Modify: `reports/fiber_connectivity_eval.md`

- [ ] **Step 1: Fix `reports/fiber_connectivity_eval.md`**

The paragraph beginning "On the penalized metric the tracer's best (24.27) is marginally ahead of connected components (22.47)" must be replaced. Keep the 128³ table as the historical record it is, but label the section explicitly as the 128³ sub-volume, and add a note directly beneath the claim:

> **Superseded at full-cube scale (2026-07-30).** Re-run on all six full 256³ cubes, connected
> components wins on *both* metrics on every cube — raw ERL by 4.5-7.4x and merge-penalized ERL by
> 1.6-3.5x. The "marginally ahead on the penalized metric" reading above is an artefact of the
> 128³ sub-volume and should not be cited. Full-cube numbers:
> `reports/fiber_benchmark_all_cubes.json`.

Use the Task 0 output for the ratios rather than the numbers written here, and recompute them if Task 0 changed any row.

- [ ] **Step 2: Fix `docs/FIBER_TRACING.md`**

Two edits:

1. The tables under "The headline finding" are 128³ sub-volume numbers. Add a parenthetical to the section heading making the scale explicit, and add a line pointing at the full-cube figures.
2. The "Current standing" paragraph already says "the tracer does not beat connected components on ERL", which remains true. Strengthen it to state the loss is on **both** metrics at full-cube scale, and drop any implication that the penalized metric is a near-tie.

- [ ] **Step 3: Add a pointer to the packaged benchmark**

At the top of `docs/FIBER_TRACING.md`, after the opening paragraph, add:

> **The measurement layer now ships as a ScrollGT target family** — six cubes, scoreable with no
> GPU and no download: <https://github.com/jonmarrs/scrollgt>. This document remains the record of
> the research and of the baseline tracer, which is the benchmark's entrant rather than part of it.

- [ ] **Step 4: Check no other document repeats the stale claim**

```bash
grep -rn "marginally ahead\|22.47\|24.27" docs/ reports/ README.md
```

Expected: matches only in the two files just edited, each now carrying the superseding note. Fix any others found.

- [ ] **Step 5: Commit**

```bash
git add docs/FIBER_TRACING.md reports/fiber_connectivity_eval.md
git commit -m "$(cat <<'EOF'
docs(fibers): correct the "marginally ahead" claim to full-cube scale

At 256^3 on all six cubes, connected components beats the tracer on both raw
and merge-penalized ERL. The near-tie on the penalized metric was an artefact
of the 128^3 sub-volume. Points at the packaged ScrollGT target family.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: prerequisite floor re-run → Task 0; scope/boundary → Tasks 1-2; dependency impact → Task 1 Step 4; data and splits → Task 3; interface → Task 5; baselines → Task 7; correction → Task 8; testing → Tasks 1, 2, 4, 6, and 7 Step 5. All six success criteria are covered: (1) Task 4 + Task 7 Step 6, (2) Task 4 Step 5, (3) Task 6 + Task 7 Step 3, (4) Task 7 Steps 1-2, (5) Task 8, (6) Task 0 plus the "use the emitted numbers" instruction in Task 7 Step 1.

**Type consistency.** `load_fiber_target` returns `(Skeleton, np.ndarray, dict)` in Task 4 and is called with that unpacking in Tasks 4, 5, 6, and 7. `score_fiber_prediction(labels_path, target_dir, with_floors=True)` keeps one signature throughout. `as_row()` keys (`erl`, `erl_merge_penalized`, `coverage`, `precision`, `splits`, `merges`, `n_pred_instances`) are used consistently by `report.py` and every test. The `skeleton.npz` and `mask.npz` key sets written in Task 3 match exactly what `_unpack_skeleton` and `load_fiber_target` read in Task 4.

**One known sharp edge.** `floor_voxel_instances` on a 256³ cube at 6.0% density produces ~1M instances. It is exercised in Task 0 Step 3, Task 4 Step 5, and Task 6. If runtime proves impractical, the correct response is to record the measured cost — not to drop the floor, which is load-bearing for the headline finding.
