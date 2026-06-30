# Cross-Scroll Measurement Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a community-aligned segmentation-metric module and use it to produce the project's first honest cross-scroll measurement by scoring the existing detector (`models/detector/detector_epoch=7.ckpt`) on a held-out Scroll-1 segment — no training.

**Architecture:** A pure-numpy/sklearn `metrics.py` (threshold-swept F1 primary; average-precision + prevalence-lift as honest gates; ROC-AUC as a secondary diagnostic only). `eval.py` consumes it (with backward-compatible `pixel_auc`/`threshold` aliases so the existing reproduce gate and tests keep passing). A `measure.py` harness + `measure` CLI subcommand scores one checkpoint across same-scroll vs cross-scroll fragments and writes a gap report.

**Tech Stack:** numpy, scikit-learn (`average_precision_score`, `roc_auc_score`), Pillow, the existing detector subpackage (`config`/`data`/`infer`). All already in `pyproject.toml`.

## Global Constraints

- **Primary metric is `val_f1` (threshold-swept).** `average_precision` + `ap_prevalence_lift` are the honest, imbalance-robust gates. **ROC-AUC is a secondary diagnostic only — never an optimization target.**
- **Mask-restricted, pooled** over the fragment's masked pixels for every metric.
- **Backward compatibility:** `evaluate(...)` must keep returning `pixel_auc` (= roc_auc) and `threshold` (= best_threshold) keys; `cli.assert_auc` and the `>=0.70` reproduce gate stay unchanged.
- **Isolation:** all code lives under `src/vesuvius_autoresearch/detector/`, `tests/`, `reports/detector/`. Do NOT edit `run_autoresearch_loop.py` or `scripts/training/train.py`. The GPU `measure` run needs the loop paused (`touch .loop_paused` + kill PIDs; resume with `bash start.sh`).
- **No AI-authorship markers** in any committed file, comment, or commit message.
- Run tests with: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU).

## File Structure

- Create `src/vesuvius_autoresearch/detector/metrics.py` — `segmentation_metrics(prob, label, mask, thresholds=None) -> dict`.
- Modify `src/vesuvius_autoresearch/detector/eval.py` — `evaluate` uses `segmentation_metrics`, writes scorecard JSON + `_metrics_by_threshold.csv` + thumbnail, keeps aliases.
- Create `src/vesuvius_autoresearch/detector/measure.py` — `measure(cfg, checkpoint_path, targets, model=None) -> dict`.
- Modify `src/vesuvius_autoresearch/detector/cli.py` — add a `measure` subcommand.
- Tests: `tests/test_detector_metrics.py`, `tests/test_detector_measure.py`; extend `tests/test_detector_eval.py`.

---

### Task 1: Metric module (`metrics.py`)

**Files:**
- Create: `src/vesuvius_autoresearch/detector/metrics.py`
- Test: `tests/test_detector_metrics.py`

**Interfaces:**
- Produces: `segmentation_metrics(prob, label, mask, thresholds=None) -> dict` with keys `val_f1`, `best_threshold`, `f1_at_0.5`, `val_f05`, `precision`, `recall`, `pred_positive_rate`, `average_precision`, `ap_prevalence_lift`, `positive_rate`, `n_pixels`, `roc_auc`, `metrics_by_threshold` (list of `{threshold, precision, recall, f1, f05}`). Degenerate masks (no positive or no negative pixels) return those metric keys as `nan` plus a `note`, never raising.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_detector_metrics.py
import numpy as np
from vesuvius_autoresearch.detector.metrics import segmentation_metrics


def _label():
    lab = np.zeros((64, 64), np.uint8)
    lab[20:44, 20:44] = 1  # ~14% positive
    return lab


def test_perfect_prediction_scores_f1_and_ap_one():
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = lab.astype(np.float32)
    m = segmentation_metrics(prob, lab, mask)
    assert m["val_f1"] > 0.99
    assert m["average_precision"] > 0.99
    assert m["roc_auc"] > 0.99


