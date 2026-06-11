# Scroll-Augmentation Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scroll_augmentations.py` the single, tested, documented library for scroll-physics augmentations and have `train.py` use it, fixing the bug where 5 of 9 sampled augmentation families are silent no-ops in real training.

**Architecture:** Keep the existing pure augmentation functions in `scroll_augmentations.py`. Add an explicit-probabilities API (`ScrollAugProbs` dataclass + `apply_scroll_augmentations`) decoupled from `ExperimentConfig`, plus a thin config-adapter `apply_scroll_specific_3d_augmentations(...config)` that the loop uses. Delete `train.py`'s inline duplicate (which only applied 4 of 9) and import the library instead.

**Tech Stack:** Python 3.10, PyTorch (`torch`, `torch.nn.functional`), pytest. Project interpreter: `.venv` via `uv run` / `PYTHONPATH=. .venv/bin/python`.

**Context notes for the implementer:**
- The 9 families: `decohesion`, `warping`, `squeeze`, `z_dropout`, `intensity_drift`, `sheet_compression`, `thick_slice`, `rician_noise`, `blank_rectangles`. The loop config carries `aug_scroll_<family>_p` for each.
- `scroll_augmentations.py` is a **top-level module at repo root** — import as `from scroll_augmentations import ...` (repo root is on `PYTHONPATH=.`).
- Tensor shapes: `x` is `[B,C,Z,H,W]`, `target_ink` is `[B,1,H,W]`, `target_fiber` is `[B,1,1,H,W]`.
- **The autoresearch loop runs `train.py` as subprocesses.** Task 4 edits `train.py` — pause the loop first (`pgrep -f "python run_autoresearch_loop.py" | xargs -r kill -9; pgrep -f "scripts/training/train.py" | xargs -r kill -9`), verify, then restart with `bash start.sh`.
- Pre-commit hooks reformat with ruff and may conflict with loop-written files (config.json). Commit code files with the loop paused, or stage only your files.

---

## File Structure

- `scroll_augmentations.py` (modify) — add `ScrollAugProbs` dataclass, `apply_scroll_augmentations(x, ink, fiber, probs)` explicit API, `__all__`; rewrite `apply_scroll_specific_3d_augmentations(x, ink, fiber, config)` as a config-adapter. Existing augmentation functions unchanged.
- `tests/test_scroll_aug_library.py` (create) — tests the explicit API (reusability, decoupled from config).
- `tests/test_scroll_specific_augmentations.py` (modify) — repoint import to the library; add the no-op-bug regression guard.
- `scripts/training/train.py` (modify) — delete inline `_warp_2d_tensor` (705), `_scroll_squeeze_warp` (718), `apply_scroll_specific_3d_augmentations` (751); add `from scroll_augmentations import apply_scroll_specific_3d_augmentations`.
- `scripts/visualize_scroll_augmentations.py` (modify) — ensure it renders all 9 families to `reports/augmentation_demos/`; fix stale docstring.
- `docs/SCROLL_AUGMENTATIONS.md` (create) — library documentation.

---

## Task 1: Explicit-probabilities API (`ScrollAugProbs` + `apply_scroll_augmentations`)

**Files:**
- Modify: `scroll_augmentations.py` (append near the existing `apply_scroll_specific_3d_augmentations`)
- Test: `tests/test_scroll_aug_library.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scroll_aug_library.py
import torch

from scroll_augmentations import ScrollAugProbs, apply_scroll_augmentations


def _sample():
    x = torch.linspace(0, 1, 2 * 1 * 8 * 16 * 16).reshape(2, 1, 8, 16, 16)
    ink = torch.zeros((2, 1, 16, 16)); ink[:, :, 4:12, 4:12] = 1.0
    fiber = torch.zeros((2, 1, 1, 16, 16)); fiber[:, :, :, :, 7:9] = 1.0
    return x, ink, fiber


def test_all_probs_one_changes_input_and_preserves_shapes():
    torch.manual_seed(0)
    x, ink, fiber = _sample()
    probs = ScrollAugProbs(
        decohesion=1.0, warping=1.0, squeeze=1.0, z_dropout=1.0,
        intensity_drift=1.0, sheet_compression=1.0, thick_slice=1.0,
        rician_noise=1.0, blank_rectangles=1.0,
    )
    x2, ink2, fiber2 = apply_scroll_augmentations(x.clone(), ink.clone(), fiber.clone(), probs)
    assert x2.shape == x.shape and ink2.shape == ink.shape and fiber2.shape == fiber.shape
    assert torch.isfinite(x2).all()
    assert not torch.equal(x2, x)  # something actually happened
    assert 0.0 <= float(ink2.min()) and float(ink2.max()) <= 1.0


def test_all_probs_zero_is_identity():
    torch.manual_seed(0)
    x, ink, fiber = _sample()
    x2, ink2, fiber2 = apply_scroll_augmentations(x.clone(), ink.clone(), fiber.clone(), ScrollAugProbs())
    assert torch.equal(x2, x) and torch.equal(ink2, ink) and torch.equal(fiber2, fiber)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_scroll_aug_library.py -q`
