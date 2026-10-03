# Pre-registration: does grid cell size drive the linear/smooth difference, and does smooth read better on coarse grids?

**Written 2026-10-03, before any coarse-grid arm was scored.** Chain
`repro/spiral_render/run_scorer_vs_labels_coarse.sh`, mesh tool `scripts/subsample_mesh.py`, analysis
`scripts/analyse_scorer_vs_labels_coarse.py`. The last is a wrapper that runs finding 72's analysis
unchanged on a different work dir. All are committed with this file.

## Why

* **Finding 70 (fitted spiral surface):** smooth vs linear moves the scorer count up to ±20% per
  window, median |Δ| 5.2%.
* **Finding 72 (villa's labelled segment meshes):** about 1%, with no change in label agreement.
* **Normalisation is ruled out:** shared p95 still gives median 4.7%.
* **Measured difference:** the spiral flat's grid cells are ~80 × 74 voxels (~10 output px), the segment
  meshes' ~20 × 20 (~2.5 px). Linear and smooth agree at grid points and differ only inside cells.
* The spiral surfaces villa's loop scores **are** coarse, so the decision-relevant question for #1818 is
  what smooth does there. The labels can answer it.

## Method

* Finding 72's pipeline, unchanged (group 1, scale 0.25, 5 slices, render_ink strip, pinned scorer with
  probabilities, labels at level 3, the fixed alignment gate, 256-px block bootstrap), with one change.
  Each segment's mesh is **subsampled 4× in both grid directions** (`subsample_mesh.py`: every 4th
  point kept unchanged, `scale` ÷ 4). That makes ~80-voxel cells, matching the spiral flats.
* **Reachability, checked (no metric):** the coarse mesh of `20231016151002` renders onto a
  4000 × 6500 canvas. Grid point *i* lands at 10*i* px in both meshes, so the frame's origin is
  unchanged. The analysis crops to the label shape (3995 × 6495), and the gate checks alignment.
* Same 8 segments, linear vs smooth on `vc-render:sampler-f637f3b35`.

## Predictions, fixed now

1. **Cell size drives the count difference:** on coarse grids, median window |Δcount| ≥ 3% (finding 72
   on fine grids: 1.3%). Confidence moderate.
2. **Smooth reads better on coarse grids:** smooth's scorer-probability AP ≥ linear's in at least 6
   of the included segments. Confidence low. This is #1818's stated mechanism: linear steps the normal
   at every cell edge, and coarse cells make those steps larger.

**Decision rule for (2):** "smooth agrees better with villa's labels on coarse grids" only if ΔAP > 0
is **resolved** in ≥ 6 of the included segments; "worse" symmetrically; otherwise no consistent
difference. Reported regardless: how much coarsening costs linear (coarse vs finding 72's fine linear
AP; descriptive only, since the domains differ slightly).

## Known confounds

As finding 72: the labels are partly pseudo-labelled with fine-grid, linear geometry. Here that
favours neither coarse mode, but it does favour fine over coarse in the descriptive comparison.

## Cost

16 renders and 16 scorer runs, about 2–3 h unattended. No new downloads: meshes are subsampled from
the finding-71 copies, and labels are re-fetched.
