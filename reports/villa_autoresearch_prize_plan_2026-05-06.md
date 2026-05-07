# Villa Autoresearch Prize Plan - 2026-05-06

## Snapshot

- Refreshed `ScrollPrize/villa` remote metadata at 2026-05-06 20:19 PDT.
- Local Villa ref: `4b7c5c20d95b404b7e92dc70606a1b1ed8648fd3`.
- Official `origin/main`: `8e0deb2487087e849d528d3425888294d521bb72`.
- Delta from our local Villa checkout to official `origin/main`: 24 files.
- Prize-relevant fresh delta: 9 Volume Cartographer / VC3D files, from upstream commit `8e0deb248 fix mask plane intersection view (#878)`.

The practical read is that our current Villa pin is still usable for Autoresearch, but the official repo has moved in review-tool code. We should not blindly update the submodule during an active sprint; we should test the VC3D delta against our exported ink/fiber overlays first.

## Highest-ROI Uses Of Villa

1. Route Scroll 2/3 candidates through geometry and fiber preprocessing before more blind ink inference.
   - Official anchor: `villa-issue-191`, surface and fiber predictions in compressed or highly curved areas.
   - Local hooks: `reports/scroll23_ranked_candidates.tsv`, `reports/lasagna_fiber_worklist.tsv`, `scripts/build_lasagna_fiber_worklist.py`, `scripts/compute_structure_tensors.py`, `scripts/run_villa_prize_evidence_chain.py`.
   - Why this helps prizes: First Letters and First Title are bottlenecked less by model architecture and more by bad local surface geometry. Our current worklist already has occupied 64x64 windows in `PHerc0125` div_90/div_100 and `PHerc0332` div_90.

2. Treat VC3D fiber overlays as a Progress Prize and review-quality multiplier.
   - Official anchors: `villa-issue-369` and the fresh VC3D mask-plane intersection fix.
   - Local hooks: `predict.py` fiber Zarr export, `scripts/validate_prize_artifact.py`, `reports/pred_*_fiber.zarr`.
   - Why this helps prizes: it converts Autoresearch outputs into a Villa-native reviewer artifact, not just a model metric. This should improve human triage and is also a plausible standalone Progress Prize contribution.

3. Keep scroll-specific 3D augmentations in the Autoresearch search space.
   - Official anchor: `villa-issue-201`.
   - Local hooks: `ExperimentConfig` fields `aug_scroll_decohesion_p`, `aug_scroll_squeeze_p`, `aug_scroll_z_dropout_p`, and `aug_scroll_intensity_drift_p`.
   - Why this helps prizes: these are directly targeted at cross-scroll domain shift, which is the failure mode between Fragment training and Scroll 2/3 discovery.

4. Use Villa as the submission compatibility oracle.
   - Official anchors: prize docs, VC3D/OME-Zarr conventions, segmentation metrics.
   - Local hooks: `train.py` prize gates, `prize_readiness.tsv`, `scripts/generate_submission_package.py`, `scripts/validate_prize_artifact.py`.
   - Why this helps prizes: every candidate should be mechanically valid before we spend reviewer time on it: window size, scale bar, train/predict separation, source position, and VC3D/Zarr metadata.

5. Add official optimized-inference compatibility as a model-family gate.
   - Official anchor: Villa optimized inference and 3D decoder contracts.
   - Local hooks: `scripts/smoke_test_villa_optimized_inference.py`, `ensemble_predict.py`, `predict.py`.
   - Why this helps prizes: a candidate that cannot run through the official-ish runtime path is weaker evidence. We should smoke-test checkpoints before promoting them as prize-facing.

## Recommended Next Sprint Queue

1. Run ranked inference on the top occupied Scroll 2/3 candidates after the current Night Shift cycle finishes:

   ```bash
   .venv/bin/python scripts/run_ranked_inference.py \
     --ranked reports/scroll23_ranked_candidates.tsv \
     --limit 8 \
     --manifest reports/scroll23_inference_commands.sh \
     --execute
   ```

2. Re-rank with prediction statistics:

   ```bash
   .venv/bin/python scripts/rank_scroll23_candidates.py \
     --queue reports/scroll23_search_queue.tsv \
     --prediction-dir predictions \
     --out reports/scroll23_ranked_candidates.tsv
   ```

3. Rebuild the Lasagna/fiber worklist:

   ```bash
   .venv/bin/python scripts/build_lasagna_fiber_worklist.py \
     --ranked reports/scroll23_ranked_candidates.tsv \
     --limit 12
   ```

4. For the top two occupied candidates, compute structure tensors and generate evidence directories:

   ```bash
   .venv/bin/python scripts/compute_structure_tensors.py \
     --input local_data/PHerc0125_Divisions/div_90/0 \
     --output reports/lasagna_fiber_candidates/000_pred_18176_4128_4128_64x64/structure_tensors.zarr

   .venv/bin/python scripts/run_villa_prize_evidence_chain.py \
     --ranked reports/scroll23_ranked_candidates.tsv \
     --candidate-index 0 \
     --out-dir reports/lasagna_fiber_candidates/000_pred_18176_4128_4128_64x64/evidence \
     --execute \
     --checkpoint best_model.pt
   ```

5. Before updating the Villa submodule, test the fresh VC3D upstream delta against our existing fiber/ink Zarrs and the active viewer workflow. If it improves mask-plane intersection review, update the submodule in a separate commit and note the exact official commit in `VILLA_STRATEGY.md`.

## Decision

The best near-term use of Villa is not another architecture port. It is a Villa-native evidence pipeline: occupied Scroll 2/3 windows -> Autoresearch ink/fiber inference -> VC3D-compatible overlays -> structure tensor / Lasagna preprocessing -> prize validator -> Crackle/VC3D human review. That path directly raises First Letters / First Title odds and also creates Progress Prize artifacts along the way.
