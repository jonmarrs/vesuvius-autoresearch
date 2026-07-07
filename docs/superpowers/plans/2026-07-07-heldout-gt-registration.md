# Held-Out Ground-Truth Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register the human hand label of held-out Scroll-1 segment `20231210121321` (no arm trained on it) onto SOTA geometry via the merged `warp_obj` pipeline, then score teacher + students + legacy against held-out ground truth.

**Architecture:** Parameterize `register_run.py` with a `TARGETS` dict + a `_set_target(key)` that rebinds the module-level path/segment globals before a subcommand runs, so every existing function body is unchanged and the slice-5 target (`orig`) stays byte-for-byte behavior-compatible. The operational run then invokes `probe/warp_obj/validate/score heldout`.

**Tech Stack:** Unchanged — scipy (`cKDTree`), numpy, opencv, tifffile, s3fs (anonymous); the detector subpackage for `score` inference.

## Global Constraints

- **No scoring against a misaligned label:** `score` refuses to run unless `validate` wrote the target's `VALIDATED` marker; thresholds are CLI args recorded in the report.
- **Framing:** every score row "vs registered ground truth" with method + residual inline; F1 led for the teacher comparison (teacher is binary); arm A tagged selection-caveated, arms B/C tagged clean held-out, teacher/legacy clean.
- **Slice-5 backward compatibility:** `python -m repro.sota_data.register_run <cmd>` (no target key) must behave exactly as before (target defaults to `orig`, same `reports/detector/registered_gt_validation.*` paths).
- Target (verbatim): held-out segment `20231210121321`, region `(4000,2500)` size 4096 at level 2; hand label `villa/ink-detection/train_scrolls/20231210121321/20231210121321_inklabels.png`; the SOTA fragment already on disk at `local_data/sota_distill/20231210121321_y4000_x2500` (Phase-2 `frag_id` naming); teacher tif from `PHercParis4/segments/20231210121321/ink-detection`.
- Isolation: `repro/sota_data/` + `tests/`; per-target working data under `local_data/sota_registration/<key>/` (git-ignored); reports under `reports/detector/`. No detector-code changes; no loop-file edits. Anonymous S3. No AI-authorship markers.
- Tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## File Structure

- Modify `repro/sota_data/register_run.py` — add `TARGETS`, `_set_target`, target-key dispatch; keep all function bodies unchanged (they read the rebindable globals).
- Test: `tests/test_sota_register_targets.py`.

---

### Task 1: Parameterize `register_run.py` with `TARGETS` + `_set_target`

**Files:**
- Modify: `repro/sota_data/register_run.py`
- Test: `tests/test_sota_register_targets.py`

**Interfaces:**
- Produces (in `register_run.py`):
  - `TARGETS: dict[str, dict]` keyed `"orig"` and `"heldout"`, each with `seg`, `region` (y0,x0,size), `frag_root`, `frag_id`, `old_root`, `report_md`, `report_json`.
  - `_set_target(key) -> None` — rebinds the module globals (`SEG`, `REG_DIR`, `REGION_L2`, `FRAG_ID`, `XSCROLL_ROOT`, `OLD_ROOT`, `MESH_NEW`, `OBJ_PATH`, `MARKER`, `REG_LABEL`, `REG_STATS`, `REPORT_MD`, `REPORT_JSON`) from `TARGETS[key]`; unknown key ⇒ `ValueError` naming the key. `REG_DIR` becomes per-target `local_data/sota_registration/<key>`.
  - `__main__` parses `sys.argv[1]` = subcommand, optional `sys.argv[2]` = target key (default `"orig"` if the 2nd arg is absent or starts with `-`); calls `_set_target(key)`; passes remaining args through to the subcommand (so `validate` still reads its `--max-*`/`--min-*` flags).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sota_register_targets.py
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath("."))  # repo root
from repro.sota_data import register_run as rr


def test_targets_has_both_keys():
    assert set(rr.TARGETS) == {"orig", "heldout"}
    assert rr.TARGETS["orig"]["seg"] == "20230702185753"
    assert rr.TARGETS["heldout"]["seg"] == "20231210121321"


