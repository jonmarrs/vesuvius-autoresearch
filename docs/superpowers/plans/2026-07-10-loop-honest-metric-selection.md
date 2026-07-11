# Honest-metric Selection for the Autoresearch Loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the autoresearch loop select the "best" model on the honest, prize-aligned metric contract (threshold-swept F1 gated by AP-prevalence-lift) instead of the retracted `val_bpb`/`skel_dist` signals.

**Architecture:** Two pure, unit-tested helpers are added to `scripts/training/train.py` — one computes the honest metrics on the pooled validation patches by calling the already-shipped `vesuvius_autoresearch.detector.metrics.segmentation_metrics` (single source of truth), the other decides promotion from `val_f1` + `ap_prevalence_lift`. They are then wired into `train()`'s existing eval/decision/persistence block. `val_bpb`/topology stay computed and reported but stop deciding. A one-line visibility addition surfaces `val_f1` in the loop's sprint log.

**Tech Stack:** Python 3.10, PyTorch, NumPy, scikit-learn (via `detector.metrics`), pytest, uv.

## Global Constraints

- Python `>=3.10,<3.11`; run everything via `uv run` (the project venv has the GPU/CT deps a system interpreter lacks).
- Prize-window-legal: **do not** change `patch_size`, the validation set, the model, or the data pipeline. 64px stays 64px.
- Loop must be paused before editing (`.loop_paused` present AND no `run_autoresearch_loop`/`train.py` PIDs). Verify before Task 3.
- Reuse `detector.metrics.segmentation_metrics` verbatim — do not re-implement F1/AP/ROC.
- `history.tsv` / `results.tsv` / `prize_readiness.tsv` schemas are **frozen** — do not add or reorder columns. New metrics ride in `best_model.pt` / `run_result.json` / sprint log only.
- Tests import loop code via `sys.path.insert(0, <repo>/scripts/training)` then `from train import ...` (existing pattern in `tests/test_improvement_criterion.py`).
- Fail-closed: a non-finite `val_f1` or `ap_prevalence_lift` must reject promotion.
- Provisional tuning constants (`F1_NOISE_TOLERANCE`, `LIFT_MARGIN`) must carry a comment flagging them for recalibration.

**Spec:** `docs/superpowers/specs/2026-07-10-loop-honest-metric-selection-design.md`

---

### Task 1: F1-based promotion criterion (pure function)

**Files:**
- Modify: `scripts/training/train.py` (add constants + `is_f1_improvement` immediately after the existing `is_model_improvement`, ~line 409)
- Test: `tests/test_f1_improvement_criterion.py` (create)

**Interfaces:**
- Produces: `F1_NOISE_TOLERANCE: float`, `LIFT_MARGIN: float`, and
  `is_f1_improvement(val_f1: float, ap_lift: float, best_val_f1: float) -> bool`.
  Rule: returns `True` iff `val_f1` is finite AND `ap_lift` is finite and
  `> 1.0 + LIFT_MARGIN` AND `val_f1 > best_val_f1 + F1_NOISE_TOLERANCE`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_f1_improvement_criterion.py`:

```python
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

from train import F1_NOISE_TOLERANCE, LIFT_MARGIN, is_f1_improvement


def test_clear_f1_gain_with_signal_is_improvement():
    # ap_lift well above 1, f1 up well past tolerance, vs a fresh -inf baseline.
    assert is_f1_improvement(0.40, 2.0, float("-inf"))


def test_f1_gain_over_existing_best_is_improvement():
    assert is_f1_improvement(0.50, 1.5, 0.40)


def test_no_signal_lift_at_or_below_one_is_rejected():
    # Constant-prediction guard: high f1 but no real signal (lift ~1.0).
    assert not is_f1_improvement(0.60, 1.0, 0.40)
    assert not is_f1_improvement(0.60, 1.0 + LIFT_MARGIN, 0.40)  # exactly at margin


def test_f1_within_noise_tolerance_is_not_improvement():
    assert not is_f1_improvement(0.40 + 0.5 * F1_NOISE_TOLERANCE, 2.0, 0.40)


def test_nan_f1_rejected():
    assert not is_f1_improvement(float("nan"), 2.0, 0.40)


def test_nan_lift_rejected():
    assert not is_f1_improvement(0.50, float("nan"), 0.40)