Expected: FAIL — `ImportError: cannot import name 'ScrollAugProbs'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scroll_augmentations.py` (after the existing augmentation functions, before/around the existing `apply_scroll_specific_3d_augmentations`):

```python
from dataclasses import dataclass


@dataclass
class ScrollAugProbs:
    """Per-augmentation application probabilities (each in [0, 1]).

    Decoupled from the autoresearch ExperimentConfig so external callers can
    use this library directly.
    """
    decohesion: float = 0.0
    warping: float = 0.0
    squeeze: float = 0.0
    z_dropout: float = 0.0
    intensity_drift: float = 0.0
    sheet_compression: float = 0.0
    thick_slice: float = 0.0
    rician_noise: float = 0.0
    blank_rectangles: float = 0.0


def _fires(p: float, device) -> bool:
    return p > 0.0 and torch.rand((), device=device).item() < p


def apply_scroll_augmentations(x, target_ink, target_fiber, probs: ScrollAugProbs):
    """Apply each scroll augmentation independently with its probability.

    x: [B,C,Z,H,W]; target_ink: [B,1,H,W]; target_fiber: [B,1,1,H,W].
    Geometric augmentations (warping, squeeze, thick_slice) also transform the
    targets. Returns the (possibly) modified tensors with labels clamped to
    [0, 1].
    """
    dev = x.device
    if _fires(probs.sheet_compression, dev):
        x = scroll_sheet_compression(x)
    if _fires(probs.thick_slice, dev):
        x, target_ink, target_fiber = scroll_thick_slice(x, target_ink, target_fiber)
    if _fires(probs.decohesion, dev):
        alpha = torch.empty((), device=dev, dtype=x.dtype).uniform_(0.15, 0.45).item()
        x = scroll_decohesion(x, alpha=alpha)
    if _fires(probs.warping, dev):
        x, target_ink, target_fiber = scroll_warping(x, target_ink, target_fiber)
    if _fires(probs.squeeze, dev):
        x, target_ink, target_fiber = scroll_squeeze(x, target_ink, target_fiber)
    if _fires(probs.z_dropout, dev):
        x = scroll_z_dropout(x)
    if _fires(probs.intensity_drift, dev):
        x = scroll_intensity_drift(x)
    if _fires(probs.rician_noise, dev):
        x = scroll_rician_noise(x)
    if _fires(probs.blank_rectangles, dev):
        x = scroll_blank_rectangles(x)
    return x, target_ink.clamp(0, 1), target_fiber.clamp(0, 1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_scroll_aug_library.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add scroll_augmentations.py tests/test_scroll_aug_library.py
git commit -m "feat(augmentations): explicit-probability API (ScrollAugProbs) decoupled from config"
```

---

## Task 2: Config-adapter + no-op-bug regression guard

**Files:**
- Modify: `scroll_augmentations.py` (rewrite the existing `apply_scroll_specific_3d_augmentations`)
- Test: `tests/test_scroll_specific_augmentations.py`

- [ ] **Step 1: Write the failing test (regression guard)**

Append to `tests/test_scroll_specific_augmentations.py`, and change its top import from
`from train import ExperimentConfig, apply_scroll_specific_3d_augmentations` to:
`from train import ExperimentConfig` and `from scroll_augmentations import apply_scroll_specific_3d_augmentations`.