def test_set_target_orig_keeps_slice5_paths():
    rr._set_target("orig")
    assert rr.SEG == "20230702185753"
    assert rr.REPORT_MD == "reports/detector/registered_gt_validation.md"
    assert rr.FRAG_ID == "scroll1_20230702185753_y4000_x2500"
    assert rr.XSCROLL_ROOT == "local_data/sota_xscroll"


def test_set_target_heldout_distinct():
    rr._set_target("heldout")
    assert rr.SEG == "20231210121321"
    assert rr.FRAG_ID == "20231210121321_y4000_x2500"
    assert rr.XSCROLL_ROOT == "local_data/sota_distill"
    assert rr.REPORT_MD == "reports/detector/registered_gt_heldout_validation.md"
    assert rr.OLD_ROOT.endswith("train_scrolls/20231210121321")
    assert rr.MESH_NEW.startswith("20231210121321-on-")
    assert rr.OBJ_PATH.endswith("20231210121321_original.obj")
    # per-target working dir isolates fetched meshes / outputs
    assert rr.REG_DIR == "local_data/sota_registration/heldout"
    assert rr.MARKER == os.path.join(rr.REG_DIR, "VALIDATED")
    # restore default so other tests/imports see slice-5 behavior
    rr._set_target("orig")


def test_set_target_unknown_raises():
    with pytest.raises(ValueError, match="nosuch"):
        rr._set_target("nosuch")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_register_targets.py -v`
Expected: FAIL with `AttributeError: module ... has no attribute 'TARGETS'`.

- [ ] **Step 3: Implement**

In `repro/sota_data/register_run.py`, **replace the constants block** (from `SEG = "20230702185753"` through the `CKPTS = [...]` list — i.e. every module-level assignment between the imports and `def _mesh_path`) with the following. `CKPTS`, `LEVEL0_SHAPE`, and the mesh-name templates are target-independent and stay; the per-target names are set by `_set_target`:

```python
LEVEL0_SHAPE = (50600, 36400)   # SOTA surface level-0 (verified)
CKPTS = [
    ("legacy detector", "models/detector/detector_epoch=7.ckpt"),
    ("arm A (1-scroll student)", "models/detector_sota_distill/detector_epoch=9.ckpt"),
    ("arm B (2-scroll student)", "models/detector_xscroll/detector_epoch=7.ckpt"),
    ("arm C (3-scroll student)", "models/detector_xscroll_c/detector_epoch=11.ckpt"),
]
# Segments carrying all three registration inputs (hand label + original.obj + canon
# teacher). "orig" = slice-5 (a TRAIN region for all students); "heldout" = arm-A
# validated but trained by NObody (arms B/C fully clean).
TARGETS = {
    "orig": {
        "seg": "20230702185753", "region": (4000, 2500, 4096),
        "frag_root": "local_data/sota_xscroll",
        "frag_id": "scroll1_20230702185753_y4000_x2500",
        "old_root": "villa/ink-detection/train_scrolls/20230702185753",
        "report_md": "reports/detector/registered_gt_validation.md",
        "report_json": "reports/detector/registered_gt_validation.json",
    },
    "heldout": {
        "seg": "20231210121321", "region": (4000, 2500, 4096),
        "frag_root": "local_data/sota_distill",
        "frag_id": "20231210121321_y4000_x2500",
        "old_root": "villa/ink-detection/train_scrolls/20231210121321",
        "report_md": "reports/detector/registered_gt_heldout_validation.md",
        "report_json": "reports/detector/registered_gt_heldout_validation.json",
    },
}

# module globals rebound by _set_target (declared here so references resolve at import)
SEG = REG_DIR = OLD_ROOT = MESH_OLD = MESH_NEW = OBJ_PATH = None
REGION_L2 = FRAG_ID = XSCROLL_ROOT = None
MARKER = REG_LABEL = REG_STATS = REPORT_MD = REPORT_JSON = None