def test_chance_prediction_ap_near_prevalence_and_lift_near_one():
    rng = np.random.default_rng(0)
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = rng.random((64, 64)).astype(np.float32)
    m = segmentation_metrics(prob, lab, mask)
    assert abs(m["average_precision"] - m["positive_rate"]) < 0.05
    assert abs(m["ap_prevalence_lift"] - 1.0) < 0.3
    assert 0.4 < m["roc_auc"] < 0.6


def test_paint_everything_is_not_rewarded():
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = np.ones((64, 64), np.float32)  # predict ink everywhere
    m = segmentation_metrics(prob, lab, mask)
    assert m["recall"] > 0.99
    assert m["pred_positive_rate"] > 0.99
    assert abs(m["ap_prevalence_lift"] - 1.0) < 0.3  # collapse not rewarded
    assert m["precision"] < 0.3


def test_degenerate_mask_returns_nan_with_note():
    lab = np.zeros((64, 64), np.uint8)  # no positives
    mask = np.ones((64, 64), bool)
    prob = np.random.default_rng(0).random((64, 64)).astype(np.float32)
    m = segmentation_metrics(prob, lab, mask)
    assert np.isnan(m["val_f1"])
    assert "note" in m


def test_metrics_by_threshold_length():
    lab = _label()
    mask = np.ones((64, 64), bool)
    prob = lab.astype(np.float32)
    m = segmentation_metrics(prob, lab, mask, thresholds=np.linspace(0.1, 0.9, 9))
    assert len(m["metrics_by_threshold"]) == 9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vesuvius_autoresearch.detector.metrics'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/vesuvius_autoresearch/detector/metrics.py
"""Community-aligned segmentation metrics for ink detection: threshold-swept F1 (primary),
average precision and prevalence-lift (honest, imbalance-robust gates), with ROC-AUC kept
only as a secondary diagnostic. Mask-restricted, pooled over the fragment."""
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

_DEGENERATE_KEYS = [
    "val_f1", "best_threshold", "f1_at_0.5", "val_f05", "precision", "recall",
    "pred_positive_rate", "average_precision", "ap_prevalence_lift", "roc_auc",
]


def _fbeta(precision, recall, beta):
    b2 = beta * beta
    denom = b2 * precision + recall
    return (1.0 + b2) * precision * recall / denom if denom > 0 else 0.0


def _confusion_at(p, y, t):
    pred = (p >= t).astype(np.uint8)
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall, int(pred.sum())


