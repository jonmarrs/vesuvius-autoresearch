# Fiber Tracer: Clearing Our Own Published Baseline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce fiber fragmentation enough that the tracer beats each cube's own connected-components merge-penalized ERL, without buying the gain with merges.

**Architecture:** Two changes to `src/vesuvius_autoresearch/fibers/trace.py`, each targeting a measured stop reason. Fix A compares each walk step against a sign-aligned mean of the last `k` directions instead of the single previous step, so voxel-quantization noise cannot terminate a walk. Fix B suppresses seed candidates lying within a thin disc perpendicular to an accepted seed's tangent. Both default to the current behaviour so the published baseline stays reproducible.

**Tech Stack:** Python 3.10, numpy, scipy.ndimage, pytest. GPU only for the semantic model (`fiber_hz_vt`) via `uv run`.

## Global Constraints

- **Repo:** `/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch`, branch `feat/fiber-tracer-connectivity`. Never commit to `main`. Nothing in the sibling `scrollgt` repo may be touched — the tracer is the benchmark's *entrant*, and editing the benchmark to flatter the entrant is the exact failure the protocol exists to prevent.
- **Run Python via `uv run`.** System `python3` lacks `tifffile`.
- **THE PRE-REGISTERED CONTRACT — copied verbatim from the spec, not revisable:**
  - **Primary metric: merge-penalized ERL**, against **each cube's own** connected-components floor. Dev targets: `s1_00497_01497_03997_256` 23.16 → beat **37.13**; `s1_00497_02497_02997_256` 33.60 → beat **64.27**.
  - **Raw ERL is reported every time, improved or not.** Currently 26.60 vs 197.11 on cube 1.
  - **Splits, merges, coverage, and instance count are reported every time.**
  - **AUTOMATIC FAILURE: ERLpen improves while merges rise.** A merge-bought win is not a win.
- **Cube roles — do not deviate:**
  - **dev** (all decisions): `s1_00497_01497_03997_256`, `s1_00497_02497_02997_256`
  - **held out** (scored once, at the end, in Task 6 only): `s1_00997_02497_02997_256`, `s1_08997_02997_02497_256`, `s1_10997_02997_02997_256`
  - **never touched** (scored once in Task 6, informs no decision, ever): `s5_03997_01497_03997_256`
- **Count every configuration you try** and record the running total in each report. This number is published.
- **Both new parameters default to current behaviour** (`tangent_window=1`, `seed_nms_radius=0.0`) so the published `tracer_strict_relink` row stays reproducible.
- Commit messages end with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` and no `Claude-Session:` line. No AI-authorship markers in code, comments, or reports.
- Held-out ERLpen floors, recorded here so they cannot be renegotiated: `s1_00997_02497_02997` 29.8 vs 56.5; `s1_08997_02997_02497` 30.8 vs 106.1; `s1_10997_02997_02997` 34.2 vs 57.7; `s5_03997_01497_03997` 25.4 vs 51.1.

---

### Task 1: Baseline regression lock

Pin the numbers being improved on, so a later "improvement" cannot be an accident of a changed default.

**Files:**
- Create: `tests/test_fiber_trace_baseline.py`
- Create: `reports/fiber_tracer_improvement.md`

**Interfaces:**
- Consumes: `trace_fibers`, `TraceParams` as they exist today.
- Produces: `reports/fiber_tracer_improvement.md` with a `## Baseline` section. Tasks 3, 5, and 6 append to this file.

- [ ] **Step 1: Write a test that pins current walk-termination behaviour**