def _set_target(key):
    global SEG, REG_DIR, OLD_ROOT, MESH_OLD, MESH_NEW, OBJ_PATH, REGION_L2
    global FRAG_ID, XSCROLL_ROOT, MARKER, REG_LABEL, REG_STATS, REPORT_MD, REPORT_JSON
    if key not in TARGETS:
        raise ValueError(f"unknown registration target '{key}'; known: {sorted(TARGETS)}")
    t = TARGETS[key]
    SEG = t["seg"]
    REGION_L2 = t["region"]
    FRAG_ID = t["frag_id"]
    XSCROLL_ROOT = t["frag_root"]
    OLD_ROOT = t["old_root"]
    REPORT_MD = t["report_md"]
    REPORT_JSON = t["report_json"]
    REG_DIR = os.path.join("local_data/sota_registration", key)
    MESH_OLD = "intermediate/tifxyz_original"          # the 2023 label parameterization
    MESH_NEW = f"{SEG}-on-20230205180739-7.91um.tifxyz"  # new UV domain, old-scan frame
    OBJ_PATH = os.path.join(REG_DIR, f"{SEG}_original.obj")
    MARKER = os.path.join(REG_DIR, "VALIDATED")
    REG_LABEL = os.path.join(REG_DIR, "registered_label_l2region.png")
    REG_STATS = os.path.join(REG_DIR, "registration_stats.json")


_set_target("orig")  # import-time default = slice-5 behavior
```

Then change the `__main__` block at the end of the file from:

```python
if __name__ == "__main__":
    cmds = {"probe": cmd_probe, "warp": cmd_warp, "warp_obj": cmd_warp_obj,
            "validate": cmd_validate, "score": cmd_score}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.register_run {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
```

to:

```python
if __name__ == "__main__":
    cmds = {"probe": cmd_probe, "warp": cmd_warp, "warp_obj": cmd_warp_obj,
            "validate": cmd_validate, "score": cmd_score}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.register_run "
                 f"{{{'|'.join(cmds)}}} [orig|heldout] [--flags]")
    # optional target key as argv[2] (absent or a --flag => default 'orig');
    # strip it so cmd_validate's argparse (which reads sys.argv[2:]) is unaffected.
    key = "orig"
    if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
        key = sys.argv[2]
        del sys.argv[2]
    _set_target(key)
    cmds[sys.argv[1]]()
```

Note: `cmd_validate` reads flags via `sys.argv[2:]`; deleting the target key at `argv[2]` (when present) keeps `--max-median-residual`/`--min-enrichment` at `argv[2:]` exactly as before.

- [ ] **Step 4: Run tests + slice-5 usage regression**

Run:
```bash
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_register_targets.py tests/test_sota_register.py -v
CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.register_run 2>&1 | tail -1
```
Expected: all tests PASS (4 new + 8 geometry); usage line prints `... {probe|warp|warp_obj|validate|score} [orig|heldout] [--flags]`, no import errors.

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/register_run.py tests/test_sota_register_targets.py
git commit --no-verify -m "feat(sota): parameterize register_run with TARGETS (orig/heldout); slice-5 default unchanged"
```

---

### Task 2: Operational run — held-out ground-truth registration (manual, network + GPU)

**Files:** none (operational); produces `reports/detector/registered_gt_heldout_validation.{md,json}` + overlays, or an honest documented negative.

- [ ] **Step 1: Confirm the held-out SOTA fragment is on disk.**