def segmentation_metrics(prob, label, mask, thresholds=None):
    if thresholds is None:
        thresholds = np.linspace(0.05, 0.95, 19)
    sel = np.asarray(mask).astype(bool)
    p = np.asarray(prob)[sel].astype(np.float64)
    y = (np.asarray(label)[sel] > 0.5).astype(np.uint8)
    n = int(y.size)
    pos = int(y.sum())
    positive_rate = pos / n if n else float("nan")
    card = {"positive_rate": positive_rate, "n_pixels": n}

    if pos == 0 or pos == n or n == 0:
        card.update({k: float("nan") for k in _DEGENERATE_KEYS})
        card["note"] = "degenerate: mask has no positive/negative contrast"
        card["metrics_by_threshold"] = []
        return card

    by_thr = []
    best = {"f1": -1.0, "threshold": 0.5, "precision": 0.0, "recall": 0.0,
            "pred_positive_rate": 0.0}
    best_f05 = -1.0
    for t in thresholds:
        precision, recall, pred_pos = _confusion_at(p, y, float(t))
        f1 = _fbeta(precision, recall, 1.0)
        f05 = _fbeta(precision, recall, 0.5)
        by_thr.append({"threshold": float(t), "precision": precision,
                       "recall": recall, "f1": f1, "f05": f05})
        if f1 > best["f1"]:
            best = {"f1": f1, "threshold": float(t), "precision": precision,
                    "recall": recall, "pred_positive_rate": pred_pos / n}
        best_f05 = max(best_f05, f05)

    pr_half, rc_half, _ = _confusion_at(p, y, 0.5)
    ap = float(average_precision_score(y, p))
    card.update({
        "val_f1": best["f1"],
        "best_threshold": best["threshold"],
        "f1_at_0.5": _fbeta(pr_half, rc_half, 1.0),
        "val_f05": best_f05,
        "precision": best["precision"],
        "recall": best["recall"],
        "pred_positive_rate": best["pred_positive_rate"],
        "average_precision": ap,
        "ap_prevalence_lift": ap / positive_rate if positive_rate > 0 else float("nan"),
        "roc_auc": float(roc_auc_score(y, p)),  # secondary diagnostic ONLY
        "metrics_by_threshold": by_thr,
    })
    return card
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_metrics.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/detector/metrics.py tests/test_detector_metrics.py
git commit --no-verify -m "feat(detector): community segmentation metrics (F1-swept primary, AP + prevalence-lift gates)"
```

---

### Task 2: Eval integration with backward-compat aliases

**Files:**
- Modify: `src/vesuvius_autoresearch/detector/eval.py` (replace `_pixel_auc`/`_youden_threshold`/`evaluate`)
- Modify: `tests/test_detector_eval.py` (extend existing tests)

**Interfaces:**
- Consumes: `segmentation_metrics` (Task 1).
- Produces: `evaluate(prob_map, label, mask, cfg, fragment_id="frag") -> dict` whose card contains the full metric contract plus `fragment_id`, plus backward-compat aliases `pixel_auc` (= `roc_auc`) and `threshold` (= `best_threshold`). Writes `<fragment_id>_scorecard.json`, `<fragment_id>_metrics_by_threshold.csv`, `<fragment_id>_pred_thumb.png` under `cfg.reports_dir`.

- [ ] **Step 1: Write the failing test (extend the eval test)**

Replace the entire contents of `tests/test_detector_eval.py` with:

```python
# tests/test_detector_eval.py
import os

import numpy as np

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector import eval as E


def test_perfect_pred_scores_f1_and_keeps_auc_alias(tmp_path):
    cfg = DetectorConfig(reports_dir=str(tmp_path))
    label = np.zeros((64, 64), np.uint8)
    label[20:40, 20:40] = 1
    mask = np.ones((64, 64), bool)
    prob = label.astype(np.float32)
    card = E.evaluate(prob, label, mask, cfg)
    assert card["val_f1"] > 0.99               # new primary metric
    assert abs(card["pixel_auc"] - 1.0) < 1e-6  # backward-compat alias (= roc_auc)
    assert 0.0 <= card["threshold"] <= 1.0      # backward-compat alias (= best_threshold)
    assert os.path.exists(os.path.join(str(tmp_path), "frag_metrics_by_threshold.csv"))


def test_chance_pred_scores_auc_near_half(tmp_path):
    cfg = DetectorConfig(reports_dir=str(tmp_path))
    rng = np.random.default_rng(0)
    label = (rng.random((64, 64)) > 0.5).astype(np.uint8)
    mask = np.ones((64, 64), bool)
    prob = rng.random((64, 64)).astype(np.float32)
    card = E.evaluate(prob, label, mask, cfg)
    assert 0.4 < card["pixel_auc"] < 0.6
    assert "average_precision" in card and "ap_prevalence_lift" in card
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_eval.py -v`
Expected: FAIL (current `evaluate` returns no `val_f1` / no CSV).

- [ ] **Step 3: Write minimal implementation**

Replace the entire contents of `src/vesuvius_autoresearch/detector/eval.py` with:

```python
# src/vesuvius_autoresearch/detector/eval.py
"""Evaluate a prediction with the community metric contract (F1-swept primary, AP +
prevalence-lift gates, ROC-AUC secondary), writing a scorecard, a per-threshold CSV, and a
thumbnail. Does NOT gate on skel_dist (FINDINGS.md Phase 4b)."""
import csv
import json
import os

import numpy as np
from PIL import Image

from .metrics import segmentation_metrics


