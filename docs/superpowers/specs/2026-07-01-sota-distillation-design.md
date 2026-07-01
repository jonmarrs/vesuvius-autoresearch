# Phase 2: Distill the Detector onto SOTA Data — Design

**Status:** Approved design (brainstorming). Second slice of the "rebase on SOTA capabilities" pivot
(follows the evaluate-only slice, `2026-07-01-rebase-detector-sota-data-design.md`).

## Context & motivation

The evaluate-only slice established two facts about the open SOTA data
(`s3://vesuvius-challenge-open-data/`):

1. **No ground-truth ink labels exist in the bucket at all.** Verified by discovery:
   `PHercParis4/segments/*/ink-detection/` holds only model predictions
   (`…new_canon_autoresearch_recipe…tif`), `PHercParis4/representations/` holds only
   `predictions`, and the `PHercParis2Fr47`/`Fr143` bucket entries hold only `photos/`. Our old
   hand labels do not align to the SOTA re-flattened geometry (old aspect ≈ 0.78 vs new ≈ 1.39).
2. **Our detector, run cross-scroll on the SOTA surface volumes, produces texture, not ink**
   (qualitative render; consistent with the measured weak cross-scroll transfer, lift ≈ 1.3).
   Better data alone does not rescue a model trained on a different distribution.

The path to a SOTA-native detector on our hardware is therefore **teacher–student distillation**:
train our detector on the SOTA surface volumes using the released canon predictions — produced by
the pipeline that actually read the scrolls — as targets.

## Honesty framing (binding)

- All supervision comes from the released `new_canon_autoresearch_recipe` prediction tifs
  (the **teacher**). Every reported metric is explicitly labeled **"agreement with teacher"** —
  never presented as ground-truth accuracy. Report filenames and headers carry this framing.
- Registering old hand labels onto the new flattening (real ground truth) is a **deferred
  follow-up**, out of scope here.

## Goals / success criteria

1. **Baseline:** measure the current detector's (`models/detector/detector_epoch=7.ckpt`)
   agreement-with-teacher on a held-out SOTA segment region (expected near-chance, per the
   qualitative result).
2. **Distill:** train the detector (proven TimeSformer recipe, unchanged) on teacher-labeled
   regions from two SOTA segments.
3. **Success = the distilled model's held-out agreement-with-teacher (A's metric contract:
   `val_f1` primary, AP + prevalence-lift gates) substantially exceeds the baseline's**, plus a
   side-by-side render (ours vs teacher) for qualitative sanity. Either direction is a finding;
   no blind re-tuning.

## Non-goals (scope boundary)

- **Scroll 1 (PHerc Paris 4) only.** No PHerc 1667/139, no multi-scroll (that is the next slice).
- **No label registration** (deferred follow-up).
- **No new architecture and no detector-code changes** — the student is the existing TimeSformer
  recipe via `detector.train`; data prep produces the detector's exact input format.
- **No loop integration** (Sub-project C).
- Teacher predictions used as released (binarized at a documented threshold, or soft if the tif is
  continuous — decided by inspecting the released tif at prep time and recorded in the report).

## Data slice

From `PHercParis4/segments/` (exact availability confirmed at run time via `discover`):
- **Train:** regions from `20230702185753` and `20231005123336`.
- **Held-out:** `20231210121321` (a segment never trained on).
- Per segment: **level-2** pyramid (~12650×9100, matches the old-data scale the recipe was proven
  at), a small number of **4096×4096 regions**, **26-layer centered depth window** — via the
  existing `qualitative.py` extraction path.
- The teacher prediction tif is fetched per segment and cropped/downscaled to the exact same
  region/scale as the extracted surface region (the alignment is deterministic: same segment
  geometry, level scaling factor, and region offsets).

## Architecture & components

All new code in `repro/sota_data/` (mirrors the existing slice).

### 1. `distill_prep.py` — the unit-testable core
`prep_distill_fragment(region_layers, teacher_region, out_root, seg_id, region_id,
threshold=None) -> out_seg_dir`:
- Inputs: `region_layers` `(26, H, W)` uint8 (from the zarr extractor) and `teacher_region`
  `(H', W')` teacher values for the same region.