```python
def test_adapter_exercises_all_nine_families(monkeypatch):
    import scroll_augmentations as sa

    called = set()

    def spy(name, fn):
        def wrapped(*a, **k):
            called.add(name)
            return fn(*a, **k)
        return wrapped

    for name in [
        "scroll_decohesion", "scroll_warping", "scroll_squeeze", "scroll_z_dropout",
        "scroll_intensity_drift", "scroll_sheet_compression", "scroll_thick_slice",
        "scroll_rician_noise", "scroll_blank_rectangles",
    ]:
        monkeypatch.setattr(sa, name, spy(name, getattr(sa, name)))

    cfg = ExperimentConfig(
        aug_scroll_decohesion_p=1.0, aug_scroll_warping_p=1.0, aug_scroll_squeeze_p=1.0,
        aug_scroll_z_dropout_p=1.0, aug_scroll_intensity_drift_p=1.0,
        aug_scroll_sheet_compression_p=1.0, aug_scroll_thick_slice_p=1.0,
        aug_scroll_rician_noise_p=1.0, aug_scroll_blank_rectangles_p=1.0,
    )
    x = torch.rand(2, 1, 8, 16, 16)
    ink = torch.zeros((2, 1, 16, 16)); ink[:, :, 4:12, 4:12] = 1.0
    fiber = torch.zeros((2, 1, 1, 16, 16)); fiber[:, :, :, :, 7:9] = 1.0

    sa.apply_scroll_specific_3d_augmentations(x, ink, fiber, cfg)

    assert called == {
        "scroll_decohesion", "scroll_warping", "scroll_squeeze", "scroll_z_dropout",
        "scroll_intensity_drift", "scroll_sheet_compression", "scroll_thick_slice",
        "scroll_rician_noise", "scroll_blank_rectangles",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=.:scripts/training .venv/bin/python -m pytest tests/test_scroll_specific_augmentations.py -q`
Expected: FAIL — the spied functions are not all called (the current `train`-imported adapter only calls 4), or `ImportError` once the import is repointed but the library adapter still delegates to a 4-family path.

- [ ] **Step 3: Rewrite the adapter to delegate to the explicit API**

Replace the body of `apply_scroll_specific_3d_augmentations` in `scroll_augmentations.py` with:

```python
def apply_scroll_specific_3d_augmentations(x, target_ink, target_fiber, config):
    """Config adapter: read aug_scroll_*_p off `config` and apply all nine
    scroll augmentations via apply_scroll_augmentations(). This is what the
    autoresearch loop calls."""
    if config is None:
        return x, target_ink, target_fiber
    probs = ScrollAugProbs(
        decohesion=float(getattr(config, "aug_scroll_decohesion_p", 0.0)),
        warping=float(getattr(config, "aug_scroll_warping_p", 0.0)),
        squeeze=float(getattr(config, "aug_scroll_squeeze_p", 0.0)),
        z_dropout=float(getattr(config, "aug_scroll_z_dropout_p", 0.0)),
        intensity_drift=float(getattr(config, "aug_scroll_intensity_drift_p", 0.0)),
        sheet_compression=float(getattr(config, "aug_scroll_sheet_compression_p", 0.0)),
        thick_slice=float(getattr(config, "aug_scroll_thick_slice_p", 0.0)),
        rician_noise=float(getattr(config, "aug_scroll_rician_noise_p", 0.0)),
        blank_rectangles=float(getattr(config, "aug_scroll_blank_rectangles_p", 0.0)),
    )
    return apply_scroll_augmentations(x, target_ink, target_fiber, probs)
```

Note: the explicit API references the module-level `scroll_*` names, so `monkeypatch.setattr(sa, "scroll_decohesion", ...)` is observed (the dispatcher must call them as module globals, which it does).

Add `__all__` near the top of the module's public section:

```python
__all__ = [
    "ScrollAugProbs",
    "apply_scroll_augmentations",
    "apply_scroll_specific_3d_augmentations",
    "scroll_decohesion", "scroll_warping", "scroll_squeeze", "scroll_z_dropout",
    "scroll_intensity_drift", "scroll_sheet_compression", "scroll_thick_slice",
    "scroll_rician_noise", "scroll_blank_rectangles",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=.:scripts/training .venv/bin/python -m pytest tests/test_scroll_specific_augmentations.py tests/test_scroll_aug_library.py -q`
