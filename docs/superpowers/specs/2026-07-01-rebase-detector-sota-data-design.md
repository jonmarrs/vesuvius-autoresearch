# Rebase the Ink Detector on SOTA Scroll-1 Data — Design

**Status:** Approved design (brainstorming). First slice of the "rebase on SOTA capabilities" pivot.

## Context & motivation

On 2026-06-25 the Vesuvius Challenge read the first *entire* Herculaneum scroll (PHerc. 1667 / Scroll 4).
The preprint (*Complete virtual unwrapping and reading of a rolled Herculaneum papyrus*, arXiv 2606.29085)
shows the achievement was driven by **better data** (new ESRF BM18 phase-contrast synchrotron µCT, where
ink is more visible) + **Volume Cartographer** unwrapping + deep-net ink models used as **"visibility
amplifiers for expert inspection, not autonomous reading systems"** + papyrologist transcription. The data
is open at `scrollprize.org/data` (`s3://vesuvius-challenge-open-data/`, OME-Zarr with partial reads; no
credentials).

Replicating the full pipeline is infeasible on our single RTX 4090 (petabyte synchrotron scans, large-volume
reconstruction, heavy segmentation, expert papyrology). But we can **rebase our detector on the SOTA data**:
run our existing detector on a released **Scroll 1 / PHerc Paris 4** segment (its ink is now directly
visible; 2023 GP readings confirmed 1-to-1) and quantify whether better data alone lifts our numbers.

Our detector's old-data Scroll-1 result (Sub-project A cross-scroll measurement, epoch-7 model trained on
Scroll-2 Fr47) is the baseline to beat: **val_f1 0.222 / ap_prevalence_lift 1.29 / roc_auc 0.585** on the
old 8-bit Scroll-1 segment `20230702185753`.

## Goals / success criteria

1. Identify and stream one released **Scroll 1 / PHerc Paris 4** segment that has both a surface-aligned
   texture volume (flattened `layers/`) and a ground-truth ink label.
2. Convert it to the detector's input format (26 depth slices, 8-bit `layers/17..42.tif`, `inklabels.png`,
   `mask.png`).
3. Evaluate our existing detector (`models/detector/detector_epoch=7.ckpt`) on it with A's metric contract
   and write a report comparing to the old-data baseline (0.222 / 1.29). **Success = a real, quantified
   data-lift number (either direction).**

## Non-goals (scope boundary)