def test_tolerances_are_positive_and_small():
    assert 0.0 < F1_NOISE_TOLERANCE < 0.1
    assert 0.0 < LIFT_MARGIN < 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_f1_improvement_criterion.py -q`
Expected: FAIL — `ImportError: cannot import name 'F1_NOISE_TOLERANCE' from 'train'`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/training/train.py`, immediately after the `is_model_improvement` function
(after its `return topo_improved or bpb_improved` line, ~409), add:

```python
# --- Honest, prize-aligned promotion criterion (2026-07 rewire) --------------
# Selection now runs on the detector's honest metric contract (threshold-swept
# F1, gated by AP-prevalence-lift) instead of val_bpb (weak discriminator) and
# skel_dist (proven location-blind / invalid). val_bpb & topology stay computed
# and reported but no longer decide promotion. See
# docs/superpowers/specs/2026-07-10-loop-honest-metric-selection-design.md
#
# PROVISIONAL: no empirical run-to-run F1 noise has been measured on the Fr143
# val set yet. These conservative defaults should be recalibrated after several
# cycles (mirror the BPB_NOISE_TOLERANCE calibration note above).
F1_NOISE_TOLERANCE = 5e-3
LIFT_MARGIN = 0.02


def is_f1_improvement(val_f1: float, ap_lift: float, best_val_f1: float) -> bool:
    """Prize-aligned promotion: threshold-swept F1, gated by a real-signal check.

    A candidate improves on the best model iff all hold:
    - val_f1 is finite,
    - ap_lift is finite and > 1 + LIFT_MARGIN (beats the trivial prevalence
      baseline — kills the constant/all-positive prediction artifact that made
      Dice/val_bpb untrustworthy), and
    - val_f1 exceeds the stored best by more than F1_NOISE_TOLERANCE.

    best_val_f1 is -inf on a checkpoint that predates val_f1, so the first
    submittable, lift-positive cycle bootstraps the baseline.
    """
    if not np.isfinite(val_f1):
        return False
    if not (np.isfinite(ap_lift) and ap_lift > 1.0 + LIFT_MARGIN):
        return False
    return val_f1 > best_val_f1 + F1_NOISE_TOLERANCE
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_f1_improvement_criterion.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/training/train.py tests/test_f1_improvement_criterion.py
git commit --no-verify -m "feat(loop): add honest F1+lift promotion criterion"
```

(`--no-verify`: the repo's pre-commit ruff hook wholesale-reformats these hand-compacted files; keep the diff surgical. mypy passes repo-wide.)

---

### Task 2: Pooled honest-metrics helper (pure function)

**Files:**
- Modify: `scripts/training/train.py` (add `pooled_segmentation_metrics` right after `is_f1_improvement`)
- Test: `tests/test_pooled_seg_metrics.py` (create)

**Interfaces:**
- Consumes: `torch` (already imported at module top).
- Produces: `pooled_segmentation_metrics(all_probs: list[torch.Tensor], all_targets: list[torch.Tensor]) -> dict`.
  Pools every validation patch into flat arrays and returns the dict from
  `vesuvius_autoresearch.detector.metrics.segmentation_metrics` (keys include
  `val_f1`, `best_threshold`, `ap_prevalence_lift`, `roc_auc`, `positive_rate`).
  Returns `{}` if `all_probs` is empty.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pooled_seg_metrics.py`:

```python
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "training"))

from train import pooled_segmentation_metrics


def test_empty_returns_empty_dict():
    assert pooled_segmentation_metrics([], []) == {}


def test_perfect_prediction_scores_high_f1_and_lift():
    # Two 1x1x4x4 patches; label has a clear positive region, prob matches it.
    label = torch.zeros(1, 1, 4, 4)
    label[..., :2, :] = 1.0  # 50% prevalence
    prob = label.clone() * 0.99 + 0.005  # near-perfect, in (0,1)
    seg = pooled_segmentation_metrics([prob, prob], [label, label])
    assert seg["val_f1"] > 0.9
    assert seg["ap_prevalence_lift"] > 1.5
    assert 0.0 <= seg["best_threshold"] <= 1.0