- Resamples the teacher to `(H, W)` if needed (nearest for binary, bilinear for soft); if
  `threshold` is given, binarizes at it; writes the detector-format fragment
  (`layers/17..42.tif`, `<seg>_<region>_inklabels.png`, `<seg>_<region>_mask.png`).
- Validates shape agreement (>20% mismatch ⇒ `ValueError`, the standing loud-guard rule).
- Also provides `teacher_region_for(zarr_level_shape, region_box, teacher_full) -> np.ndarray`:
  crops the full-segment teacher tif to the level/region box (pure geometry, unit-testable).

### 2. `distill_run.py` — operational orchestration
Steps (each re-runnable): fetch teacher tifs; extract train/held-out regions (reusing the
`qualitative.py` zarr path); `prep_distill_fragment` for each; baseline measurement (epoch-7
detector vs teacher on the held-out region); train via
`DetectorConfig(data_root=..., train_fragment_ids=[train regions], valid_fragment_id=<held-out
region>)` and `detector.train`; best-epoch selection by held-out agreement-with-teacher; final
measurement + side-by-side render; write
`reports/detector/sota_distill_measurement.{md,json}` (baseline row vs distilled row, all columns
labeled "vs teacher").

### 3. Hardening (folded in, from the last review's deferred findings)
- `evaluate.py`: `json.dump(..., default=float)`.
- `convert.py`: `ValueError` (not `AttributeError`) when the label file fails to read; loud
  `ValueError` on unexpected integer dtypes in `_read_8bit`.
- `qualitative.py`: `write_fragment` reuses the same scaling logic as `convert._read_8bit` for
  non-uint8 input (shared helper) instead of a bare clip.

## Data flow

```
bucket: segments/{A,B,H}/surface-volumes/*.zarr + ink-detection/<canon>.tif
  extract level-2 regions (26 x 4096 x 4096)     [qualitative.py path]
  crop teacher tif to same region/scale          [distill_prep.teacher_region_for]
  prep_distill_fragment -> local_data/sota_distill/<seg>_<region>/ (detector format)
  baseline: epoch-7 detector vs teacher on held-out region   [A's metrics, "vs teacher"]
  detector.train (TimeSformer recipe, unchanged) on train regions
  best epoch by held-out agreement-with-teacher
  report: sota_distill_measurement.md (baseline vs distilled) + side-by-side render
```

## Testing

`tests/test_sota_distill_prep.py` (CPU, synthetic):
- `prep_distill_fragment` on a synthetic `(26,128,128)` stack + synthetic teacher: writes 26
  layers + label + mask; label matches the (resampled/binarized) teacher; loads via
  `read_image_mask`.
- Shape-mismatch teacher ⇒ `ValueError`.
- `teacher_region_for` geometry: cropping a known full-teacher array to a region box returns the
  expected sub-array (including a level-scaling case).
- Hardening regressions: `convert` unreadable-label → `ValueError`; unexpected int dtype →
  `ValueError`; `write_fragment` uint16 input is range-scaled (not clipped to black).

`distill_run.py` is operational (network + GPU), verified by running; training reuses the
already-tested `detector.train`.

## Error handling

- Teacher/region shape mismatches and unreadable files ⇒ loud `ValueError`s.
- The teacher tif's value range (binary vs continuous) is inspected at prep time; the chosen
  handling (threshold or soft) is recorded in the report — no silent assumption.
- Operational steps are individually re-runnable; fetches are resumable (re-run skips existing
  files at the `fs.get` level or re-downloads idempotently).
- GPU steps need the loop paused (`.loop_paused` + kill; resume `bash start.sh`).

## Global constraints

- A's metric contract; all metrics labeled "vs teacher". No detector code changes.
- Anonymous S3 (`s3fs`, `anon=True`), bucket `vesuvius-challenge-open-data`.
- Isolation: `repro/sota_data/` + `tests/` + `reports/detector/` + `local_data/sota_distill/`
  (git-ignored). Do NOT edit `run_autoresearch_loop.py` or `scripts/training/train.py`.
- No AI-authorship markers.

## Follow-ups (out of scope)

- Label registration (old hand labels → new flattening) to spot-check distillation against real
  ground truth.
- Multi-scroll distillation across the bucket's ~48 scrolls (the cross-scroll frontier).
- Sub-project C: point the autoresearch loop at the SOTA-native detector.
- July Progress Prize filing incorporating these results.