```python
"""Baseline lock: the tracer's current behaviour, so an improvement is provable.

These tests do not assert the tracer is good. They assert it behaves exactly as
it did when the published baseline was measured, so that a later change can be
attributed to the change rather than to drift.
"""

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.trace import TraceParams, trace_fibers


def _straight_tube(shape=(40, 40, 40), axis=0, centre=(20, 20), radius=2.0):
    """A single straight fiber along `axis`, with a clean orientation field."""
    response = np.zeros(shape, dtype=float)
    dirs = np.zeros(shape + (3,), dtype=float)
    valid = np.zeros(shape, dtype=bool)
    zz, yy, xx = np.indices(shape)
    coords = [zz, yy, xx]
    perp = [i for i in range(3) if i != axis]
    d2 = (coords[perp[0]] - centre[0]) ** 2 + (coords[perp[1]] - centre[1]) ** 2
    inside = d2 <= radius * radius
    response[inside] = 1.0
    dirs[inside, axis] = 1.0
    valid[inside] = True
    return response, dirs, valid


def test_defaults_preserve_published_behaviour():
    """tangent_window and seed_nms_radius must default to a no-op."""
    p = TraceParams()
    assert p.tangent_window == 1, "default must reproduce the published baseline"
    assert p.seed_nms_radius == 0.0, "default must reproduce the published baseline"


def test_straight_fiber_traces_end_to_end():
    response, dirs, valid = _straight_tube()
    res = trace_fibers(
        response=response, seed_response=response, directions=dirs, valid=valid,
        params=TraceParams(seed_threshold=0.5, continue_threshold=0.25, min_length=5.0),
    )
    assert len(res) == 1, f"expected one fiber, got {len(res)}: {res.stop_counts}"
    assert res.fibers[0].length > 25.0


def test_single_corrupted_voxel_terminates_the_walk_today():
    """The defect being fixed, pinned as current behaviour.

    One voxel with a wildly wrong orientation splits the fiber in two, because
    the walk compares against only the immediately previous step.
    """
    response, dirs, valid = _straight_tube()
    dirs[20, 20, 20] = np.array([0.0, 1.0, 0.0])  # perpendicular to the fiber

    res = trace_fibers(
        response=response, seed_response=response, directions=dirs, valid=valid,
        params=TraceParams(seed_threshold=0.5, continue_threshold=0.25,
                           min_length=3.0, max_angle_deg=25.0),
    )
    assert res.stop_counts.get("high_curvature", 0) >= 1, (
        "the corrupted voxel should currently stop a walk; if it does not, this "
        "test no longer pins the defect and must be rewritten before proceeding"
    )
```

- [ ] **Step 2: Run it**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
uv run python -m pytest tests/test_fiber_trace_baseline.py -v
```

Expected: `test_defaults_preserve_published_behaviour` FAILS (the attributes do not exist yet). The other two PASS. That failure is correct — Task 2 adds the parameters.

If `test_single_corrupted_voxel_terminates_the_walk_today` does not see a `high_curvature` stop, **stop and report**: the synthetic geometry is not reproducing the real defect, and the fix cannot be validated against it.

- [ ] **Step 3: Reproduce the published baseline on both dev cubes**

```bash
uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_00497_01497_03997_256
uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube s1_00497_02497_02997_256
```

Expected on cube 1, matching the published row exactly: ERL 26.60, ERLpen 23.16, coverage 0.623, splits 1872, merges 38, 669 instances. Stop counts approximately `{'high_curvature': 750, 'collision': 455, 'low_response': 243, 'out_of_bounds': 196}`.

If cube 1 does not reproduce, **stop and report** — the baseline is not what the benchmark published, and nothing downstream is meaningful.

- [ ] **Step 4: Start the report**

Create `reports/fiber_tracer_improvement.md`:

```markdown
# Clearing our own published fiber baseline

Pre-registered contract: `docs/superpowers/specs/2026-07-31-fiber-tracer-beat-baseline-design.md`.
Primary metric is merge-penalized ERL against **each cube's own** connected-components floor.
Raw ERL, splits, merges and coverage are reported every time regardless of outcome. An ERLpen
gain accompanied by a rise in merges is a **failure**, not a win.

Dev cubes: `s1_00497_01497_03997_256`, `s1_00497_02497_02997_256`.
Held out until the final run: the three other Scroll-1 cubes.
Never used for any decision: `s5_03997_01497_03997_256`.

**Configurations tried so far: 1** (the baseline itself).

## Baseline (reproduced <DATE>)

| cube | ERL | ERLpen | cc ERLpen | coverage | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 26.60 | 23.16 | 37.13 | 0.623 | 1872 | 38 | 669 |
| s1_00497_02497_02997 | <fill from Step 3> | | 64.27 | | | | |

Stop reasons, cube 1: `high_curvature` 750 (46%), `collision` 455 (28%),
`low_response` 243 (15%), `out_of_bounds` 196 (12%).
```

Replace `<DATE>` and `<fill from Step 3>` with the actual values you measured. Do not leave placeholders.

- [ ] **Step 5: Commit**

```bash
git add tests/test_fiber_trace_baseline.py reports/fiber_tracer_improvement.md
git commit -m "$(cat <<'EOF'
test(fibers): lock the published tracer baseline before changing it