- **One segment, evaluate-only** (Phase 1). Retrain on SOTA data is Phase 2 (deferred, in-spec).
- **Use released, already-flattened surface volumes** — no segmentation / Volume-Cartographer unwrapping.
- **No full-scroll reading**; **no detector code changes** (reuse `detector` + A's `metrics`/`measure`).
- No PHerc 1667 / PHerc 139 in this slice (Scroll 1 chosen for validatability).

## Architecture & components

New directory `repro/sota_data/` (mirrors `repro/gp_winner`, `repro/ink_segformer`), reusing the
`vesuvius_autoresearch.detector` subpackage for inference and evaluation.

### 1. `discover.py` — de-risking data discovery (operational)
Lists `s3://vesuvius-challenge-open-data/` (via `s3fs`/`boto3`, anonymous) for Scroll 1 / PHerc Paris 4
segments, reporting for each candidate: whether a surface-volume (flattened `layers/` or OME-Zarr texture
volume) exists, whether an ink label / ink prediction exists, and approximate sizes. Prints a ranked
candidate list. **Resolves the layout unknowns before any download.**

### 2. `fetch.py` — stream one segment (operational)
`fetch(segment_id, out_dir="local_data/sota_scroll1/<seg>")` streams (OME-Zarr partial read) the chosen
segment's surface-volume slices (all depth slices, or a bounded depth range the discovery step reports) +
ink label + mask to local disk. GB-scale, not TB.

### 3. `convert.py` — format adapter (the one unit-testable code unit)
`convert_surface_volume(src_dir, seg_id, out_root, start_idx=17, end_idx=43) -> out_seg_dir`:
- Reads the fetched surface-volume slices (a `(depth, H, W)` or `(H, W, depth)` stack), selects the
  26-slice depth window centered on the surface, writes 8-bit `layers/{i:02}.tif` for `i in [start_idx,
  end_idx)`.
- Writes `<seg>_inklabels.png` (ink label resampled to the layer H×W grid) and `<seg>_mask.png`.
- **Validates** the depth count and label/volume H×W agreement (>20% mismatch ⇒ `ValueError`, mirroring
  the cross-scroll loader guard), failing loudly rather than producing garbage.
- Output layout matches `detector.data.read_image_mask` exactly (so evaluation is a straight reuse).

### 4. Evaluation (reuse A)
Run `detector` inference + A's `metrics.segmentation_metrics` (via `cli measure` or a thin caller) on the
converted segment, and write `reports/detector/sota_scroll1_measurement.md` / `.json` comparing SOTA-data
`val_f1`/`ap`/`lift`/`roc_auc` to the old-data baseline (0.222 / 1.29 / 0.585). No new eval code.

## Data flow

```
s3://vesuvius-challenge-open-data/ (Scroll1 / PHercParis4)
  discover.py            -> candidate segment ids (surface-vol + ink label + sizes)
  fetch.py <seg>         -> local_data/sota_scroll1/<seg>/ (partial OME-Zarr read)
  convert.py <seg>       -> .../layers/17..42.tif + <seg>_inklabels.png + <seg>_mask.png
  detector measure       -> val_f1 / ap / lift / roc_auc
                         -> reports/detector/sota_scroll1_measurement.md (vs old 0.222 / 1.29)
```

## Testing

`tests/test_sota_convert.py` (CPU, synthetic — the only genuinely unit-testable unit):
- Build a synthetic surface volume (e.g. a `(40, 128, 128)` uint16 stack + a `(128,128)` ink label + mask
  as files or arrays), run `convert_surface_volume` → assert exactly 26 `layers/{17..42}.tif` are written,
  each `(128,128)`; `inklabels.png` and `mask.png` exist at `(128,128)`; and the output dir loads cleanly
  via `detector.data.read_image_mask` (shape `(...,26)`).
- A depth-count or H×W-mismatch input raises `ValueError` (loud-failure guard).

`discover.py` / `fetch.py` are **operational** (they hit the live bucket) — verified by running, not unit
tests (no live-network unit tests). Evaluation reuses A's already-tested `metrics`/`measure`.

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_sota_convert.py -v`

## Error handling & contingencies

- **No released ink label for any Scroll-1 segment** (discovered in step 1): fall back to comparing our
  detector's ink map to the released ink *prediction* (qualitative overlay in the report), and record the
  limitation — do NOT fabricate a val_f1 without ground truth.
- **Streaming deps missing** (`s3fs`): `discover.py` checks and the plan adds `s3fs` via `uv add` if absent
  (`zarr`/`numpy`/`Pillow` are already present).
- **Bucket/network failure**: surfaced as a clear error; the operational steps are re-runnable.
- **Depth/shape mismatch** in convert: `ValueError` with actual-vs-expected shapes.

## Operational note

The GPU eval (~4 min, one segment) needs the loop paused (`.loop_paused` + kill; resume `bash start.sh`).
Discovery/fetch/convert are CPU/network and don't need the GPU.

## Global constraints

- Reuse A's metric contract (`val_f1` primary; AP + prevalence-lift gates; ROC-AUC secondary). No detector
  code changes.
- Isolation: new code under `repro/sota_data/` + `tests/`; artifacts under `reports/detector/` +
  `local_data/sota_scroll1/` (git-ignored data). Do NOT edit `run_autoresearch_loop.py` or
  `scripts/training/train.py`.
- No AI-authorship markers.

## Follow-ups (out of scope)

- Phase 2: retrain the detector on SOTA Scroll-1 segments (hold one out) if the data lift is promising.
- PHerc 1667 / PHerc 139 rebasing (cross-scroll on SOTA data).
- Volume-Cartographer unwrapping of a raw sub-volume (mini end-to-end).