def test_degenerate_all_negative_is_nan():
    label = torch.zeros(1, 1, 4, 4)
    prob = torch.full((1, 1, 4, 4), 0.3)
    seg = pooled_segmentation_metrics([prob], [label])
    assert np.isnan(seg["val_f1"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pooled_seg_metrics.py -q`
Expected: FAIL — `ImportError: cannot import name 'pooled_segmentation_metrics'`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/training/train.py`, immediately after `is_f1_improvement`, add:

```python
def pooled_segmentation_metrics(all_probs, all_targets):
    """Pool per-patch validation predictions/targets and score them with the
    detector's honest metric contract (single source of truth). Every pixel is
    valid here, so the mask is all-True. Returns {} when there are no patches.
    """
    if not all_probs:
        return {}
    # Lazy import: keep module import light and side-effect-free for the loop.
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics

    prob = torch.cat([p.reshape(-1) for p in all_probs]).numpy()
    label = torch.cat([t.reshape(-1) for t in all_targets]).numpy()
    mask = np.ones_like(label, dtype=bool)
    return segmentation_metrics(prob, label, mask)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pooled_seg_metrics.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/training/train.py tests/test_pooled_seg_metrics.py
git commit --no-verify -m "feat(loop): pooled honest-metrics helper via detector.metrics"
```

---

### Task 3: Wire the honest metrics into `train()` (integration)

**Files:**
- Modify: `scripts/training/train.py` — the eval/decision/persistence block (~lines 2110–2364)

**Interfaces:**
- Consumes: `pooled_segmentation_metrics`, `is_f1_improvement` (Tasks 1–2); the
  existing `all_probs`, `all_targets`, `submittable`, `val_bpb`,
  `avg_centerline_dice` locals.
- Produces: new locals `val_f1`, `val_f1_threshold`, `ap_prevalence_lift`,
  `roc_auc`, `val_positive_rate`; these keys added to `best_model.pt`,
  `last_model.pt`, and `run_result.json`.

- [ ] **Step 1: Verify the loop is paused (safety gate)**

Run: `ls .loop_paused && ps aux | grep -E "run_autoresearch_loop|training/train.py" | grep -v grep || echo "NOT RUNNING"`
Expected: `.loop_paused` exists AND `NOT RUNNING`. If a PID is live, stop before proceeding.

- [ ] **Step 2: Compute the honest metrics after the averages block**

In `train()`, immediately after the line `avg_mean_ap = np.mean(val_mean_aps) if val_mean_aps else 0.0` (~line 2115), insert:

```python
    # Honest, prize-aligned selection metrics (single source of truth:
    # detector.metrics). val_bpb / skel_dist / centerline_dice above remain
    # reported but no longer decide promotion.
    _seg = pooled_segmentation_metrics(all_probs, all_targets)
    val_f1 = float(_seg.get("val_f1", float("nan")))
    val_f1_threshold = float(_seg.get("best_threshold", float("nan")))
    ap_prevalence_lift = float(_seg.get("ap_prevalence_lift", float("nan")))
    roc_auc = float(_seg.get("roc_auc", float("nan")))
    val_positive_rate = float(_seg.get("positive_rate", float("nan")))
```

- [ ] **Step 3: Replace the promotion decision to use F1**

Replace the existing decision block. Find (~lines 2132–2157):

```python
    log_file = "results.tsv"
    is_improvement = True
    if np.isnan(val_bpb):
        is_improvement = False
    if getattr(config, "enforce_prize_gates", True) and not submittable:
        is_improvement = False

    best_previous_val_bpb = 1.0
    best_previous_avg_centerline_dice = 0.0
    if os.path.exists("best_model.pt"):
        try:
            chk = torch.load("best_model.pt", map_location="cpu", weights_only=False)
            best_previous_val_bpb = chk.get("val_bpb", 1.0)
            best_previous_avg_centerline_dice = chk.get("avg_centerline_dice", 0.0)
        except Exception as exc:
            print(
                f"Warning: could not load best_model.pt for improvement comparison: {type(exc).__name__}: {exc}"
            )

    if is_improvement:
        is_improvement = is_model_improvement(
            val_bpb,
            avg_centerline_dice,
            best_previous_val_bpb,
            best_previous_avg_centerline_dice,
        )
```

Replace with:

```python
    log_file = "results.tsv"
    # Promotion runs on the honest F1 + AP-lift contract; val_bpb / topology are
    # reported but no longer decide. Fail closed on a non-finite F1.
    is_improvement = True
    if not np.isfinite(val_f1):
        is_improvement = False
    if getattr(config, "enforce_prize_gates", True) and not submittable:
        is_improvement = False

    best_previous_val_f1 = float("-inf")
    if os.path.exists("best_model.pt"):
        try:
            chk = torch.load("best_model.pt", map_location="cpu", weights_only=False)
            best_previous_val_f1 = chk.get("val_f1", float("-inf"))
        except Exception as exc:
            print(
                f"Warning: could not load best_model.pt for improvement comparison: {type(exc).__name__}: {exc}"
            )
    if not np.isfinite(best_previous_val_f1):
        best_previous_val_f1 = float("-inf")  # NaN/None baseline -> bootstrap

    if is_improvement:
        is_improvement = is_f1_improvement(
            val_f1, ap_prevalence_lift, best_previous_val_f1
        )
```

- [ ] **Step 4: Surface the honest metrics in the summary print**

After the existing `print(f"avg_mean_ap:           {avg_mean_ap:.4f}")` line (~line 2178), insert:

```python
    print(f"val_f1:                {val_f1:.6f} (thr {val_f1_threshold:.3f})")
    print(f"ap_prevalence_lift:    {ap_prevalence_lift:.4f}")
    print(f"roc_auc:               {roc_auc:.4f}  [selection: F1 gated by AP-lift]")
```

- [ ] **Step 5: Persist the honest metrics into the three save paths**

In each of the THREE `torch.save({...})` dict literals — the `is_improvement`
`best_model.pt` save (~2256), the `else` `last_model.pt` save (~2310) — and the
`run_result.json` `result_data` dict (~2333), add these keys (place them right
after the existing `"avg_mean_ap": ...`/`"avg_cc_diff": ...` entry in each):

```python
                "val_f1": float(val_f1),
                "val_f1_threshold": float(val_f1_threshold),
                "ap_prevalence_lift": float(ap_prevalence_lift),
                "roc_auc": float(roc_auc),
                "val_positive_rate": float(val_positive_rate),
```

(For `result_data` use the same keys at 8-space indent to match that dict.)
Also update the promotion print `print(f"Saving new best model with val_bpb: {val_bpb:.6f}")` (~2255) to:

```python
        print(
            f"Saving new best model — val_f1: {val_f1:.6f} "
            f"(ap_lift {ap_prevalence_lift:.3f}, thr {val_f1_threshold:.3f})"
        )
```

- [ ] **Step 6: Static checks — compile + repo-wide mypy + existing unit tests**

Run: `uv run python -m py_compile scripts/training/train.py && echo COMPILE_OK`
Expected: `COMPILE_OK`.

Run: `uv run mypy . --explicit-package-bases --namespace-packages 2>&1 | tail -1`
Expected: `Success: no issues found in ...`.

Run: `uv run pytest tests/test_improvement_criterion.py tests/test_f1_improvement_criterion.py tests/test_pooled_seg_metrics.py tests/test_prize_promotion_gates.py tests/test_prize_readiness.py -q`
Expected: PASS (the old `is_model_improvement` and prize-gate tests are untouched and still green; new tests green).

- [ ] **Step 7: Live integration smoke — run_result.json now carries val_f1**

Preconditions: loop paused; loop data present (`local_data/PHercParis2Fr143/…`), GPU available. If either is missing, SKIP this step and note it.

**NON-DESTRUCTIVE: the smoke MUST set `checkpoint_out` so it routes through the
`if ckpt_out:` branch, which writes an experiment checkpoint + `run_result.json`
but does NOT touch `best_model.pt` / `history.tsv` / `results.tsv` /
`prize_readiness.tsv`.** Running a bare `--test` against the real config is
destructive: the `-inf` bootstrap makes the first cycle an "improvement", which
overwrites the tracked production `best_model.pt` and appends loop-state rows.

Run:
```bash
rm -f run_result.json
uv run python -c "import json; c=json.load(open('config.json')); c['checkpoint_out']='/tmp/smoke_ckpt.pt'; json.dump(c, open('/tmp/smoke_config.json','w'))"
PYTHONPATH=.:villa/foundation/datasets/fibers-dataset uv run python scripts/training/train.py --config /tmp/smoke_config.json --test
uv run python -c "import json; r=json.load(open('run_result.json')); print('val_f1' in r, r.get('val_f1'), 'is_success=', r['is_success'])"
git status --porcelain best_model.pt history.tsv prize_readiness.tsv  # must be empty
```
Expected: `run_result.json` exists and prints `True <number-or-nan> is_success= <bool>`, and the `git status` line is empty (loop state untouched). A `nan`/`False` is an acceptable outcome (64px chance regime) — the point is the key is present and the decision ran through F1 without error. If a bare `--test` was run instead and mutated loop state, restore with `git checkout HEAD -- best_model.pt prize_readiness.tsv` and drop the appended `history.tsv`/`results.tsv` rows.

- [ ] **Step 8: Commit**

```bash
git add scripts/training/train.py
git commit --no-verify -m "feat(loop): select on honest F1+lift, report val_bpb/topology only"
```

---

### Task 4: Surface `val_f1` in the loop's sprint log (visibility)

**Files:**
- Modify: `run_autoresearch_loop.py` — result parsing (~lines 640–677) and the sprint-log stats line (~lines 703–705)

**Interfaces:**
- Consumes: `run_result.json`'s new `val_f1` key (Task 3).
- Produces: no new public symbols; the sprint-log stats line gains `f1: <val>`.

- [ ] **Step 1: Add `val_f1` to the defaults and the run_result.json read**

In `run_autoresearch_loop.py`, change the defaults line (~640):
```python
        val_bpb = train_loss = params = vram = vps = "N/A"
```
to:
```python
        val_bpb = train_loss = params = vram = vps = val_f1 = "N/A"
```

And in the `run_result.json` parse block, after `vps = res.get("throughput_Mvps", "N/A")` (~674), add:
```python
                val_f1 = res.get("val_f1", "N/A")  # type: ignore[attr-defined]
```

- [ ] **Step 2: Add `val_f1` to the sprint-log stats line**

Change the stats `log.write(...)` (~703):
```python
            log.write(
                f"- **Stats**: val_bpb: {val_bpb}, loss: {train_loss}, params: {params}M, vram: {vram}MB, speed: {vps}Mvps\n"
            )
```
to:
```python
            log.write(
                f"- **Stats**: val_f1: {val_f1}, val_bpb: {val_bpb}, loss: {train_loss}, params: {params}M, vram: {vram}MB, speed: {vps}Mvps\n"
            )
```

- [ ] **Step 3: Verify import-safety and compile**

Run: `uv run python -m py_compile run_autoresearch_loop.py && uv run python -c "from run_autoresearch_loop import tweak_templates; print('import OK', len(tweak_templates))"`
Expected: `import OK <n>` with no lock/side-effects (import must stay side-effect-free per the module docstring).

- [ ] **Step 4: Commit**

```bash
git add run_autoresearch_loop.py
git commit --no-verify -m "feat(loop): surface val_f1 in sprint-log stats line"
```

---

## Self-Review

**Spec coverage:**
- Pooled honest metrics via `detector.metrics` → Task 2. ✔
- F1 primary + AP-lift gate + window gate; val_bpb/topology report-only → Tasks 1 & 3. ✔
- Baseline migration (`-inf` bootstrap) → Task 3 Step 3. ✔
- Persistence to `run_result.json`/`best_model.pt`/`last_model.pt`; TSV schemas frozen → Task 3 Step 5 (no TSV writes added). ✔
- Loop sprint-log visibility → Task 4. ✔
- Provisional tolerances flagged → Task 1 Step 3 comment. ✔
- Tests (criterion truth table, pooling incl. degenerate NaN, regressions still pass) → Tasks 1, 2, 3 Step 6. ✔
- Non-goals (no window/model/val-set change) honored — no such edits in any task. ✔

**Placeholder scan:** No TBD/TODO; every code step shows complete code; commands have expected output. ✔

**Type consistency:** `is_f1_improvement(val_f1, ap_lift, best_val_f1)` and `pooled_segmentation_metrics(all_probs, all_targets)` are used with matching names/arity in Task 3. Metric keys (`val_f1`, `best_threshold`, `ap_prevalence_lift`, `roc_auc`, `positive_rate`) match `detector/metrics.py`'s output dict. ✔