Expected: PASS (all, including the new guard and the pre-existing shape/bounds test).

- [ ] **Step 5: Commit**

```bash
git add scroll_augmentations.py tests/test_scroll_specific_augmentations.py
git commit -m "feat(augmentations): config adapter delegates to library; guard all 9 families fire"
```

---

## Task 3: Verify library import resolves the way the loop imports train.py

**Files:** none (verification only)

- [ ] **Step 1: Confirm bare top-level import resolves under package import**

Run:
```bash
PYTHONPATH=. .venv/bin/python -c "from scroll_augmentations import apply_scroll_specific_3d_augmentations, ScrollAugProbs; print('lib import OK')"
PYTHONPATH=. .venv/bin/python -c "import scroll_augmentations; print('all:', scroll_augmentations.__all__[:3])"
```
Expected: both print OK. (If `ImportError`, stop — the train.py swap in Task 4 would crash the loop; resolve before proceeding.)

---

## Task 4: Switch train.py to the library; delete inline duplicates (LOOP-CRITICAL)

**Files:**
- Modify: `scripts/training/train.py` — delete lines for `_warp_2d_tensor` (705), `_scroll_squeeze_warp` (718), `apply_scroll_specific_3d_augmentations` (751); add import.

- [ ] **Step 1: Pause the loop**

```bash
pgrep -f "python run_autoresearch_loop.py" | xargs -r kill -9
pgrep -f "scripts/training/train.py" | xargs -r kill -9
sleep 2; nvidia-smi --query-gpu=memory.used --format=csv,noheader   # expect ~6 MiB
```

- [ ] **Step 2: Add the import**

In `scripts/training/train.py`, near the other top-level project imports (e.g. after `from scripts.cldice_loss import SoftClDiceLoss`), add:

```python
from scroll_augmentations import apply_scroll_specific_3d_augmentations
```

- [ ] **Step 3: Delete the three inline functions**

Delete the entire bodies of `_warp_2d_tensor` (starts line ~705), `_scroll_squeeze_warp` (~718), and `apply_scroll_specific_3d_augmentations` (~751) from `train.py`. Leave the call site (`return apply_scroll_specific_3d_augmentations(x_aug, ink_aug, fiber_aug, config)`, ~line 1063) unchanged — it now resolves to the imported library function. Verify no other code in `train.py` references `_warp_2d_tensor` or `_scroll_squeeze_warp` (Task context confirmed only `_scroll_squeeze_warp` used `_warp_2d_tensor`; `_scroll_squeeze_warp` is only used by the deleted dispatcher).

- [ ] **Step 4: Verify tests + smoke**

```bash
PYTHONPATH=.:scripts/training .venv/bin/python -m pytest tests/test_scroll_specific_augmentations.py tests/test_scroll_aug_library.py -q
PYTHONPATH=. .venv/bin/python scripts/training/train.py --smoke
```
Expected: tests PASS; smoke prints `PREFLIGHT OK`.

- [ ] **Step 5: End-to-end short run with augmentations active (no NaN)**

```bash
.venv/bin/python -c "import json;c=json.load(open('config.json'));c['aug_scroll_blank_rectangles_p']=1.0;c['aug_scroll_rician_noise_p']=1.0;c['aug_scroll_thick_slice_p']=1.0;c['time_budget']=45;json.dump(c,open('/tmp/cfg_aug.json','w'))"
PYTHONPATH=. .venv/bin/python scripts/training/train.py --test --config /tmp/cfg_aug.json 2>&1 | grep -iE "Instability|NaN|Traceback|val_bpb \(Off|RESULT" | tail -4
rm -f /tmp/cfg_aug.json
```
Expected: a `val_bpb (Official)` line and `[RESULT] ...`; NO `Instability`/`NaN`/`Traceback`.

- [ ] **Step 6: Commit (loop still paused)**

```bash
git add scripts/training/train.py
git commit -m "refactor(train): use scroll_augmentations library; remove inline duplicates (fixes 5 no-op augmentations)"
```

- [ ] **Step 7: Restart the loop and confirm a clean cycle start**