Pins the corrupted-voxel defect as current behaviour and reproduces the
published row on both dev cubes, so a later improvement is attributable to the
change rather than to drift.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Fix A — tangent smoothing

**Files:**
- Modify: `src/vesuvius_autoresearch/fibers/trace.py` (`TraceParams`, `_walk`)
- Modify: `tests/test_fiber_trace_baseline.py`

**Interfaces:**
- Consumes: `TraceParams`, `_walk` as they exist.
- Produces: `TraceParams.tangent_window: int = 1`. `_walk` unchanged in signature.

**Root cause, so you implement the right thing:** `params.step` is 0.7 voxels and `_direction_at` uses **nearest-neighbour** lookup, so the orientation field is piecewise-constant per voxel and jumps discontinuously at voxel boundaries. `_walk` compares each new direction against `prev` — the single immediately-preceding step. One noisy voxel, crossed once, terminates the walk permanently. The fix makes the existing test robust; it must **not** loosen `max_angle_deg`, which would buy coverage by letting walks jump between fibers and would fail the pre-registered merge condition.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fiber_trace_baseline.py`:

```python
def test_smoothing_survives_a_single_corrupted_voxel():
    """Fix A: one bad voxel must no longer end the walk."""
    response, dirs, valid = _straight_tube()
    dirs[20, 20, 20] = np.array([0.0, 1.0, 0.0])

    res = trace_fibers(
        response=response, seed_response=response, directions=dirs, valid=valid,
        params=TraceParams(seed_threshold=0.5, continue_threshold=0.25,
                           min_length=3.0, max_angle_deg=25.0, tangent_window=3),
    )
    assert len(res) == 1, f"expected one unbroken fiber, got {len(res)}"
    assert res.fibers[0].length > 25.0
    assert res.stop_counts.get("high_curvature", 0) == 0


def test_smoothing_still_stops_at_a_genuine_bend():
    """Fix A must not silently disable the curvature test.

    A sustained 90-degree turn is a real direction change, not quantization
    noise, and must still terminate the walk.
    """
    shape = (40, 40, 40)
    response = np.zeros(shape, dtype=float)
    dirs = np.zeros(shape + (3,), dtype=float)
    valid = np.zeros(shape, dtype=bool)

    # an L: along z for the first half, along y for the second
    for z in range(5, 20):
        response[z, 18:23, 18:23] = 1.0
        dirs[z, 18:23, 18:23] = np.array([1.0, 0.0, 0.0])
        valid[z, 18:23, 18:23] = True
    for y in range(20, 35):
        response[18:23, y, 18:23] = 1.0
        dirs[18:23, y, 18:23] = np.array([0.0, 1.0, 0.0])
        valid[18:23, y, 18:23] = True

    res = trace_fibers(
        response=response, seed_response=response, directions=dirs, valid=valid,
        params=TraceParams(seed_threshold=0.5, continue_threshold=0.25,
                           min_length=3.0, max_angle_deg=25.0, tangent_window=3),
    )
    assert res.stop_counts.get("high_curvature", 0) >= 1, (
        "a sustained 90-degree bend must still stop a walk")


def test_window_of_one_is_exactly_the_old_behaviour():
    response, dirs, valid = _straight_tube()
    dirs[20, 20, 20] = np.array([0.0, 1.0, 0.0])
    p = dict(seed_threshold=0.5, continue_threshold=0.25, min_length=3.0,
             max_angle_deg=25.0)

    old = trace_fibers(response=response, seed_response=response, directions=dirs,
                       valid=valid, params=TraceParams(tangent_window=1, **p))
    assert old.stop_counts.get("high_curvature", 0) >= 1
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run python -m pytest tests/test_fiber_trace_baseline.py -v
```

Expected: the three new tests and `test_defaults_preserve_published_behaviour` FAIL with `TypeError: __init__() got an unexpected keyword argument 'tangent_window'`.

- [ ] **Step 3: Add the parameter**

In `TraceParams`, after `max_angle_deg`:

```python
    tangent_window: int = 1
    """Compare each step against the mean of the last `tangent_window` directions
    rather than against the single previous step.

    `step` is sub-voxel while `_direction_at` is nearest-neighbour, so the
    orientation field is piecewise-constant and jumps at voxel boundaries. With a
    window of 1, a single noisy voxel ends a walk permanently -- measured as 46%
    of all stops on a real cube. A window spanning two voxels (`ceil(2 / step)`,
    i.e. 3 at the default step) averages that out while leaving `max_angle_deg`
    untouched, so a sustained bend still terminates the walk.

    Defaults to 1, which is exactly the published baseline's behaviour.
    """
