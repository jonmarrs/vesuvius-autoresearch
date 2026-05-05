# Villa Prize Readiness Workflow

This repo uses the official `ScrollPrize/villa` checkout as the compatibility
target for prize-facing outputs: OME-Zarr / VC3D metadata, official evaluation
metrics, and reproducible Scroll 2/3 search queues.

## 0. Audit the Official Villa Pin

Before a prize sprint, refresh upstream metadata and audit our pinned Villa
submodule:

```bash
git -C villa fetch origin main
uv run python scripts/audit_villa_upstream.py
uv run python scripts/plan_villa_prize_opportunities.py
```

The report is written to `reports/villa_upstream_audit.json` and groups upstream
changes by prize relevance: `lasagna`, optimized inference, ResNet3D decoder,
VC3D / Volume Cartographer, Vesuvius data access, and current prize docs. The
opportunity planner writes `reports/villa_prize_opportunities.json`, ranking
official issue-backed work by prize impact and local Autoresearch hooks.

## 1. Build the Scroll 2/3 Search Queue

```bash
uv run python scripts/build_scroll23_search_queue.py \
  --windows-per-division 5 \
  --out reports/scroll23_search_queue.tsv \
  --manifest reports/scroll23_search_queue.json
```

The queue prioritizes Scroll 2 (`PHerc0125`) and Scroll 3 (`PHerc0332`) windows
for First Letters / First Title searches. When local Zarr divisions are present,
it seeds candidate windows from occupied chunks instead of placeholder center
coordinates. It marks `64x64` ML windows as submittable under the official
guidance and records any local division data.

Rank the queue after predictions are available:

```bash
uv run python scripts/rank_scroll23_candidates.py \
  --queue reports/scroll23_search_queue.tsv \
  --prediction-dir predictions \
  --out reports/scroll23_ranked_candidates.tsv
```

The ranking pass uses queue priority, core-scroll focus, local data availability,
submittable-window status, and optional `*_ink.npy` / `*_fiber.npy` prediction
statistics. It also records local Zarr chunk occupancy and penalizes stale queue
rows that point at missing chunks. It is metadata-only and does not run inference
or download data.

Build a Lasagna/fiber worklist for official Villa issue #191:

```bash
uv run python scripts/build_lasagna_fiber_worklist.py \
  --ranked reports/scroll23_ranked_candidates.tsv \
  --limit 12
```

This writes `reports/lasagna_fiber_worklist.json` and `.tsv`, filtering to
submittable occupied local windows and adding commands for structure-tensor
preprocessing plus follow-up evidence-chain runs.

Generate exact inference commands for the top ranked rows:

```bash
uv run python scripts/run_ranked_inference.py \
  --ranked reports/scroll23_ranked_candidates.tsv \
  --limit 8 \
  --manifest reports/scroll23_inference_commands.sh
```

This is dry-run by default. Add `--execute` only when you are ready to run the
jobs serially on the active machine/GPU.

## 2. Run Prediction on a Candidate

Use a row from `reports/scroll23_search_queue.tsv`:

```bash
uv run python predict.py \
  --uri local_data/PHerc0125_Divisions/div_100/0 \
  --z 9000 --y 2048 --x 2048 \
  --width 64 --height 64 --patch_size 64 \
  --output_img predictions/scroll2_div100_candidate.png \
  --metadata_out predictions/scroll2_div100_candidate_meta.json
```

`predict.py` writes:

- PNG discovery/context image with a scale bar
- `*_ink.npy` and `*_fiber.npy`
- `*_ink.png` and `*_fiber.png`
- VC3D-compatible ink and fiber prediction Zarrs with `meta.json` and OME-Zarr scale metadata
- metadata JSON with source URI, origin XYZ, voxel size, patch size, ink stats, and fiber stats

## 3. Validate Prize Mechanics

```bash
uv run python scripts/validate_prize_artifact.py \
  --metadata predictions/scroll2_div100_candidate_meta.json \
  --train-mask submission_package_dry_run/train_mask.npy \
  --predict-mask submission_package_dry_run/predict_mask.npy \
  --out predictions/scroll2_div100_candidate_readiness.json
```

The validator checks locally verifiable requirements:

- scroll / source / segmentation provenance
- 3D position
- `64x64` or smaller ML window
- declared 1 cm scale bar
- zero train/predict overlap when masks are provided
- VC3D/Zarr shape metadata and OME-Zarr spatial scale metadata when a prediction Zarr is provided

## 4. Generate a Dry-Run Package

```bash
uv run python scripts/generate_submission_package.py
```

This creates `submission_package_dry_run/` with a discovery image, metadata,
separate train/predict masks, hallucination mitigation note, and
`PRIZE_READINESS_REPORT.json`.

## 5. Training Logs

Training still writes the historical `results.tsv` schema. Prize-specific
readiness fields are written separately to `prize_readiness.tsv` and embedded in
`best_model.pt` / `run_result.json`:

- `submittable`
- `window_ok`
- `window_mm`
- `villa_metrics_ok`

Scroll-specific 3D augmentations can be enabled in `ExperimentConfig` for
Villa issue #201 ablations:

- `aug_scroll_decohesion_p`
- `aug_scroll_squeeze_p`
- `aug_scroll_z_dropout_p`
- `aug_scroll_intensity_drift_p`
