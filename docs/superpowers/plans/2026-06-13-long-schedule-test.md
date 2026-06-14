# Longer From-Scratch Schedule Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one clean ~12h fresh-init resenc training while logging pooled V-region pixel AUC as a learning curve, to decide whether the ~0.557 detection ceiling is budget- or capacity/window-limited.

**Architecture:** Reuse the production `scripts/training/train.py` path unchanged except for a gated periodic-eval hook (default off). The hook periodically samples fixed validation patches, computes pooled pixel AUC via a new pure helper, saves a step-tagged checkpoint, and appends a row to a curve CSV. A fresh 12h run (best_model.pt moved aside, isolated via checkpoint_out) then produces the curve.

**Tech Stack:** Python, PyTorch, NumPy, scikit-learn (`roc_auc_score`), pytest. Reuses `VesuviusLabeledDataset`, `checkpoint_out` (committed `fc26ea9c`/`2d3d3678`), `jitter` flag (`6224c711`).

**Spec:** `docs/superpowers/specs/2026-06-13-long-schedule-test-design.md`

---

## File Structure

- `scripts/pixel_auc.py` (create) — pure `pooled_pixel_auc(prob_arrays, label_arrays)`. Standalone module (no `train` import) to avoid a circular import with `measure_ink_auc.py`.
- `scripts/training/train.py` (modify) — two config fields + a gated periodic-eval helper + a one-line hook call in the training loop.
- `experiments/long_schedule/cfg_long.json` (create) — the fresh 12h run config.
- `tests/test_pixel_auc.py` (create).
- `experiments/long_schedule/long_model.pt*`, `*.curve.csv`, `*.log` (runtime, gitignored).
- `FINDINGS.md`, memory (modify) — record the verdict.

---

## Task 1: Pure pooled-pixel-AUC helper

**Files:**
- Create: `scripts/pixel_auc.py`
- Test: `tests/test_pixel_auc.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pixel_auc.py
import numpy as np

from scripts.pixel_auc import pooled_pixel_auc


def test_perfect_separation():
    probs = [np.array([0.9, 0.8]), np.array([0.1, 0.2])]
    labels = [np.array([1, 1]), np.array([0, 0])]
    assert pooled_pixel_auc(probs, labels) == 1.0


def test_random_is_near_half():
    rng = np.random.RandomState(0)
    probs = [rng.rand(500)]
    labels = [(rng.rand(500) > 0.5).astype(int)]
    assert 0.4 < pooled_pixel_auc(probs, labels) < 0.6


def test_single_class_guard_returns_half():
    probs = [np.array([0.9, 0.1])]
    labels = [np.array([1, 1])]  # only one class present
    assert pooled_pixel_auc(probs, labels) == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch && PYTHONPATH=. .venv/bin/python -m pytest tests/test_pixel_auc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.pixel_auc'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/pixel_auc.py
"""Pooled pixel-level AUC over many per-patch probability/label arrays. Kept in
its own module (no `train` import) so train.py can import it without the circular
dependency that `measure_ink_auc.py` would introduce."""

import numpy as np
from sklearn.metrics import roc_auc_score


def pooled_pixel_auc(prob_arrays, label_arrays):
    """prob_arrays / label_arrays: lists of 1-D arrays (per-patch flattened
    sigmoid probabilities and binary labels). Concatenates all pixels and returns
    a single roc_auc_score; returns 0.5 if only one class is present."""
    p = np.concatenate([np.asarray(a).ravel() for a in prob_arrays])
    y = np.concatenate([np.asarray(a).ravel() for a in label_arrays])
    y = (y > 0.5).astype(int)
    if y.min() == y.max():
        return 0.5
    return float(roc_auc_score(y, p))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pixel_auc.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/pixel_auc.py tests/test_pixel_auc.py
git commit -m "feat(eval): pooled pixel-AUC helper"
```
(ruff-format may reformat+abort the first commit; re-add and re-run if so — no --no-verify.)

---

## Task 2: Gated periodic-eval hook in train.py

**Files:**
- Modify: `scripts/training/train.py` — config dataclass (after `checkpoint_out`, ~line 113); new helper function (just below `confidence_weight`, ~line 707); hook call in the training loop (after `step += 1`, ~line 1865).

This task has no standalone unit test (the hook is deep in the training loop); it is validated by the smoke run in Task 3. The pure AUC math is already tested in Task 1.

- [ ] **Step 1: Add the two config fields**