```

- [ ] **Step 4: Implement the smoothing in `_walk`**

Replace the body of `_walk` between `prev = seed_dir.copy()` and the loop's `prev = d` assignment. The full changed section:

```python
    cos_limit = float(np.cos(np.deg2rad(params.max_angle_deg)))
    pts: list[np.ndarray] = []
    resp: list[float] = []
    p = start.astype(float).copy()
    prev = seed_dir.copy()
    window = max(1, int(params.tangent_window))
    recent: list[np.ndarray] = [seed_dir.copy()]
    reason = StopReason.MAX_LENGTH

    for _ in range(params.max_steps):
        # Reference tangent: sign-aligned mean of the recent directions. The
        # orientation field is defined only up to sign, so each entry is flipped
        # into the frame of the first before averaging -- otherwise two equally
        # valid opposing vectors cancel to near-zero.
        ref = np.zeros(3, dtype=float)
        for q in recent:
            ref += q if float(np.dot(q, recent[0])) >= 0.0 else -q
        n_ref = float(np.linalg.norm(ref))
        ref = prev if n_ref < 1e-8 else ref / n_ref

        d = _direction_at(dirs, valid, p, ref)
        if d is None:
            reason = StopReason.INVALID_DIRECTION
            break
        if float(np.dot(d, ref)) < cos_limit:
            reason = StopReason.HIGH_CURVATURE
            break

        nxt = p + d * params.step
        idx = tuple(int(round(v)) for v in nxt)
        if not all(0 <= idx[a] < response.shape[a] for a in range(3)):
            reason = StopReason.OUT_OF_BOUNDS
            break

        other = claimed[idx]
        if other != 0 and other != claim_id:
            reason = StopReason.COLLISION
            break

        r = _trilinear(response, nxt)
        if not np.isfinite(r):
            reason = StopReason.OUT_OF_BOUNDS
            break
        if r < params.continue_threshold:
            reason = StopReason.LOW_RESPONSE
            break

        pts.append(nxt.copy())
        resp.append(r)
        prev = d
        recent.append(d.copy())
        if len(recent) > window:
            recent.pop(0)
        p = nxt

    return pts, resp, reason
```

Two details that matter and are easy to get wrong:

1. **`_direction_at` is now passed `ref`, not `prev`.** It uses that argument only to resolve the field's sign ambiguity, and the smoothed reference is the more stable frame to resolve against.
2. **With `window == 1`, `recent` holds exactly one entry and `ref` equals the previous direction**, so behaviour is bit-identical to before. That is what `test_window_of_one_is_exactly_the_old_behaviour` checks.

- [ ] **Step 5: Run the tests**

```bash
uv run python -m pytest tests/test_fiber_trace_baseline.py -v
uv run python -m pytest tests/ -q -k "fiber and not vesselness_parity"
```

Expected: all baseline tests pass, and the pre-existing fiber suite passes. Run the full fiber suite **with the GPU visible** (no `CUDA_VISIBLE_DEVICES=""`) — the vesselness parity test fails under CUDA masking for unrelated reasons.

- [ ] **Step 6: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/trace.py tests/test_fiber_trace_baseline.py
git commit -m "$(cat <<'EOF'
feat(fibers): compare walk steps against a smoothed tangent

high_curvature was 46% of all stops. The cause is quantization, not curvature:
step is 0.7 voxels while direction lookup is nearest-neighbour, so the field is
piecewise-constant and one noisy voxel ended a walk permanently. Comparing
against a sign-aligned mean of the last k directions spans two voxels and
averages that out, leaving max_angle_deg untouched so a sustained bend still
terminates. Defaults to a window of 1, exactly the published behaviour.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Measure Fix A on the dev cubes

**Files:**
- Modify: `src/vesuvius_autoresearch/fibers/bench_cli.py` (add `--tangent-window`)
- Modify: `reports/fiber_tracer_improvement.md`

**Interfaces:**
- Consumes: `TraceParams.tangent_window` from Task 2.
- Produces: a `## Fix A` section in the report.

