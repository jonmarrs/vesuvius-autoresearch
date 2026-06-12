# GPU-Fibers Standalone Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vendor the validated GPU fiber/ridge/vesselness detection into `src/vesuvius_autoresearch/fibers/` (package + CLI + tests), and repoint `vesuvius_loader.py`'s ridge path to it — fixing the confirmed silent zero-ridges bug.

**Architecture:** Copy only the fiber-detection functions from the `sprint033-fibers-gpu` branch's `tools.py` into a focused package via a deterministic AST extraction, expose a public API + CLI, port the parity tests, then swap the loader off the broken clone `tools.py`.

**Tech Stack:** Python 3.10, NumPy, SciPy ndimage, optional CuPy (`cupyx.scipy.ndimage`), pytest. Interpreter: `.venv` via `PYTHONPATH=. .venv/bin/python`.

**Context for the implementer:**
- The validated source lives in the sibling villa clone: `~/openclaw-workspace/Neo-VM/projects/villa`, branch `sprint033-fibers-gpu`, file `foundation/datasets/fibers-dataset/tools.py`.
- Functions to vendor (11): `get_backend`, `divide_nonzero`, `normalize`, `hessian`, `compute_eigenvalues_3x3_batch`, `detect_ridges`, `detect_vesselness`, `_smoothed_global_range`, `_detect_tiled`, `detect_ridges_tiled`, `detect_vesselness_tiled`. (The others — `nlm`, `nms_3d`, `ms_3d`, `denoise_3d`, `adjust_contrast`, `proximity_boolean_filter`, `detect_edges` — are dropped; verified the kept ones don't reference them.)
- Tensor convention: volumes are `[Z, H, W]` numpy or cupy arrays.
- **The loop runs `train.py` subprocesses and imports the loader.** Task 3 edits the loader — pause the loop first (`pgrep -f "python run_autoresearch_loop.py" | xargs -r kill -9; pgrep -f "scripts/training/train.py" | xargs -r kill -9`), verify, restart with `bash start.sh`.
- Pre-commit now excludes loop state files, so doc/code commits land cleanly while the loop runs.

## File Structure

- `src/vesuvius_autoresearch/fibers/__init__.py` (create) — public API re-export.
- `src/vesuvius_autoresearch/fibers/detection.py` (create) — vendored detection functions.
- `src/vesuvius_autoresearch/fibers/cli.py` (create) — command-line runner.
- `tests/test_fibers.py` (create) — eigensolver + parity tests.
- `tests/test_fibers_cli.py` (create) — CLI round-trip test.
- `src/vesuvius_autoresearch/core/vesuvius_loader.py` (modify) — repoint ridge path.
- `docs/FIBER_DETECTION.md` (create) + `README.md` (modify) — docs.

---

## Task 1: Vendor the detection package

**Files:**
- Create: `src/vesuvius_autoresearch/fibers/__init__.py`, `src/vesuvius_autoresearch/fibers/detection.py`
- Test: `tests/test_fibers.py`

- [ ] **Step 1: Write the failing tests** (`tests/test_fibers.py`):

```python
import numpy as np
import pytest

from vesuvius_autoresearch.fibers import (
    compute_eigenvalues_3x3_batch,
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
)

try:
    import cupy as cp
    HAS_CUPY = True
except ImportError:
    HAS_CUPY = False


def test_eigensolver_matches_numpy():
    rng = np.random.default_rng(0)
    A = rng.random((50, 3, 3)).astype(np.float64)
    A = (A + A.swapaxes(-1, -2)) / 2  # symmetric
    ours = np.asarray(compute_eigenvalues_3x3_batch(A))
    ref = np.linalg.eigvalsh(A)
    np.testing.assert_allclose(np.sort(ours, -1), np.sort(ref, -1), rtol=1e-4, atol=1e-6)


def test_vesselness_nonzero_and_finite():
    rng = np.random.default_rng(0)
    vol = rng.random((24, 32, 32)).astype(np.float32)
    out = detect_vesselness(vol)
    assert out.shape == vol.shape
    assert np.isfinite(out).all()
    assert float(np.abs(out).sum()) > 0.0


def test_tiled_matches_dense_vesselness():
    rng = np.random.default_rng(42)
    vol = rng.random((64, 64, 64)).astype(np.float32)
    dense = detect_vesselness(vol.copy())
    tiled = detect_vesselness_tiled(vol.copy(), block_size=32, halo=16)
    np.testing.assert_allclose(dense, tiled, rtol=1e-3, atol=1e-4)


def test_tiled_matches_dense_ridges():
    rng = np.random.default_rng(7)
    vol = rng.random((64, 64, 64)).astype(np.float32)
    dense = detect_ridges(vol.copy())
    tiled = detect_ridges_tiled(vol.copy(), block_size=32, halo=16)
    np.testing.assert_allclose(dense, tiled, rtol=1e-3, atol=1e-4)


@pytest.mark.skipif(not HAS_CUPY, reason="CuPy not available")
def test_cpu_gpu_vesselness_parity():
    rng = np.random.default_rng(42)
    vol = rng.random((32, 32, 32)).astype(np.float32)
    res_np = detect_vesselness(vol)
    res_cp = detect_vesselness(cp.asarray(vol))
    np.testing.assert_allclose(res_np, cp.asnumpy(res_cp), rtol=1e-3, atol=1e-4)
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_fibers.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'vesuvius_autoresearch.fibers'`.

- [ ] **Step 3: Create the package via deterministic extraction**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p src/vesuvius_autoresearch/fibers
git -C ../villa show sprint033-fibers-gpu:foundation/datasets/fibers-dataset/tools.py > /tmp/validated_tools.py
.venv/bin/python - <<'PYEOF'
import ast
src = open("/tmp/validated_tools.py").read()
tree = ast.parse(src)
keep = ["get_backend", "divide_nonzero", "normalize", "hessian",
        "compute_eigenvalues_3x3_batch", "detect_ridges", "detect_vesselness",
        "_smoothed_global_range", "_detect_tiled", "detect_ridges_tiled",
        "detect_vesselness_tiled"]
by_name = {n.name: ast.get_source_segment(src, n) for n in tree.body
           if isinstance(n, ast.FunctionDef)}
missing = [k for k in keep if k not in by_name]
assert not missing, f"missing functions in source: {missing}"
header = '''"""GPU-native fiber / ridge / vesselness detection for scroll CT.

Vendored from the validated `sprint033-fibers-gpu` branch (proposed as
ScrollPrize/villa PR #1033). The closed-form symmetric-3x3 eigensolver
(`compute_eigenvalues_3x3_batch`) avoids the cuSolver `eigvalsh` failure on
large Hessian batches; `get_backend` dispatches per-array so the same functions
run on NumPy (CPU) or CuPy (GPU). Tiled variants process volumes larger than
VRAM with a halo, normalizing each block against the global smoothed range.
"""

import math

import numpy as np
from scipy import ndimage

try:
    import cupy as cp
    from cupyx.scipy import ndimage as cupy_ndimage

    HAS_CUPY = True
except ImportError:
    HAS_CUPY = False
'''
body = "\n\n\n".join(by_name[k] for k in keep)
open("src/vesuvius_autoresearch/fibers/detection.py", "w").write(header + "\n\n" + body + "\n")
print("wrote detection.py with", len(keep), "functions")
PYEOF
cat > src/vesuvius_autoresearch/fibers/__init__.py <<'PYEOF'
"""GPU-native fiber / ridge / vesselness detection (vendored, villa PR #1033)."""

from vesuvius_autoresearch.fibers.detection import (
    compute_eigenvalues_3x3_batch,
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
)

__all__ = [
    "compute_eigenvalues_3x3_batch",
    "detect_ridges",
    "detect_vesselness",
    "detect_ridges_tiled",
    "detect_vesselness_tiled",
]
PYEOF
echo "=== verify no dropped-helper references leaked in ==="
grep -nE "nlm|nms_3d|ms_3d|denoise_3d|adjust_contrast|proximity_boolean|detect_edges|tqdm|skimage" src/vesuvius_autoresearch/fibers/detection.py || echo "clean"
```
Expected: "wrote detection.py with 11 functions" and "clean".

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_fibers.py -q`
Expected: PASS (4 CPU tests; the cupy parity test passes if CuPy present, else skipped).

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/ tests/test_fibers.py
git commit -m "feat(fibers): vendor validated GPU fiber/ridge/vesselness detection (villa PR #1033)"
```

---

## Task 2: CLI runner

**Files:**
- Create: `src/vesuvius_autoresearch/fibers/cli.py`
- Test: `tests/test_fibers_cli.py`

- [ ] **Step 1: Write the failing test** (`tests/test_fibers_cli.py`):

```python
import subprocess
import sys

import numpy as np


def test_cli_vesselness_roundtrip(tmp_path):
    vol = np.random.default_rng(0).random((16, 32, 32)).astype(np.float32)
    inp = tmp_path / "vol.npy"
    out = tmp_path / "out.npy"
    np.save(inp, vol)
    r = subprocess.run(
        [sys.executable, "-m", "vesuvius_autoresearch.fibers.cli",
         "--input", str(inp), "--filter", "vesselness", "--output", str(out)],
        capture_output=True, text=True, cwd=".",
    )
    assert r.returncode == 0, r.stderr
    res = np.load(out)
    assert res.shape == vol.shape
    assert np.isfinite(res).all()
    assert float(np.abs(res).sum()) > 0.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_fibers_cli.py -q`
Expected: FAIL — `No module named vesuvius_autoresearch.fibers.cli` (returncode non-zero).

- [ ] **Step 3: Write the CLI** (`src/vesuvius_autoresearch/fibers/cli.py`):

```python
"""Run GPU fiber/ridge/vesselness detection on a .npy CT volume.

Usage:
    python -m vesuvius_autoresearch.fibers.cli --input vol.npy \
        --filter vesselness --output out.npy [--tiled --block-size 128 --halo 16] \
        [--preview out.png]
"""

import argparse
import time

import numpy as np

from vesuvius_autoresearch.fibers import (
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="GPU fiber/ridge/vesselness detection.")
    ap.add_argument("--input", required=True, help="input .npy CT volume [Z,H,W]")
    ap.add_argument("--filter", choices=["vesselness", "ridges"], default="vesselness")
    ap.add_argument("--output", required=True, help="output .npy path")
    ap.add_argument("--tiled", action="store_true", help="tiled/halo execution for large volumes")
    ap.add_argument("--block-size", type=int, default=128)
    ap.add_argument("--halo", type=int, default=16)
    ap.add_argument("--preview", help="optional z-mean preview PNG")
    args = ap.parse_args()

    vol = np.load(args.input).astype(np.float32)
    backend = "cpu"
    arr = vol
    try:
        import cupy as cp

        arr = cp.asarray(vol)
        backend = "gpu"
    except ImportError:
        pass

    if args.filter == "vesselness":
        fn = detect_vesselness_tiled if args.tiled else detect_vesselness
    else:
        fn = detect_ridges_tiled if args.tiled else detect_ridges
    kwargs = {"block_size": args.block_size, "halo": args.halo} if args.tiled else {}

    t0 = time.time()
    out = fn(arr, **kwargs)
    try:
        import cupy as cp

        if isinstance(out, cp.ndarray):
            out = cp.asnumpy(out)
    except ImportError:
        pass
    out = np.asarray(out, dtype=np.float32)
    dt = time.time() - t0

    np.save(args.output, out)
    print(f"{args.filter} backend={backend} tiled={args.tiled} shape={out.shape} "
          f"time={dt:.2f}s -> {args.output}")

    if args.preview:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.imsave(args.preview, out.mean(axis=0), cmap="magma")
        print(f"preview -> {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_fibers_cli.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/fibers/cli.py tests/test_fibers_cli.py
git commit -m "feat(fibers): CLI runner for fiber/ridge/vesselness detection"
```

---

## Task 3: Repoint the loader ridge path (LOOP-CRITICAL)

**Files:**
- Modify: `src/vesuvius_autoresearch/core/vesuvius_loader.py` (line 19 import; ridge calls at ~180, ~192, ~630, ~639)

- [ ] **Step 1: Pause the loop**

```bash
pgrep -f "python run_autoresearch_loop.py" | xargs -r kill -9
pgrep -f "scripts/training/train.py" | xargs -r kill -9
sleep 2; nvidia-smi --query-gpu=memory.used --format=csv,noheader   # expect ~6 MiB
```

- [ ] **Step 2: Swap the import** — replace line 19 `import tools as fiber_tools` with:

```python
from vesuvius_autoresearch.fibers import detect_ridges
```

- [ ] **Step 3: Replace the four call sites** — change each `fiber_tools.detect_ridges(` to `detect_ridges(` (four occurrences, the GPU and CPU branches in both `__getitem__` ridge blocks). Run this to do it and confirm zero remaining references:

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
sed -i 's/fiber_tools\.detect_ridges(/detect_ridges(/g' src/vesuvius_autoresearch/core/vesuvius_loader.py
grep -c "fiber_tools\.detect_ridges" src/vesuvius_autoresearch/core/vesuvius_loader.py   # expect 0
grep -c "import tools as fiber_tools" src/vesuvius_autoresearch/core/vesuvius_loader.py  # expect 0
```
Expected: both 0. (The two remaining `fiber_tools` mentions at ~171/~255 are comments; leave them or update the prose — they don't affect behavior.)

- [ ] **Step 4: Verify the ridge channel is now non-zero (the bug fix)**

```bash
PYTHONPATH=. .venv/bin/python - <<'PYEOF'
import numpy as np, torch
from vesuvius_autoresearch.core.vesuvius_loader import FastVesuviusVolume
v = FastVesuviusVolume("local_data/PHercParis2Fr47/surface_volume.zarr", use_ridges=True, ridge_sigma=2.0)
patch = v[10:26, 2000:2064, 2000:2064]   # [2, Z, H, W]: ct + ridge
ridge = patch[1].numpy()
print("ridge channel: shape", ridge.shape, "abs-sum", float(np.abs(ridge).sum()), "finite", bool(np.isfinite(ridge).all()))
assert np.isfinite(ridge).all() and np.abs(ridge).sum() > 0.0, "ridge channel still zero/non-finite!"
print("OK: ridge channel is non-zero and finite")
PYEOF
PYTHONPATH=. .venv/bin/python scripts/training/train.py --smoke 2>&1 | tail -2
```
Expected: "OK: ridge channel is non-zero and finite"; `PREFLIGHT OK`. (If the exact slice has no data, pick another in-bounds region; the volume is `(33, 14830, 9506)`.)

- [ ] **Step 5: End-to-end short run (no NaN, no zero-ridge warning)**

```bash
.venv/bin/python -c "import json;c=json.load(open('config.json'));c['use_ridges']=True;c['time_budget']=45;json.dump(c,open('/tmp/cfg_ridge.json','w'))"
PYTHONPATH=. .venv/bin/python scripts/training/train.py --test --config /tmp/cfg_ridge.json 2>&1 | grep -iE "Instability|NaN|Traceback|using zero ridges|val_bpb \(Off|RESULT" | tail -4
rm -f /tmp/cfg_ridge.json
```
Expected: a `val_bpb (Official)` + `[RESULT]` line; NO `Instability`/`NaN`/`Traceback`/`using zero ridges`.

- [ ] **Step 6: Commit (loop still paused)**

```bash
git add src/vesuvius_autoresearch/core/vesuvius_loader.py
git commit -m "fix(loader): use vendored fiber detection; fixes silent zero-ridges bug

The ridge feature channel was all-zeros whenever use_ridges=true: the broken
upstream clone tools.py failed on both the GPU path (cuSolver eigvalsh) and the
CPU path (numpy-under-cupy-global-backend TypeError), so the loader substituted
zeros. Repointed to the vendored vesuvius_autoresearch.fibers.detect_ridges
(closed-form eigensolver + get_backend dispatch), which works on both backends."
```

- [ ] **Step 7: Restart the loop and confirm clean start**

```bash
bash start.sh; sleep 10
grep -c ModuleNotFoundError autoresearch.out   # expect 0
tail -3 autoresearch.out
```
Expected: 0 import crashes; output shows `Applying …` / `Running … training`.

---

## Task 4: Documentation

**Files:**
- Create: `docs/FIBER_DETECTION.md`
- Modify: `README.md`

- [ ] **Step 1: Write `docs/FIBER_DETECTION.md`** covering: the cuSolver `eigvalsh` failure the closed-form eigensolver solves; the validated numbers (eigensolver float64 parity 3.1e-10; dense 14–94× over NumPy at 64³–256³; tiled 512³ in ~3–5 s at ~1 GB VRAM — link `reports/fibers_gpu_validation_2026-06.md`); the CLI usage; and the API example below:

```python
import numpy as np
from vesuvius_autoresearch.fibers import detect_vesselness, detect_vesselness_tiled

vol = np.random.rand(128, 256, 256).astype(np.float32)   # [Z,H,W] CT
ves = detect_vesselness(vol)                              # dense (fits in memory)
big = np.random.rand(512, 512, 512).astype(np.float32)
ves_big = detect_vesselness_tiled(big, block_size=128, halo=16)   # tiled
```

```bash
python -m vesuvius_autoresearch.fibers.cli --input vol.npy --filter vesselness --output ves.npy --preview ves.png
```

- [ ] **Step 2: Add a README subsection** under "Design choices" / near the scroll-augmentations subsection:

```markdown
## GPU fiber detection

`vesuvius_autoresearch.fibers` is a standalone GPU fiber/ridge/vesselness
detector with a closed-form symmetric-3×3 eigensolver that avoids the cuSolver
`eigvalsh` failure on large Hessian batches (14–94× over NumPy; 512³ tiled in
~1 GB VRAM). See **[docs/FIBER_DETECTION.md](docs/FIBER_DETECTION.md)**.
```

- [ ] **Step 3: Commit**

```bash
git add docs/FIBER_DETECTION.md README.md
git commit -m "docs(fibers): fiber-detection library reference + README pointer"
```

---

## Verification (whole feature)

- [ ] `PYTHONPATH=. .venv/bin/python -m pytest tests/test_fibers.py tests/test_fibers_cli.py -q` → all pass.
- [ ] Loader: the ridge-channel check prints non-zero/finite; `train.py --smoke` prints `PREFLIGHT OK`; the `--test` run shows no NaN and no "using zero ridges" warning.
- [ ] Loop restarted, `grep -c ModuleNotFoundError autoresearch.out` is 0, a cycle running.
- [ ] Diff limited to: `src/vesuvius_autoresearch/fibers/`, `src/vesuvius_autoresearch/core/vesuvius_loader.py`, `tests/test_fibers.py`, `tests/test_fibers_cli.py`, `docs/FIBER_DETECTION.md`, `README.md`.
- [ ] `git fetch origin && git push origin main`.
