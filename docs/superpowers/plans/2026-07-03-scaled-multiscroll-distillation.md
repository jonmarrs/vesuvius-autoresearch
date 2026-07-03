# Scaled Multi-Scroll Distillation (Arm C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train arm C — the unchanged TimeSformer recipe distilled on 6 regions across 3 scrolls (Scroll 1, PHerc 0139, PHerc 0172) — and measure it on the same held-out PHerc-1667 region against the committed arm history (baseline / A / B).

**Architecture:** One registry line in `distill_run.py` (`pherc0172`), then arm-C machinery in `xscroll_run.py`: `TRAIN_C`/`SECONDARY_0172_HELD`/`MODEL_DIR_C` constants, a shared `_prep_targets` helper (used by both the existing `cmd_prep` and the new `cmd_prep_c`, with provenance merging), a `model_dir`-parameterized `_best_epoch`, and `prep_c`/`train_c`/`measure_c` subcommands. `measure_c` cites the committed arm-B report's numbers instead of re-inferring them.

**Tech Stack:** Unchanged — s3fs (anonymous), zarr, tifffile, opencv, numpy; `vesuvius_autoresearch.detector` config-only.

## Global Constraints

- **All metrics "agreement with teacher"**; per-scroll teacher provenance persisted (merged across preps); the report states BOTH the capability-run confound (arm C differs from B in diversity *and* volume) and the selection-set caveat with the **legacy-baseline comparison as the asymmetry-free anchor**.
- Registry entry verbatim: `"pherc0172": "PHerc0172"`. Student via unchanged `detector.train` (config-only). Anonymous S3.
- The reviewed arm-B code paths (`prep`/`baselines`/`train`/`measure`) must keep working (the shared-helper refactor of `cmd_prep` must not change its behavior).
- `measure_c` requires the committed `reports/detector/cross_scroll_distill.json` (loud `ValueError` if missing) and cites its baseline/armA/armB numbers rather than re-running inference.
- Isolation: `repro/sota_data/` + `tests/` + `reports/detector/` + `local_data/` (git-ignored). No `run_autoresearch_loop.py`/`scripts/training/train.py` edits. No AI-authorship markers.
- Tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## File Structure

- Modify `repro/sota_data/distill_run.py` — one `SCROLLS` line.
- Modify `repro/sota_data/xscroll_run.py` — arm-C constants, `_prep_targets` helper, `_best_epoch(fid, model_dir=...)`, `cmd_prep_c`/`cmd_train_c`/`cmd_measure_c`, `__main__` dispatch.
- Modify `tests/test_sota_xscroll.py` — registry expectations.

---

### Task 1: Registry entry + arm-C machinery

**Files:**
- Modify: `repro/sota_data/distill_run.py` (SCROLLS)
- Modify: `repro/sota_data/xscroll_run.py`
- Modify: `tests/test_sota_xscroll.py`

**Interfaces:**
- Consumes: everything already in `distill_run`/`xscroll_run` (registry helpers, `_measure(ckpt, fid, data_root=)`, `prep_distill_fragment`, `teacher_region_for`).
- Produces: `SCROLLS` gains `pherc0172`; `xscroll_run` gains `TRAIN_C: list[tuple]` (6 targets), `SECONDARY_0172_HELD: tuple`, `MODEL_DIR_C="models/detector_xscroll_c"`, `_prep_targets(targets) -> dict` (preps fragments, returns provenance dict), `_best_epoch(fid, model_dir=MODEL_DIR)`, and subcommands `prep_c`/`train_c`/`measure_c`.

- [ ] **Step 0: Resolve the three PHerc-0172 segment ids (deterministic discovery)**

Run: `timeout 120 uv run python -m repro.sota_data.discover PHerc0172/segments 2>&1 | sed 's#.*/segments/##' | sort | head -3`
Record the three ids printed, in order, as `SEG_0172_A`, `SEG_0172_B`, `SEG_0172_C`. Use them verbatim in Step 3's constants (A and B are training regions; C is the secondary held-out). This is a live-bucket read; if it errors on network, stop and report.