- [ ] **Step 1: Expose the parameter on the CLI**

In `cmd_trace`'s `TraceParams(...)` call, add `tangent_window=args.tangent_window`. In the argparse block alongside `--max-angle`, add:

```python
            p.add_argument("--tangent-window", type=int, default=1,
                           help="compare each step against the mean of the last N "
                                "directions (1 = published baseline behaviour)")
```

- [ ] **Step 2: Run the dev cubes at window 3**

```bash
uv run python -m vesuvius_autoresearch.fibers.bench_cli trace \
  --cube s1_00497_01497_03997_256 --tangent-window 3
uv run python -m vesuvius_autoresearch.fibers.bench_cli trace \
  --cube s1_00497_02497_02997_256 --tangent-window 3
```

Record ERL, ERLpen, coverage, splits, merges, instance count, and the stop-reason breakdown for each.

- [ ] **Step 3: Check the pre-registered failure condition before anything else**

Compare merges against the baseline for each cube. **If merges rose while ERLpen improved, that is a failure by the contract** — record it as such in the report and do not present it as a win. Do not tune to hide it.

- [ ] **Step 4: If window 3 does not clear the floor, try at most two more windows**

Permitted values: 2 and 5. Nothing else, and no other parameter may be changed in this task. Each run increments the configuration count. If none clears the floor, that is the result — proceed to Task 4 and report it honestly.

- [ ] **Step 5: Append the results**

Add to `reports/fiber_tracer_improvement.md`:

```markdown
## Fix A: tangent smoothing

| cube | window | ERL | ERLpen | cc ERLpen | coverage | splits | merges | n inst |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 1 (base) | 26.60 | 23.16 | 37.13 | 0.623 | 1872 | 38 | 669 |
| s1_00497_01497_03997 | 3 | | | 37.13 | | | | |
| s1_00497_02497_02997 | 1 (base) | | | 64.27 | | | | |
| s1_00497_02497_02997 | 3 | | | 64.27 | | | | |

Stop reasons after: <fill>

**Merge check (pre-registered):** merges went <baseline> -> <after> on cube 1 and
<baseline> -> <after> on cube 2. <PASS: merges did not rise / FAIL: ERLpen gain
accompanied by more merges>.

**Configurations tried so far: N**
```

Fill every cell with a measured value. Do not leave a placeholder in a committed report.

- [ ] **Step 6: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/bench_cli.py reports/fiber_tracer_improvement.md
git commit -m "$(cat <<'EOF'
bench(fibers): measure tangent smoothing on the dev cubes

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Fix B — seed non-maximum suppression

**Files:**
- Modify: `src/vesuvius_autoresearch/fibers/trace.py` (`TraceParams`, `trace_fibers`)
- Modify: `tests/test_fiber_trace_baseline.py`

**Interfaces:**
- Consumes: `TraceParams` from Task 2.
- Produces: `TraceParams.seed_nms_radius: float = 0.0`.

**Read this before implementing.** The seed loop already skips candidates lying in claimed territory (`if claimed[s] != 0: continue`), so duplicate seeds across one cross-section are *partly* handled already. The 455 collisions may therefore be mostly walks drifting into a *neighbouring* fiber rather than duplicate seeds on the same one. **Fix B is expected to be the smaller of the two fixes, and it may produce no gain at all.** Measure it; if the collision count barely moves, report that plainly rather than tuning until something shifts.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fiber_trace_baseline.py`:

```python
def test_nms_keeps_one_seed_per_cross_section():
    """A single fat fiber must not yield several parallel instances."""
    response, dirs, valid = _straight_tube(radius=3.0)
    res = trace_fibers(
        response=response, seed_response=response, directions=dirs, valid=valid,
        params=TraceParams(seed_threshold=0.5, continue_threshold=0.25,
                           min_length=5.0, seed_stride=1, claim_radius=0.5,
                           seed_nms_radius=2.0),
    )
    assert len(res) == 1, f"expected one instance, got {len(res)}"