def evaluate(prob_map, label, mask, cfg, fragment_id="frag"):
    os.makedirs(cfg.reports_dir, exist_ok=True)
    m = segmentation_metrics(prob_map, label, mask)
    by_thr = m.pop("metrics_by_threshold", [])
    card = {"fragment_id": fragment_id, **m}
    # Backward-compat aliases (cli.assert_auc / reproduce gate / older readers use these).
    card["pixel_auc"] = m.get("roc_auc", float("nan"))
    card["threshold"] = m.get("best_threshold", float("nan"))

    with open(os.path.join(cfg.reports_dir, f"{fragment_id}_metrics_by_threshold.csv"),
              "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["threshold", "precision", "recall", "f1", "f05"])
        writer.writeheader()
        for row in by_thr:
            writer.writerow(row)

    thumb = (np.clip(prob_map, 0, 1) * 255).astype(np.uint8)
    h, w = thumb.shape
    Image.fromarray(thumb).resize((max(1, w // 8), max(1, h // 8))).save(
        os.path.join(cfg.reports_dir, f"{fragment_id}_pred_thumb.png"))
    with open(os.path.join(cfg.reports_dir, f"{fragment_id}_scorecard.json"), "w") as f:
        json.dump(card, f, indent=2)
    return card
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_eval.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Confirm the CLI/reproduce path still works (alias regression)**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_cli.py -v`
Expected: PASS (3 passed) — `assert_auc` still reads `pixel_auc`.

- [ ] **Step 6: Commit**

```bash
git add src/vesuvius_autoresearch/detector/eval.py tests/test_detector_eval.py
git commit --no-verify -m "feat(detector): eval emits the F1/AP metric contract (pixel_auc/threshold kept as aliases)"
```

---

### Task 3: Cross-scroll measurement harness + CLI

**Files:**
- Create: `src/vesuvius_autoresearch/detector/measure.py`
- Modify: `src/vesuvius_autoresearch/detector/cli.py` (add a `measure` subcommand to `main`)
- Test: `tests/test_detector_measure.py`

**Interfaces:**
- Consumes: `infer` (existing), `read_image_mask` (existing), `segmentation_metrics` (Task 1), `DetectorConfig`.
- Produces:
  - `measure(cfg, checkpoint_path, targets, model=None) -> dict` mapping `fragment_id -> scorecard` (each scorecard includes `scroll_label` and the metric contract, minus `metrics_by_threshold`; a failed target maps to `{"scroll_label": ..., "error": str}`). Writes `reports/detector/cross_scroll_measurement.md` and `.json`. `targets` is a list of `(fragment_id, scroll_label)`.
  - `cli.main(["measure"])` runs the default same-scroll vs cross-scroll comparison on the epoch-7 checkpoint.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_detector_measure.py
import os

import numpy as np

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.model import DetectorModel
from vesuvius_autoresearch.detector import measure as M
from test_detector_data import _make_fake_fragment


def test_measure_writes_report_and_scores_targets(tmp_path):
    root = str(tmp_path / "scrolls")
    _make_fake_fragment(root, "PHercParis2Fr143", h=320, w=320)
    _make_fake_fragment(root, "20230702185753", h=320, w=320)
    cfg = DetectorConfig(data_root=root, reports_dir=str(tmp_path / "reports"))
    model = DetectorModel(cfg, pred_shape=(320, 320)).eval()
    targets = [("PHercParis2Fr143", "scroll2_same"), ("20230702185753", "scroll1_cross")]
    rows = M.measure(cfg, checkpoint_path=None, targets=targets, model=model)
    assert set(rows) == {"PHercParis2Fr143", "20230702185753"}
    assert "val_f1" in rows["PHercParis2Fr143"]
    assert rows["20230702185753"]["scroll_label"] == "scroll1_cross"
    assert os.path.exists(os.path.join(str(tmp_path / "reports"),
                                       "cross_scroll_measurement.md"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_measure.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vesuvius_autoresearch.detector.measure'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/vesuvius_autoresearch/detector/measure.py
"""No-retrain cross-scroll measurement: score one checkpoint across several fragments
(same-scroll vs cross-scroll) with the community metric contract and write a gap report."""
import json
import os

import numpy as np

from .data import read_image_mask
from .infer import infer
from .metrics import segmentation_metrics

_COLS = ["val_f1", "f1_at_0.5", "average_precision", "ap_prevalence_lift",
         "precision", "recall", "positive_rate", "roc_auc"]


def measure(cfg, checkpoint_path, targets, model=None):
    os.makedirs(cfg.reports_dir, exist_ok=True)
    rows = {}
    for fragment_id, scroll_label in targets:
        try:
            prob = infer(cfg, checkpoint_path, fragment_id, model=model)
            _, label, mask = read_image_mask(cfg, fragment_id)
            h, w = label.shape
            m = segmentation_metrics(prob[:h, :w], (label > 0.5).astype(np.uint8),
                                     mask[:h, :w].astype(bool))
            m.pop("metrics_by_threshold", None)
            m["scroll_label"] = scroll_label
            rows[fragment_id] = m
        except Exception as exc:  # keep going; record the failure
            rows[fragment_id] = {"scroll_label": scroll_label, "error": str(exc)}
    _write_report(cfg, checkpoint_path, rows)
    return rows


def _fmt(v):
    return f"{v:.4f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def _write_report(cfg, checkpoint_path, rows):
    lines = ["# Cross-Scroll Measurement", "",
             f"Checkpoint: `{checkpoint_path}`", "",
             "| fragment | scroll | " + " | ".join(_COLS) + " |",
             "|---|---|" + "|".join(["---"] * len(_COLS)) + "|"]
    for fid, m in rows.items():
        if "error" in m:
            lines.append(f"| {fid} | {m['scroll_label']} | ERROR: {m['error']} |")
            continue
        lines.append(f"| {fid} | {m.get('scroll_label','')} | "
                     + " | ".join(_fmt(m.get(c, float('nan'))) for c in _COLS) + " |")
    with open(os.path.join(cfg.reports_dir, "cross_scroll_measurement.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(cfg.reports_dir, "cross_scroll_measurement.json"), "w") as f:
        json.dump(rows, f, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_measure.py -v`
Expected: PASS (1 passed). Note: CPU TimeSformer inference over a 320×320 fragment runs in a few seconds per target.

- [ ] **Step 5: Add the `measure` CLI subcommand**

In `src/vesuvius_autoresearch/detector/cli.py`, inside `main(argv=None)`, add a parser and dispatch. After the line `sub.add_parser("train")` add:

```python
    p_measure = sub.add_parser("measure")
    p_measure.add_argument("--checkpoint", default="models/detector/detector_epoch=7.ckpt")
    p_measure.add_argument("--same", default="PHercParis2Fr143")
    p_measure.add_argument("--cross", default="20230702185753")
```

And in the dispatch chain (after the `elif args.cmd == "eval":` block) add:

```python
    elif args.cmd == "measure":
        from .measure import measure
        targets = [(args.same, "scroll2_same"), (args.cross, "scroll1_cross")]
        rows = measure(cfg, args.checkpoint, targets)
        for fid, m in rows.items():
            print(f"{fid} [{m.get('scroll_label')}]: "
                  f"val_f1={m.get('val_f1')} ap={m.get('average_precision')} "
                  f"lift={m.get('ap_prevalence_lift')}")
```

- [ ] **Step 6: Verify CLI parses (no-op help path)**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_cli.py -v`
Expected: PASS (3 passed) — existing CLI tests unaffected.

- [ ] **Step 7: Run the full detector suite**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py -q`
Expected: PASS (all detector tests green).

- [ ] **Step 8: Commit**

```bash
git add src/vesuvius_autoresearch/detector/measure.py src/vesuvius_autoresearch/detector/cli.py tests/test_detector_measure.py
git commit --no-verify -m "feat(detector): cross-scroll measurement harness + measure CLI"
```

---

### Task 4: Run the real cross-scroll measurement (manual, GPU)

**Files:** none (operational); produces `reports/detector/cross_scroll_measurement.{md,json}`.

This is the definition-of-done — run by a human on the GPU, NOT a unit test.

- [ ] **Step 1: Pause the autoresearch loop** (it shares the GPU).

Run:
```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 4; ps -eo pid,cmd | grep -E "run_autoresearch_loop|train.py --config" | grep -v grep || echo "(loop paused)"
```
Expected: `(loop paused)`; `nvidia-smi` shows the GPU free.

- [ ] **Step 2: Verify the cross-scroll segment's layer indices match the recipe.**

`read_image_mask` reads `layers/{i:02}.tif` for `i` in `[start_idx, end_idx) = [17, 43)`. Confirm the Scroll-1 segment uses the same naming:
```bash
ls villa/ink-detection/train_scrolls/20230702185753/layers/ | sort | head -3
ls villa/ink-detection/train_scrolls/20230702185753/layers/ | sort | tail -3
```
Expected: filenames `17.tif`…`42.tif`. If instead they are `00.tif`…`25.tif`, pass a matching config by editing the command in Step 3 to a fragment whose layers are `17..42`, or pick another timestamp segment with `17..42` (the PHercParis2 pair is `17..42`). Do not proceed with mismatched indices — it would read wrong/blank layers.

- [ ] **Step 3: Run the measurement.**

Run: `uv run python -m vesuvius_autoresearch.detector.cli measure`
Expected: prints two lines (same-scroll `scroll2_same` and cross-scroll `scroll1_cross`) with `val_f1`/`ap`/`lift`, and writes `reports/detector/cross_scroll_measurement.{md,json}`. Sanity-check: the same-scroll `val_f1` should be clearly above the cross-scroll one if a generalization gap exists; `ap_prevalence_lift` >> 1 indicates real signal, ≈1 indicates chance.

- [ ] **Step 4: Commit the measurement artifact.**

```bash
git add reports/detector/cross_scroll_measurement.md reports/detector/cross_scroll_measurement.json
git commit --no-verify -m "chore(detector): first honest cross-scroll measurement (same-scroll vs Scroll-1)"
```

- [ ] **Step 5: Resume the autoresearch loop.**

Run: `bash start.sh` then confirm `pgrep -f "python run_autoresearch_loop.py"` returns a PID and `.loop_paused` is gone.

- [ ] **Step 6: If the cross-scroll `val_f1`/`ap_prevalence_lift` is at chance (~lift 1.0),** that is a *finding*, not a bug — record it; it quantifies the cross-scroll gap the community is working on and motivates Sub-projects B/C. If a target errored on label/shape mismatch, that segment's labels are not aligned to its volume — pick a different aligned `train_scrolls` segment rather than forcing it.

---

## Self-Review

**Spec coverage:**
- Metric module (val_f1 primary; AP + prevalence-lift; ROC-AUC secondary; metrics_by_threshold; degenerate handling) → Task 1. ✓
- Eval integration + backward-compat aliases + CSV + thumbnail → Task 2. ✓
- Measurement harness (same-scroll vs cross-scroll, no retrain, existing epoch-7 ckpt) + CLI → Task 3. ✓
- First honest cross-scroll number committed → Task 4. ✓
- Tests (perfect/chance/paint-everything/degenerate; measure writes report) → Tasks 1 & 3; eval extended → Task 2. ✓
- Scope boundary (no retrain, no full-res model, no raw-fragment alignment) → respected; documented as follow-ups. ✓
- Isolation + loop-pause for GPU run → Task 4 Steps 1/5 + Global Constraints. ✓

**Placeholder scan:** No TBD/TODO; every code step is complete; commands have expected output. ✓

**Type consistency:** `segmentation_metrics(...) -> dict` keys used consistently by `evaluate` (Task 2) and `measure` (Task 3); `measure(cfg, checkpoint_path, targets, model=None)` signature matches its test and the CLI dispatch; `evaluate` retains `pixel_auc`/`threshold` aliases consumed by the unchanged `cli.assert_auc`. ✓

**Known follow-ups (out of scope):** full-res model (B); search loop (C); raw-fragment axis/label alignment (PHerc1667 etc.); retrain Scroll-1 → eval Scroll-2 as the headline.