Find this line in the `ExperimentConfig` dataclass:
```python
    checkpoint_out: str | None = None
```
Replace with:
```python
    checkpoint_out: str | None = None
    eval_every_steps: int = 0
    eval_sample_patches: int = 250
```

- [ ] **Step 2: Add the periodic-eval helper**

Find the `confidence_weight` function (added earlier):
```python
def confidence_weight(target):
    """Per-pixel confidence weight for soft pseudo-labels: 1.0 where the label
    is confident (0 or 1), 0.0 in the uncertain band (encoded as 0.5). Recomputed
    from the (possibly augmented) target each step, so it survives mixup/affine
    interpolation, and is a no-op on true binary labels."""
    return (2.0 * (target - 0.5).abs()).clamp(0.0, 1.0)
```
Immediately AFTER it, add this helper:

```python
def periodic_pixel_auc_eval(model, val_dataset, config, device, step, elapsed_s):
    """Gated learning-curve probe: pooled pixel AUC on a FIXED random sample of
    validation patches, plus a step-tagged checkpoint and a CSV row. Wrapped so a
    mid-run eval glitch cannot kill a multi-hour training run. Indices are drawn
    once (seeded) so every call scores the same patches."""
    import csv

    import numpy as np

    from scripts.pixel_auc import pooled_pixel_auc

    prefix = config.checkpoint_out or "long_model.pt"
    curve_path = f"{prefix}.curve.csv"
    nl = config.num_layers
    try:
        n = min(config.eval_sample_patches, len(val_dataset))
        idxs = np.random.RandomState(12345).permutation(len(val_dataset))[:n]
        model.eval()
        probs, labels = [], []
        with torch.no_grad():
            for i in idxs:
                x_raw, t, _ = val_dataset[int(i)]
                x = x_raw[:, 4 : 4 + nl].unsqueeze(0).to(device)
                out = model(x)
                out = out[0] if isinstance(out, tuple) else out
                probs.append(torch.sigmoid(out).squeeze().float().cpu().numpy().ravel())
                labels.append((t.numpy() > 0.5).astype(int).ravel())
        auc = pooled_pixel_auc(probs, labels)
    except Exception as exc:  # an eval glitch must not kill a 12h run
        print(f"  [curve] eval failed at step {step}: {type(exc).__name__}: {exc}")
        auc = float("nan")
    finally:
        model.train()

    write_header = not os.path.exists(curve_path)
    with open(curve_path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["step", "elapsed_s", "pixel_auc"])
        w.writerow([step, round(elapsed_s, 1), f"{auc:.4f}"])
    try:
        torch.save(
            {"model_state_dict": model.state_dict(), "step": step, "config": asdict(config)},
            f"{prefix}.step{step}.pt",
        )
    except Exception as exc:
        print(f"  [curve] checkpoint save failed at step {step}: {exc}")
    print(f"  [curve] step={step} elapsed={elapsed_s:.0f}s pooled_pixel_auc={auc:.4f}")
```

- [ ] **Step 3: Add the gated hook call in the training loop**

Find this block at the end of the training-loop body:
```python
        step += 1
        if total_training_time >= config.time_budget:
```
Replace with:
```python
        step += 1
        if (
            getattr(config, "eval_every_steps", 0)
            and step % config.eval_every_steps == 0
        ):
            periodic_pixel_auc_eval(
                model, val_data_loader.dataset, config, device, step, total_training_time
            )
        if total_training_time >= config.time_budget:
```

- [ ] **Step 4: Verify the module imports and the default path is inert**

Run: `PYTHONPATH=. .venv/bin/python -c "import sys; sys.path.insert(0,'scripts/training'); import train; print('import OK'); from dataclasses import fields; print('eval_every_steps' in [f.name for f in fields(train.ExperimentConfig)])"`
Expected: `import OK` then `True`.