def test_nms_does_not_merge_two_nearby_parallel_fibers():
    """Suppression must not swallow a genuinely separate neighbour."""
    shape = (40, 40, 40)
    response = np.zeros(shape, dtype=float)
    dirs = np.zeros(shape + (3,), dtype=float)
    valid = np.zeros(shape, dtype=bool)
    for cx in (17, 23):  # two fibers 6 voxels apart
        response[:, 20, cx] = 1.0
        dirs[:, 20, cx] = np.array([1.0, 0.0, 0.0])
        valid[:, 20, cx] = True

    res = trace_fibers(
        response=response, seed_response=response, directions=dirs, valid=valid,
        params=TraceParams(seed_threshold=0.5, continue_threshold=0.25,
                           min_length=5.0, seed_stride=1, claim_radius=0.5,
                           seed_nms_radius=2.0),
    )
    assert len(res) == 2, f"expected two fibers, got {len(res)}"


def test_nms_suppresses_perpendicular_only():
    """A candidate far along the tangent must still be accepted.

    Suppressing along the tangent would stop a long fiber being re-seeded past
    a gap, costing coverage.
    """
    from vesuvius_autoresearch.fibers.trace import _suppress_perpendicular

    accepted = np.array([20.0, 20.0, 20.0])
    tangent = np.array([1.0, 0.0, 0.0])

    near_perp = np.array([20.0, 21.0, 20.0])   # 1 voxel perpendicular
    far_along = np.array([35.0, 20.0, 20.0])   # 15 voxels along the tangent

    assert _suppress_perpendicular(near_perp, accepted, tangent, 2.0) is True
    assert _suppress_perpendicular(far_along, accepted, tangent, 2.0) is False
```

- [ ] **Step 2: Run them to verify they fail**

```bash
uv run python -m pytest tests/test_fiber_trace_baseline.py -v -k nms
```

Expected: FAIL — `seed_nms_radius` is not a parameter and `_suppress_perpendicular` does not exist.

- [ ] **Step 3: Add the parameter**

In `TraceParams`, after `seed_stride`:

```python
    seed_nms_radius: float = 0.0
    """Suppress seed candidates lying within this distance of an accepted seed,
    measured **perpendicular to that seed's tangent**. 0 disables it.

    Several seeds landing across one fiber's cross-section each start a walk;
    the first claims the fiber and the rest stop immediately with COLLISION.
    Suppression is perpendicular-only on purpose: distance *along* the tangent
    is unconstrained, so a long fiber can still be re-seeded beyond a gap.

    A radius of 2 comes from fiber geometry rather than tuning -- papyrus fibers
    are roughly 10-20 um at 7.91 um/voxel.
    """
```

- [ ] **Step 4: Implement the helper and wire it in**

Add near `_claim` in `trace.py`:

```python
def _suppress_perpendicular(
    candidate: np.ndarray, accepted: np.ndarray, tangent: np.ndarray, radius: float
) -> bool:
    """True if `candidate` lies within `radius` of `accepted`, perpendicular to `tangent`.

    Distance along the tangent is ignored, so a candidate far down the same fiber
    is not suppressed.
    """
    v = np.asarray(candidate, dtype=float) - np.asarray(accepted, dtype=float)
    t = np.asarray(tangent, dtype=float)
    n = float(np.linalg.norm(t))
    if n < 1e-8:
        return bool(np.linalg.norm(v) < radius)
    t = t / n
    perp = v - float(np.dot(v, t)) * t
    return bool(np.linalg.norm(perp) < radius)