- [ ] **Step 1: Write the failing test (update registry expectations)**

In `tests/test_sota_xscroll.py`, replace the two functions `test_scroll_registry_keys` and `test_scroll_prefix_builds_bucket_paths` with:

```python
def test_scroll_registry_keys():
    assert SCROLLS == {"scroll1": "PHercParis4", "pherc0139": "PHerc0139",
                       "pherc1667": "PHerc1667", "pherc0172": "PHerc0172"}


def test_scroll_prefix_builds_bucket_paths():
    assert _scroll_prefix("scroll1", "segA", "ink-detection") == \
        f"{BUCKET}/PHercParis4/segments/segA/ink-detection"
    assert _scroll_prefix("pherc0139", "segB", "surface-volumes") == \
        f"{BUCKET}/PHerc0139/segments/segB/surface-volumes"
    assert _scroll_prefix("pherc1667", "segC", "surface-volumes") == \
        f"{BUCKET}/PHerc1667/segments/segC/surface-volumes"
    assert _scroll_prefix("pherc0172", "segD", "ink-detection") == \
        f"{BUCKET}/PHerc0172/segments/segD/ink-detection"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_xscroll.py -v`
Expected: `test_scroll_registry_keys` and `test_scroll_prefix_builds_bucket_paths` FAIL (registry lacks `pherc0172`); the other two still pass.

- [ ] **Step 3: Implement**

(a) In `repro/sota_data/distill_run.py`, inside `SCROLLS`, add after the `"pherc1667"` line:

```python
    "pherc0172": "PHerc0172",
```

(b) In `repro/sota_data/xscroll_run.py`, immediately after the `SECONDARY_0139_HELD = (...)` line, add (substituting the Step-0 ids):

```python
# Arm C (capability run): 3 scrolls x 2 regions. Differs from arm B in BOTH diversity
# (+pherc0172) and volume (6 vs 4 regions) -- stated in the report.
TRAIN_C = TRAIN + [
    ("pherc0172", "SEG_0172_A", 4000, 2500),
    ("pherc0172", "SEG_0172_B", 4000, 2500),
]
SECONDARY_0172_HELD = ("pherc0172", "SEG_0172_C", 4000, 2500)
MODEL_DIR_C = "models/detector_xscroll_c"
SCALE_REPORT_MD = "reports/detector/cross_scroll_scale.md"
SCALE_REPORT_JSON = "reports/detector/cross_scroll_scale.json"
```

(c) Refactor `cmd_prep` into a shared helper. Replace the entire existing `cmd_prep` function with:

```python
def _prep_targets(targets):
    """Prep detector-format fragments for (scroll_key, seg, y0, x0) targets; return the
    per-teacher provenance dict for the teachers touched."""
    provenance = {}
    teachers = {}
    for (scroll_key, seg, y0, x0) in targets:
        key = (scroll_key, seg)
        if key not in teachers:
            tpath = dr.fetch_teacher(seg, scroll_key=scroll_key)
            teachers[key] = tifffile.imread(tpath)
            t = teachers[key]
            print(f"{scroll_key}/{seg}: teacher shape={t.shape} dtype={t.dtype} "
                  f"range=[{t.min()},{t.max()}]", flush=True)
            provenance[f"{scroll_key}/{seg}"] = {
                "shape": list(t.shape), "dtype": str(t.dtype),
                "min": int(t.min()), "max": int(t.max()),
            }
        region, level_shape, box = dr.extract_region(seg, y0, x0, scroll_key=scroll_key)
        t_region = teacher_region_for(teachers[key], level_shape, box)
        fid = _fid((scroll_key, seg, y0, x0))
        out = prep_distill_fragment(region, t_region, DATA_ROOT, fid)
        lab = cv2.imread(os.path.join(out, f"{fid}_inklabels.png"), 0)
        print(f"prepped {out} teacher-positive={float((lab > 0).mean()):.3f}", flush=True)
    return provenance


def _write_provenance(provenance):
    """Merge new teacher provenance into DATA_ROOT/teacher_provenance.json."""
    os.makedirs(DATA_ROOT, exist_ok=True)
    path = os.path.join(DATA_ROOT, "teacher_provenance.json")
    merged = {}
    if os.path.exists(path):
        with open(path) as f:
            merged = json.load(f).get("teachers", {})
    merged.update(provenance)
    with open(path, "w") as f:
        json.dump({"binarize_threshold": 128,
                   "note": "teacher = released canon model prediction, binarized at >=128 "
                           "after uint8 scaling; NOT ground truth",
                   "teachers": merged}, f, indent=2)


def cmd_prep():
    provenance = _prep_targets(TRAIN + [HELD, SECONDARY_0139_HELD])
    _write_provenance(provenance)


def cmd_prep_c():
    held_dir = os.path.join(DATA_ROOT, _fid(HELD))
    if not os.path.isdir(held_dir):
        raise ValueError(f"{held_dir} missing; run the arm-B `prep` step first "
                         "(the held-out 1667 fragment is shared)")
    provenance = _prep_targets(TRAIN_C + [SECONDARY_0172_HELD])
    _write_provenance(provenance)
```

(d) Parameterize `_best_epoch`: change its signature line from `def _best_epoch(fid):` to
`def _best_epoch(fid, model_dir=MODEL_DIR):` and, inside it, replace both occurrences of
`MODEL_DIR` with `model_dir` (the glob line and the error message).

(e) Add `cmd_train_c` and `cmd_measure_c` after the existing `cmd_measure`:

```python
def cmd_train_c():
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.train import train
    cfg = DetectorConfig(data_root=DATA_ROOT, model_dir=MODEL_DIR_C,
                         train_fragment_ids=[_fid(t) for t in TRAIN_C],
                         valid_fragment_id=_fid(HELD))
    print(train(cfg))


def cmd_measure_c():
    held_fid = _fid(HELD)
    if not os.path.exists(REPORT_JSON):
        raise ValueError(f"{REPORT_JSON} missing; the committed arm-B report is required "
                         "(its baseline/armA/armB numbers are cited, not re-run)")
    with open(REPORT_JSON) as f:
        prior = json.load(f)
    m_c, ck_c, prob_c = _best_epoch(held_fid, model_dir=MODEL_DIR_C)

    Image.fromarray((np.clip(prob_c, 0, 1) * 255).astype(np.uint8)).resize(
        (prob_c.shape[1] // 4, prob_c.shape[0] // 4)).save(
        "reports/detector/xscroll_armC_1667.png")

    sec = {}
    m, _ = dr._measure(ck_c, _fid(SECONDARY_0172_HELD), data_root=DATA_ROOT)
    sec["armC_on_held0172"] = m
    m, _ = dr._measure(ck_c, _fid(SECONDARY_0139_HELD), data_root=DATA_ROOT)
    sec["armC_on_held0139"] = m
    m, _ = dr._measure(ck_c, dr.frag_id(dr.HELD_SEG, *dr.HELD_REGION),
                       data_root=dr.DATA_ROOT)
    sec["armC_on_heldScroll1_phase2"] = m

    prov = None
    prov_path = os.path.join(DATA_ROOT, "teacher_provenance.json")
    if os.path.exists(prov_path):
        with open(prov_path) as f:
            prov = json.load(f)

    def row(label, m):
        return f"| {label} | " + " | ".join(
            f"{m.get(c, float('nan')):.4f}" for c in COLS) + " |"

    on1667 = prior["on_held_1667"]
    lines = ["# Scaled multi-scroll distillation (arm C) on held-out PHerc 1667", "",
             "**All metrics are agreement-with-teacher (the released canon predictions), "
             "NOT ground-truth accuracy.** No arm trained on any PHerc-1667 data. Arm C is a "
             "**capability run**: it differs from arm B in BOTH training-scroll diversity "
             "(+PHerc0172) and data volume (6 vs 4 regions) -- it is not a single-variable "
             "experiment. Caveat: the held-out region serves as the best-epoch selection set "
             "for arms B and C (not for arm A or the legacy baseline) -- the asymmetry-free "
             "anchor is the **arm-vs-legacy-baseline** comparison. Baseline/A/B rows are "
             "cited from the committed cross_scroll_distill.json, not re-run.", ""]
    if prov is not None:
        lines += ["Teacher provenance: " + "; ".join(
            f"`{s}` {p['dtype']} range [{p['min']},{p['max']}]"
            for s, p in prov["teachers"].items())
            + f". Labels binarized at >= {prov['binarize_threshold']} after uint8 scaling.",
            ""]
    lines += [f"Held-out: `{held_fid}`  |  arm C best ckpt: `{os.path.basename(ck_c)}`", "",
              "| model (on held-out 1667) | " + " | ".join(COLS) + " |",
              "|---|" + "|".join(["---"] * len(COLS)) + "|",
              row("legacy detector (cited)", on1667["baseline"]),
              row("arm A: 1 scroll, 4 regions (cited)", on1667["armA"]),
              row("arm B: 2 scrolls, 4 regions (cited)", on1667["armB"]),
              row("arm C: 3 scrolls, 6 regions", m_c),
              "", "Secondary (arm C same-scroll read-outs):", "",
              "| model / fragment | " + " | ".join(COLS) + " |",
              "|---|" + "|".join(["---"] * len(COLS)) + "|",
              row("arm C on held-out PHerc-0172 region", sec["armC_on_held0172"]),
              row("arm C on held-out PHerc-0139 region", sec["armC_on_held0139"]),
              row("arm C on Phase-2 held-out Scroll-1 region",
                  sec["armC_on_heldScroll1_phase2"]),
              "", "Renders (held-out 1667): [arm C](xscroll_armC_1667.png) | "
              "[arm B](xscroll_armB_1667.png) | [arm A](xscroll_armA_1667.png) | "
              "[teacher](xscroll_teacher_1667.png)."]
    with open(SCALE_REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(SCALE_REPORT_JSON, "w") as f:
        json.dump({"held_out": held_fid, "armC_best_checkpoint": os.path.basename(ck_c),
                   "on_held_1667": {**on1667, "armC": m_c},
                   "secondary_armC": sec,
                   "cited_from": "reports/detector/cross_scroll_distill.json",
                   "teacher_provenance": prov},
                  f, indent=2, default=float)
    print(f"ARM C vs teacher on held-out 1667: val_f1={m_c.get('val_f1', float('nan')):.4f} "
          f"(armB {on1667['armB'].get('val_f1', float('nan')):.4f}, "
          f"armA {on1667['armA'].get('val_f1', float('nan')):.4f}, "
          f"baseline {on1667['baseline'].get('val_f1', float('nan')):.4f})", flush=True)
```

(f) In the `__main__` block, extend the `cmds` dict to:

```python
    cmds = {"prep": cmd_prep, "baselines": cmd_baselines, "train": cmd_train,
            "measure": cmd_measure, "prep_c": cmd_prep_c, "train_c": cmd_train_c,
            "measure_c": cmd_measure_c}
```

- [ ] **Step 4: Run tests + usage checks to verify**

Run:
```bash
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_xscroll.py tests/test_sota_distill_prep.py -v
CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.xscroll_run 2>&1 | tail -1
CUDA_VISIBLE_DEVICES="" uv run python -m repro.sota_data.distill_run 2>&1 | tail -1
```
Expected: all tests PASS; `xscroll_run` usage line now lists `{prep|baselines|train|measure|prep_c|train_c|measure_c}`; `distill_run` usage unchanged. No import errors.

- [ ] **Step 5: Commit**