Run the existing loss tests to confirm nothing broke: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_confidence_weighted_loss.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/training/train.py
git commit -m "feat(train): gated periodic pixel-AUC learning-curve hook"
```

---

## Task 3: Long-run config + smoke gate

**Files:**
- Create: `experiments/long_schedule/cfg_long.json`

- [ ] **Step 1: Write the long-run config**

Generate it from the current production config so all fields are present:
```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p experiments/long_schedule
.venv/bin/python - <<'PYEOF'
import json
c = json.load(open("config.json"))
c.update({
    "uris": ["local_data/PHercParis2Fr47/surface_volume.zarr"],
    "val_uri": "local_data/PHercParis2Fr143_Vregion/surface_volume.zarr",
    "time_budget": 43200,
    "pinned": False,
    "pseudo_label_dir": None,
    "use_uamt": False,
    "use_wandb": False,
    "use_confidence_weight": False,
    "architecture": "resenc_unet",
    "checkpoint_out": "experiments/long_schedule/long_model.pt",
    "eval_every_steps": 18000,
    "eval_sample_patches": 250,
})
json.dump(c, open("experiments/long_schedule/cfg_long.json", "w"), indent=2)
print("wrote cfg_long.json; time_budget", c["time_budget"], "eval_every_steps", c["eval_every_steps"])
PYEOF
```
Note: `eval_every_steps=18000` targets ~12 evals for a 12h run (the 2.5h run reported `max_steps=45000`, so 12h ≈ 216k steps). After the real run reports its `max_steps`, confirm ~12 points; this is a logging cadence only and does not affect training.

- [ ] **Step 2: Smoke-test the hook (tiny budget, frequent eval, verify loop state untouched)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
.venv/bin/python -c "import json; c=json.load(open('experiments/long_schedule/cfg_long.json')); c['time_budget']=90; c['eval_every_steps']=10; c['checkpoint_out']='experiments/long_schedule/smoke_model.pt'; json.dump(c, open('experiments/long_schedule/cfg_smoke.json','w'), indent=2)"
echo "BEFORE: best_model.pt $(stat -c %Y best_model.pt 2>/dev/null || echo NONE) ; history.tsv $(wc -l < history.tsv)"
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/long_schedule/cfg_smoke.json > experiments/long_schedule/smoke.log 2>&1
echo "exit=$?"
echo "AFTER:  best_model.pt $(stat -c %Y best_model.pt 2>/dev/null || echo NONE) ; history.tsv $(wc -l < history.tsv)"
echo "=== curve CSV ==="; cat experiments/long_schedule/smoke_model.pt.curve.csv 2>&1
echo "=== step checkpoints ==="; ls experiments/long_schedule/smoke_model.pt.step*.pt 2>&1
grep -i "\[curve\]" experiments/long_schedule/smoke.log | head
```
Expected: the run completes; `smoke_model.pt.curve.csv` has a header + ≥1 data rows with a finite `pixel_auc`; at least one `smoke_model.pt.step*.pt` exists; `[curve]` lines printed; **`best_model.pt` mtime and `history.tsv` line count UNCHANGED** (note: if `best_model.pt` was already moved aside it prints NONE both times — that is fine; the invariant is "no change"). If the curve CSV is empty or the run errored, stop and fix before the long run.

- [ ] **Step 3: Clean up smoke artifacts and commit the config**

```bash
rm -f experiments/long_schedule/cfg_smoke.json experiments/long_schedule/smoke_model.pt* experiments/long_schedule/smoke.log
git add experiments/long_schedule/cfg_long.json
git commit -m "chore(long): fresh 12h run config with hourly pixel-AUC eval"
```

- [ ] **Step 4: Gitignore runtime artifacts**

Append to `.gitignore`:
```
experiments/long_schedule/*.pt
experiments/long_schedule/*.curve.csv
experiments/long_schedule/*.log
experiments/long_schedule/cfg_smoke.json
```
```bash
git add .gitignore
git commit -m "chore(long): gitignore long-run artifacts"
```

---

## Task 4: Pause loop, fresh init, launch the 12h run

- [ ] **Step 1: Pause the loop and free the GPU**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop|train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 6
nvidia-smi --query-gpu=memory.used --format=csv,noheader
```
Expected: GPU memory near-idle (a few hundred MiB). Kill any lingering `train.py` PID too.

- [ ] **Step 2: Move best_model.pt aside for fresh init**

```bash
test -f best_model.pt.prebkup_pseudolabel || cp best_model.pt best_model.pt.prebkup_pseudolabel
mv best_model.pt best_model.pt.HOLD_long
test -f best_model.pt && echo "WARN present" || echo "fresh-init OK"
```
(If `best_model.pt` was already moved by a prior step and only `.HOLD_*`/`.prebkup_*` exist, ensure no `best_model.pt` is in the CWD before launching, so the run starts from random init.)

- [ ] **Step 3: Launch the 12h run in the background**

```bash
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/long_schedule/cfg_long.json > experiments/long_schedule/long.log 2>&1 &
echo "launched PID $!"
```

- [ ] **Step 4: Confirm fresh init + hook armed (after ~40s)**

```bash
sleep 40
grep -iE "Loading weights from best_model|nnUNet-style ResEnc|Budget-Aware|Valid Patches" experiments/long_schedule/long.log | head
```
Expected: NO "Loading weights from best_model" line (fresh init); `Budget-Aware Scheduling: max_steps=...` printed. Record the reported `max_steps`; if `max_steps/eval_every_steps` is far from ~8–15, it only changes how many curve points you get (acceptable).

---

## Task 5: Analyze the curve, record, restore the loop

- [ ] **Step 1: After the run completes, read the curve**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
cat experiments/long_schedule/long_model.pt.curve.csv
PYTHONPATH=. .venv/bin/python scripts/measure_ink_auc.py --checkpoint experiments/long_schedule/long_model.pt --fragments local_data/PHercParis2Fr143_Vregion 2>&1 | grep -i AUC | tail -1
```
Report the pixel-AUC trajectory (per row), the max, and whether the last third of the curve is still rising (compare the final 3–4 points).