```

In `trace_fibers`, immediately after `cand = cand[order][:: max(1, params.seed_stride)]`, add the suppression pass. It stamps a thin perpendicular disc into a boolean volume, which is O(n) rather than the O(n²) of comparing every candidate pair:

```python
    if params.seed_nms_radius > 0.0:
        r_nms = float(params.seed_nms_radius)
        rr = int(np.ceil(r_nms))
        suppressed = np.zeros(shape, dtype=bool)
        offsets = np.array(
            [
                (dz, dy, dx)
                for dz in range(-rr, rr + 1)
                for dy in range(-rr, rr + 1)
                for dx in range(-rr, rr + 1)
                if dz * dz + dy * dy + dx * dx <= r_nms * r_nms
            ],
            dtype=float,
        )
        kept = []
        for c in cand:
            cs = tuple(int(v) for v in c)
            if suppressed[cs]:
                continue
            kept.append(c)
            t = _direction_at(directions, valid, np.array(cs, dtype=float), None)
            if t is None:
                continue
            # stamp a disc perpendicular to the tangent: keep offsets whose
            # component along t is small, so the mark does not extend down the fiber
            along = offsets @ t
            disc = offsets[np.abs(along) <= 0.5]
            pts = np.rint(np.array(cs, dtype=float) + disc).astype(int)
            ok = np.ones(len(pts), dtype=bool)
            for a in range(3):
                ok &= (pts[:, a] >= 0) & (pts[:, a] < shape[a])
            pts = pts[ok]
            if len(pts):
                suppressed[pts[:, 0], pts[:, 1], pts[:, 2]] = True
        cand = np.array(kept) if kept else np.zeros((0, 3), dtype=int)
        if len(cand) == 0:
            return TraceResult(fibers=[], shape=shape, stop_counts={}, n_seeds_tried=0)
```

- [ ] **Step 5: Run the tests**

```bash
uv run python -m pytest tests/test_fiber_trace_baseline.py -v
uv run python -m pytest tests/ -q -k "fiber and not vesselness_parity"
```

Expected: all pass, including the Task 1 and Task 2 tests.

- [ ] **Step 6: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/trace.py tests/test_fiber_trace_baseline.py
git commit -m "$(cat <<'EOF'
feat(fibers): seed non-maximum suppression perpendicular to the tangent

Several seeds across one fiber's cross-section each start a walk; the first
claims the fiber and the rest stop with COLLISION (28% of stops). Suppression
is perpendicular-only so a long fiber can still be re-seeded past a gap.
Radius 2 comes from fiber geometry, not tuning. Defaults to disabled.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Measure Fix B, and both together

**Files:**
- Modify: `src/vesuvius_autoresearch/fibers/bench_cli.py` (add `--seed-nms-radius`)
- Modify: `reports/fiber_tracer_improvement.md`

- [ ] **Step 1: Expose the parameter**

Add `seed_nms_radius=args.seed_nms_radius` to `cmd_trace`'s `TraceParams(...)`, and:

```python
            p.add_argument("--seed-nms-radius", type=float, default=0.0,
                           help="suppress seeds within this perpendicular distance "
                                "of an accepted seed (0 = disabled)")
```

- [ ] **Step 2: Run Fix B alone, then both, on the dev cubes**

```bash
for CUBE in s1_00497_01497_03997_256 s1_00497_02497_02997_256; do
  uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube $CUBE --seed-nms-radius 2.0
  uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube $CUBE \
    --tangent-window <best from Task 3> --seed-nms-radius 2.0
done
```

Use the window Task 3 selected. Record the collision count specifically — that is what Fix B is supposed to move.

- [ ] **Step 3: Check the pre-registered failure condition**

For every row, compare merges against that cube's baseline. An ERLpen gain with more merges is a failure and must be recorded as one.

- [ ] **Step 4: Append the results, including a negative if that is the outcome**

```markdown
## Fix B: seed NMS, and both fixes together

| cube | window | nms | ERL | ERLpen | cc ERLpen | coverage | splits | merges | collisions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

**Did Fix B move collisions?** <baseline collisions> -> <after>. <If the change is
small, say so plainly: the seed loop already skipped claimed candidates, so most
collisions were walks drifting into neighbouring fibers rather than duplicate seeds.>

**Merge check (pre-registered):** <PASS / FAIL per cube>

**Configurations tried so far: N**
```

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/bench_cli.py reports/fiber_tracer_improvement.md
git commit -m "$(cat <<'EOF'
bench(fibers): measure seed NMS and the combined configuration

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: The held-out run, once

This task is the moment the protocol exists for. **Read the whole task before running anything.**

**Files:**
- Modify: `reports/fiber_tracer_improvement.md`
- Modify: `docs/FIBER_TRACING.md`

- [ ] **Step 1: Freeze the configuration**

Write the single chosen configuration into the report *before* running: the tangent window, the NMS radius, and every other tracer parameter. **After this point no parameter may change.** If a held-out cube disappoints, that is the result.

- [ ] **Step 2: Run all six cubes once**

```bash
for CUBE in s1_00497_01497_03997_256 s1_00497_02497_02997_256 \
            s1_00997_02497_02997_256 s1_08997_02997_02497_256 \
            s1_10997_02997_02997_256 s5_03997_01497_03997_256; do
  uv run python -m vesuvius_autoresearch.fibers.bench_cli trace --cube $CUBE \
    --tangent-window <frozen> --seed-nms-radius <frozen>