```bash
git add repro/sota_data/distill_run.py repro/sota_data/xscroll_run.py tests/test_sota_xscroll.py
git commit --no-verify -m "feat(sota): arm C -- pherc0172 registry entry + scaled 3-scroll distillation machinery"
```

---

### Task 2: Operational run — the scaled experiment (manual, network + GPU)

**Files:** none (operational); produces `reports/detector/cross_scroll_scale.{md,json}` + `xscroll_armC_1667.png`.

Run by a human. Definition-of-done.

- [ ] **Step 1: Prep (network; loop may keep running).**

Run: `uv run python -m repro.sota_data.xscroll_run prep_c`
Expected: PHerc-0172 teachers download for the first time (provenance printed + merged into the provenance json); 7 fragments prepped (the 4 arm-B train fragments re-prep idempotently). **Check:** every teacher-positive in the 0.02–0.4 band; adjust the 0172 entries' offsets (constants in `xscroll_run.py`) and re-run if degenerate, committing the adjustment. If the held-1667 fragment is missing it fails loudly — run `prep` first.

- [ ] **Step 2: Pause the loop; train arm C (~15–20 h GPU).**

Run:
```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 4
nohup uv run python -m repro.sota_data.xscroll_run train_c > reports/detector/xscroll_train_c.log 2>&1 &
```
Expected: 12 epochs over 6 fragments, checkpoints in `models/detector_xscroll_c/`. Roughly 1.5× arm B's epoch time.

- [ ] **Step 3: Measure.**

Run: `uv run python -m repro.sota_data.xscroll_run measure_c`
Expected: per-epoch lines, then `ARM C vs teacher on held-out 1667: val_f1=… (armB …, armA …, baseline …)`; writes `cross_scroll_scale.{md,json}` + the arm-C render. **Read the verdict:** C > B ⇒ scaling keeps improving unseen-scroll transfer; C ≈ B ⇒ saturation at this recipe/scale. Check the secondaries for same-scroll costs.

- [ ] **Step 4: Commit and resume the loop.**

```bash
git add reports/detector/cross_scroll_scale.md reports/detector/cross_scroll_scale.json \
        reports/detector/xscroll_armC_1667.png
git commit --no-verify -m "chore(sota): arm C scaled multi-scroll distillation result (held-out PHerc 1667)"
bash start.sh
```
Expected: loop resumes. Record the verdict honestly either way; no blind re-tuning.

---

## Self-Review

**Spec coverage:** registry entry (T1a) ✓; arm-C constants/machinery with minimal churn to reviewed paths (`_prep_targets` refactor keeps `cmd_prep` behavior; `_best_epoch` parameterized) (T1c–f) ✓; cites committed arm-B numbers with loud prereq guard (T1e) ✓; capability-confound + selection-caveat + baseline-anchor wording in the report (T1e `lines`) ✓; provenance merged across preps (T1c `_write_provenance`) ✓; four-row table + secondaries incl. held-0172 + renders (T1e) ✓; sanity-band + degenerate rule + loop pause + verdict reading (T2) ✓; tests updated (T1 Step 1) ✓.

**Placeholder scan:** `SEG_0172_A/B/C` are resolved by Task 1 Step 0's deterministic discovery command before the constants are written — a documented resolution procedure with an exact command, not a TBD. All code complete. ✓

**Type consistency:** `_prep_targets(targets) -> dict` consumed by both `cmd_prep` and `cmd_prep_c`; `_best_epoch(fid, model_dir=MODEL_DIR)` called with `model_dir=MODEL_DIR_C` in `cmd_measure_c` and default-compatible with the existing `cmd_measure` call; `prior["on_held_1667"]` keys (`baseline`/`armA`/`armB`) match what `cmd_measure` writes to `REPORT_JSON`; `dr.*` symbols all exist in the committed `distill_run.py`. ✓

**Known follow-ups:** periodic bucket re-sweep for new teacher scrolls; checkpoint pruning (3×12 ckpts after this run); July filing refresh.