- [ ] **Step 2: Apply the decision rule**

- Max pixel AUC clearly exceeds ~0.557 AND the final points are still rising → **budget-limited**: longer training / a better long schedule is a real lever; flag the final checkpoint as a promotion candidate.
- Curve plateaus at/near ~0.50–0.557 (final points flat) → **capacity/window ceiling**: training longer does not fix detection; the bottleneck is the architecture or the 64px window — redirect strategy.

- [ ] **Step 3: Update FINDINGS.md**

Add a bullet under "What we learned" stating: the run length, the pixel-AUC trajectory (start → max → end), the verdict (budget vs capacity), and the implication. Honest framing consistent with the existing negative-result bullets. If budget-limited, note the promotion candidate and that the production-loop ceiling was a schedule artifact, not a capacity limit.

- [ ] **Step 4: Update memory**

Write `long-schedule-test-result.md` (type project): the verdict, the curve summary, and the link to `[[pseudo-label-self-training-blocked]]` / `[[model-barely-discriminates-ink]]`. Add a one-line pointer in `MEMORY.md`.

- [ ] **Step 5: Commit docs + push**

```bash
git add FINDINGS.md
git commit -m "docs(findings): longer from-scratch schedule test result"
git push origin main
```

- [ ] **Step 6: Restore best_model.pt and the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mv best_model.pt.HOLD_long best_model.pt
cmp -s best_model.pt best_model.pt.prebkup_pseudolabel && echo "model intact" || echo "DIFFERS — investigate"
rm -f .loop_paused
bash start.sh
sleep 20
ps -eo pid,etime,cmd | grep run_autoresearch_loop | grep -v grep
```
Expected: `best_model.pt` restored intact; loop running again. The long run only wrote to `experiments/long_schedule/*` (checkpoint_out), so `best_model.pt`/`history.tsv` were never touched.

---

## Self-Review

**Spec coverage:**
- Pure pooled-pixel-AUC helper, no circular import → Task 1. ✓
- Gated `eval_every_steps` hook (periodic checkpoint + curve CSV + pixel AUC, default off) → Task 2. ✓
- `eval_sample_patches` fixed seeded sample → Task 2 helper. ✓
- Fresh 12h run config, isolated via checkpoint_out → Task 3 + Task 4. ✓
- Smoke gate (curve rows appear, loop state untouched) → Task 3 Step 2. ✓
- try/except so an eval glitch can't kill the run; single-class AUC guard → Task 2 helper + Task 1. ✓
- Decision rule + FINDINGS/memory + restore → Task 5. ✓
- Loop-safety (default off, best_model protected) → Tasks 2/4/5. ✓

**Placeholder scan:** None. `eval_every_steps=18000` is a concrete cadence with a stated refinement note (logging-only, non-critical). The smoke gate resolves any import/path issue before the 12h run.

**Type consistency:** `pooled_pixel_auc(prob_arrays, label_arrays)` signature matches Task 1's definition and the Task 2 call; `periodic_pixel_auc_eval(model, val_dataset, config, device, step, elapsed_s)` is defined and called with matching args (`val_data_loader.dataset` as `val_dataset`); single-sample Z-slice `x_raw[:, 4:4+nl]` matches the established pattern in `generate_pseudo_labels.py`; config fields `eval_every_steps`/`eval_sample_patches`/`checkpoint_out` are consistent across the dataclass, helper, and config file.

**Loop-safety:** `eval_every_steps` defaults to 0 → the hook never fires in the running loop; combined with `checkpoint_out=None` default, the loop's training and persistence are byte-identical until the experiment config opts in.