done
```

- [ ] **Step 3: Write the final table**

Every cube, every metric, against each cube's own floor:

```markdown
## Final result (frozen configuration, held-out cubes scored once)

Configuration: tangent_window=<N>, seed_nms_radius=<R>, all other parameters at
the published defaults. Configurations tried in total: <N>.

| cube | role | ERL | cc ERL | ERLpen | cc ERLpen | beat floor? | coverage | splits | merges |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | dev | | 197.1 | | 37.13 | | | | |
| s1_00497_02497_02997 | dev | | 207.5 | | 64.27 | | | | |
| s1_00997_02497_02997 | held out | | 195.8 | | 56.5 | | | | |
| s1_08997_02997_02497 | held out | | 186.5 | | 106.1 | | | | |
| s1_10997_02997_02997 | held out | | 194.1 | | 57.7 | | | | |
| s5_03997_01497_03997 | never touched | | 182.2 | | 51.1 | | | | |
```

- [ ] **Step 4: State the verdict plainly, in one of exactly these three forms**

- **Cleared on ERLpen, not on raw ERL:** say so explicitly, quote both, and state that the benchmark was *not* beaten outright. Include the pre-registered reasoning about raw ERL rewarding merges, and note it was recorded before the runs.
- **Cleared on both:** state it, and note that raw ERL was cleared without a rise in merges.
- **Did not clear:** publish it in the same style as the project's existing negatives, with the numbers and the likely reason.

Also report whether the gain held on the held-out cubes, and specifically on the never-touched cross-scroll cube. **A gain that appears on dev and vanishes on held-out must be reported as such, not re-tuned.**

- [ ] **Step 5: Update the tracer documentation**

In `docs/FIBER_TRACING.md`, replace the "Current standing" paragraph's numbers with the new ones. Keep the existing structure and the note that the tracer is the benchmark's entrant rather than part of it. If the tracer now clears the ERLpen floor, say precisely that — cleared the merge-penalized floor, and whether raw ERL was cleared — never "beats connected components" unqualified.

- [ ] **Step 6: Commit**

```bash
git add reports/fiber_tracer_improvement.md docs/FIBER_TRACING.md
git commit -m "$(cat <<'EOF'
report(fibers): final result against the pre-registered contract

Held-out cubes scored once at a frozen configuration; the cross-scroll cube
informed no decision. Both metrics reported for every cube.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage.** Pre-registered contract → Global Constraints, enforced in Tasks 3 Step 3, 5 Step 3, 6 Step 4. Anti-tuning protocol → cube roles in Global Constraints, held-out cubes touched only in Task 6, configuration counting in Tasks 3/5/6. Fix A → Task 2, measured in Task 3. Fix B → Task 4, measured in Task 5. Baseline reproducibility → Task 1. Testing requirements → Tasks 1, 2, 4 (corrupted voxel, genuine bend, two parallel fibers, one cross-section, perpendicular-only). All six success criteria are covered: (1) Task 3/5, (2) Task 6 Step 2, (3) Task 6 Steps 2 and 4, (4) every report table, (5) configuration counts, (6) Task 6 Step 4's third form.

**Type consistency.** `tangent_window: int` and `seed_nms_radius: float` are named identically in Tasks 2, 3, 4, 5, 6 and in both CLI flags (`--tangent-window`, `--seed-nms-radius`). `_suppress_perpendicular(candidate, accepted, tangent, radius) -> bool` is defined in Task 4 Step 4 and called with that signature in Task 4 Step 1's test. `_walk`'s signature is unchanged, so no caller needs updating.

**One known risk.** `_suppress_perpendicular` is unit-tested directly but the production path uses the stamped-disc volume rather than calling it per pair, for O(n) rather than O(n²) cost. The two implement the same rule, and the disc's `|offset · t| <= 0.5` band is the perpendicular-only constraint. If Task 4's cross-section and parallel-fibers tests pass, both paths agree on the cases that matter; if they diverge later, the volume path is the one in use.
