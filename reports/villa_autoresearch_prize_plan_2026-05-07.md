# Villa Autoresearch Prize Plan - 2026-05-07

## Snapshot

- Refreshed official `ScrollPrize/villa` remote metadata at 2026-05-07 during the active Day Shift sprint.
- Local Villa ref: `4b7c5c20d95b404b7e92dc70606a1b1ed8648fd3`.
- Official `origin/main`: `ad4e1b7d8a85c553c0b135b5f02ef98af9a9e923`.
- Delta from our local Villa checkout to official `origin/main`: 33 files.
- Prize-relevant fresh delta:
  - `lasagna`: 5 changed files, including flow/min-cut preprocessing and optimizer changes.
  - `volume-cartographer`: 13 changed files, including VC3D segmentation, overlay, chunked volume viewer, dataset, and surface patch code.
  - `optimized_inference`, `resnet3d_decoder`, `vesuvius_data`, and prize docs: no fresh changed files in this delta.
- Recent upstream commits:
  - `ad4e1b7d8 Fix crop to valid / early intersection end at edges (#884)`
  - `648245707 vc: in VcDataset use blosc_decompress_ctx to avoid global lock (#880)`
  - `027ca2542 vc: enable OPENMP in docker build (#881)`
  - `964bb5f49 L3d flow speed (#879)`
  - `8e0deb248 fix mask plane intersection view (#878)`

The practical read: the official repo is moving fastest in the exact tools we need after model inference: Lasagna geometry handling and VC3D review/performance. We should use the active Day Shift for model search, then route the best Scroll 2/3 candidates through Villa-native evidence generation as soon as the GPU is free.

## Best Uses Of Villa For Prize Odds

1. **Use issue #191 as the main First Letters / First Title bridge.**
   - Official hook: https://github.com/ScrollPrize/villa/issues/191
   - Local hook: `reports/lasagna_fiber_worklist.tsv`
   - Current top candidates are occupied 64x64 windows in `PHerc0125` div_90/div_100 and `PHerc0332` div_90.
   - Why this matters: plain ink inference is weak in compressed/high-curvature regions. Villa Lasagna/fiber preprocessing attacks the geometry failure mode before we ask the model to read ink.

2. **Treat VC3D fiber overlays as both a review layer and a Progress Prize path.**
   - Official hooks: https://github.com/ScrollPrize/villa/issues/369 and upstream VC3D commits #878, #880, #881, #884.
   - Local hook: `predict.py` already emits ink and fiber Zarr metadata; `scripts/validate_prize_artifact.py` checks scale/readiness.
   - Why this matters: prize reviewers need inspectable evidence, not just `val_bpb`. Fiber overlays beside ink overlays make false positives easier to reject and real strokes easier to defend.

3. **Keep scroll-specific augmentation search tied to official issue #201.**
   - Official hook: https://github.com/ScrollPrize/villa/issues/201
   - Local hook: `aug_scroll_decohesion_p`, `aug_scroll_squeeze_p`, `aug_scroll_z_dropout_p`, and `aug_scroll_intensity_drift_p`.
   - Why this matters: cross-scroll generalization remains the key model-side blocker. These knobs are already in Autoresearch and align with an official Progress Prize request.

4. **Use Villa as the compatibility oracle before any submission.**
   - Official hooks: VC3D/OME-Zarr conventions and ScrollPrize prize docs.
   - Local hook: `scripts/generate_submission_package.py`, `scripts/validate_prize_artifact.py`, `prize_readiness.tsv`.
   - Why this matters: every candidate should clear window size, scale bar, source position, train/predict separation, and OME-Zarr metadata checks before human review.

5. **Defer a blind Villa submodule update until post-sprint validation.**
   - The current upstream delta is valuable, but updating during active training risks mixing reproducibility and runtime changes.
   - Validate the new VC3D/Lasagna behavior against our existing `reports/pred_10_1000_1000_64x64_*` artifacts and the top Scroll 2/3 worklist first.

## Immediate Post-Sprint Handoff

The guarded handoff runner already refuses to spend GPU while Day/Night Shift is active. After the current Day Shift sprint finishes, run:

```bash
.venv/bin/python scripts/run_post_sprint_villa_handoff.py
```

Expected status while training is active is `BLOCKED_ACTIVE_SPRINT`. When the GPU is free, run the evidence path:

```bash
.venv/bin/python scripts/run_post_sprint_villa_handoff.py \
  --execute-inference \
  --execute-evidence
```

This executes the following queue:

1. `scripts/run_ranked_inference.py` over the top Scroll 2/3 ranked candidates.
2. `scripts/rank_scroll23_candidates.py` to fold prediction statistics back into ranking.
3. `scripts/build_lasagna_fiber_worklist.py` to refresh the issue #191 worklist.
4. `scripts/run_villa_prize_evidence_chain.py` for the top two candidates.

## Concrete Next Engineering Moves

1. Add a small `--skip-gpu` or `--preflight-only` mode to `run_post_sprint_villa_handoff.py` so we can refresh non-GPU manifests during active training without tripping the active-sprint guard.
2. Add a regression fixture for VC3D fiber/ink Zarr scale metadata using `reports/pred_10_1000_1000_64x64_*` as the local known-good artifact.
3. Add a Villa pin review checklist that compares local `villa` to `origin/main` for only `lasagna/`, `volume-cartographer/`, and prize docs before allowing a submodule update.
4. Convert the top 12 `reports/lasagna_fiber_worklist.tsv` rows into per-candidate evidence directories with structure tensors, ink/fiber overlays, metadata, and validator output.
5. Feed successful Villa evidence back into Autoresearch as hard negatives/positives or pseudo-label seeds, so the model search is informed by reviewable Scroll 2/3 geometry instead of Fragment-only metrics.

## Decision

The highest expected prize lift is a two-lane workflow:

- **During Day/Night Shift:** keep Autoresearch optimizing model families and official issue #201 augmentation axes.
- **Between shifts:** run the Villa handoff on high-occupancy Scroll 2/3 candidates, using Lasagna/fiber preprocessing and VC3D-compatible review artifacts to decide which model outputs deserve human review or submission packaging.

This uses official Villa where it is strongest: geometry, review tooling, data conventions, and Progress Prize alignment. It keeps Autoresearch focused where it is strongest: rapid model/config search and reproducible candidate generation.