```bash
bash start.sh; sleep 10
grep -c ModuleNotFoundError autoresearch.out   # expect 0
tail -3 autoresearch.out
```
Expected: 0 import errors; output shows `Applying ...` / `Running ... training`.

---

## Task 5: Visual demos for all 9 families

**Files:**
- Modify: `scripts/visualize_scroll_augmentations.py`

- [ ] **Step 1: Inspect current coverage**

Run: `PYTHONPATH=. .venv/bin/python scripts/visualize_scroll_augmentations.py --help`
Read the script: confirm it imports from `scroll_augmentations` and lists which families it renders.

- [ ] **Step 2: Ensure all 9 families render to reports/augmentation_demos/**

Edit the script so it: imports each of the 9 `scroll_*` functions (and uses `scroll_decohesion`, `scroll_warping`, `scroll_squeeze`, `scroll_z_dropout`, `scroll_intensity_drift`, `scroll_sheet_compression`, `scroll_thick_slice`, `scroll_rician_noise`, `scroll_blank_rectangles`), renders a before/after montage per family on a real Fr47 patch, and writes PNGs to `reports/augmentation_demos/<family>.png`. Replace the stale docstring line claiming the augmentations "live in train.py" with a pointer to `scroll_augmentations.py`.

- [ ] **Step 3: Generate the demos**

```bash
PYTHONPATH=. .venv/bin/python scripts/visualize_scroll_augmentations.py --out reports/augmentation_demos
ls reports/augmentation_demos/
```
Expected: 9 PNGs (one per family), each a visible before/after.

- [ ] **Step 4: Commit**

```bash
git add scripts/visualize_scroll_augmentations.py reports/augmentation_demos/
git commit -m "docs(augmentations): visual before/after demos for all 9 scroll families"
```

---

## Task 6: Library documentation

**Files:**
- Create: `docs/SCROLL_AUGMENTATIONS.md`
- Modify: `README.md` (add a short "Scroll augmentations" subsection linking the doc + demos)

- [ ] **Step 1: Write `docs/SCROLL_AUGMENTATIONS.md`**

Cover: one paragraph per family (what scroll-physics artifact it models — pull from the existing docstrings in `scroll_augmentations.py`), the parameter ranges, the `ScrollAugProbs` + `apply_scroll_augmentations` usage example below, links to `reports/augmentation_demos/`, and a reference to villa issue #201.

```python
import torch
from scroll_augmentations import ScrollAugProbs, apply_scroll_augmentations

x = torch.rand(2, 1, 16, 64, 64)        # [B,C,Z,H,W] CT volume in [0,1]
ink = torch.zeros(2, 1, 64, 64)         # [B,1,H,W]
fiber = torch.zeros(2, 1, 1, 64, 64)    # [B,1,1,H,W]

probs = ScrollAugProbs(decohesion=0.25, squeeze=0.25, blank_rectangles=0.5)
x_aug, ink_aug, fiber_aug = apply_scroll_augmentations(x, ink, fiber, probs)
```

- [ ] **Step 2: Add a README subsection**

Under the existing "Design choices" / project structure area of `README.md`, add a short subsection pointing to `docs/SCROLL_AUGMENTATIONS.md` and the demo images, noting it addresses villa issue #201.

- [ ] **Step 3: Commit**

```bash
git add docs/SCROLL_AUGMENTATIONS.md README.md
git commit -m "docs(augmentations): scroll-augmentation library reference + README pointer"
```

---

## Verification (whole feature)

- [ ] `PYTHONPATH=.:scripts/training .venv/bin/python -m pytest tests/test_scroll_aug_library.py tests/test_scroll_specific_augmentations.py -q` → all pass (incl. the 9-family guard).
- [ ] `train.py --smoke` prints `PREFLIGHT OK`; the `--test` run shows no NaN/instability with the new augmentations active.
- [ ] Loop restarted, `grep -c ModuleNotFoundError autoresearch.out` is 0, a cycle is running.
- [ ] `reports/augmentation_demos/` has 9 before/after PNGs.
- [ ] Diff limited to: `scroll_augmentations.py`, `scripts/training/train.py`, the two test files, `scripts/visualize_scroll_augmentations.py`, `docs/SCROLL_AUGMENTATIONS.md`, `README.md`, and the demo PNGs.
- [ ] `git push origin main`.