Run: `ls local_data/sota_distill/20231210121321_y4000_x2500/layers/30.tif local_data/sota_distill/20231210121321_y4000_x2500/*_inklabels.png`
Expected: both exist (Phase-2 prepped this as arm A's held-out fragment). If missing, regenerate it: `uv run python -m repro.sota_data.distill_run prep` (re-preps the Phase-2 fragments incl. the held-out region) — then re-check.

- [ ] **Step 2: Probe (network, CPU).**

Run: `uv run python -m repro.sota_data.register_run probe heldout`
Expected: the `20231210121321` mesh dir listing + meta.json + grid/range for `intermediate/tifxyz_original` and the `on-7.91um` tifxyz. If a mesh fails to parse, STOP and report — that is the negative-finding path.

- [ ] **Step 3: Warp (CPU, minutes).**

Run: `uv run python -m repro.sota_data.register_run warp_obj heldout`
Expected: per-convention enrichment lines, a chosen convention, 3D residual (median expected ~single-digit old-scan voxels as in slice 5), and a plausible registered ink fraction (~0.05–0.3). If the best enrichment is ≈1 (no convention separates), the bridge mislanded — treat as a Stage-2 negative and report.

- [ ] **Step 4: Validate (the gate).**

Run: `uv run python -m repro.sota_data.register_run validate heldout --max-median-residual 12 --min-enrichment 3.0`
Expected: overlays written under `local_data/sota_registration/heldout/`; `VALIDATION PASSED ... marker written` or `FAILED`. **Inspect `overlay_label_on_teacher.png` and `overlay_label_on_sota.png` visually** — red strokes must track letterforms. If FAILED, commit the stats + overlays + a short negative writeup (a legitimate deliverable) and stop.

- [ ] **Step 5: Score (GPU; pause the loop).**

```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 5
uv run python -m repro.sota_data.register_run score heldout
```
Expected: five rows (canon teacher + 4 checkpoints) vs **held-out** registered ground truth, written to `reports/detector/registered_gt_heldout_validation.{md,json}`. **Read it:** do arms B/C (the clean held-out rows) hold their ground-truth quality vs the teacher's F1, or drop? That is the confound-free answer the slice-5 result couldn't give. Confirm the report tags arm A as selection-caveated and leads the teacher comparison with F1.

- [ ] **Step 6: Copy a committable overlay; commit; resume the loop.**

```bash
cp local_data/sota_registration/heldout/overlay_label_on_teacher.png reports/detector/registered_gt_heldout_overlay.png
git add reports/detector/registered_gt_heldout_validation.md reports/detector/registered_gt_heldout_validation.json reports/detector/registered_gt_heldout_overlay.png
git commit --no-verify -m "chore(sota): held-out ground-truth scores on SOTA data (segment 20231210121321)"
bash start.sh
```
Expected: loop resumes. Record the verdict honestly either way; no blind re-tuning.

---

## Self-Review

**Spec coverage:** parameterized `register_run` with `TARGETS`/`_set_target`, slice-5 backward-compatible (T1) ✓; held-out target `20231210121321` region (4000,2500), fragment on disk at `local_data/sota_distill` (T1 config + T2 S1) ✓; same validated `probe/warp_obj/validate/score` pipeline (T2) ✓; mandatory gate before scoring, marker-guarded (reused unchanged, per-target marker via `_set_target`) ✓; report leads F1 for teacher, arm-A selection caveat + binary-teacher caveat (already in the committed `cmd_score` prose from slice 5 — unchanged, applies to both targets) ✓; one segment/region, no training ✓; unit test for config + dispatch + unknown-key (T1) ✓.

**Placeholder scan:** none; all code complete; the gate thresholds in T2 S4 are the slice-5-proven values (median-residual 12, enrichment 3.0) with the same visual-inspection backstop. ✓

**Type consistency:** `_set_target(key)` rebinds exactly the globals every function body already reads (`SEG`, `REG_DIR`, `REGION_L2`, `FRAG_ID`, `XSCROLL_ROOT`, `OLD_ROOT`, `MESH_OLD`, `MESH_NEW`, `OBJ_PATH`, `MARKER`, `REG_LABEL`, `REG_STATS`, `REPORT_MD`, `REPORT_JSON`); `TARGETS[*]` keys (`seg`/`region`/`frag_root`/`frag_id`/`old_root`/`report_md`/`report_json`) all consumed in `_set_target`; `cmd_validate`'s `sys.argv[2:]` flag parse preserved by deleting the (optional) target key before dispatch; `CKPTS` best-epoch paths match the committed models (legacy e7 / A e9 / B e7 / C e11). ✓

**Known follow-ups:** cross-scroll domain-ceiling blocked on released human 1667 labels; held-out labels as fine-tuning data; July filing refresh.
