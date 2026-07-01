# Detector on SOTA Scroll-1 data — qualitative (no aligned ground truth)

**Slice:** "rebase the ink detector on SOTA data" (Scroll 1 / PHerc Paris 4), evaluate-only phase.
The plan targeted a quantitative `val_f1`, but the operational run found that isn't cleanly
possible (see below), so per the plan's contingency this is a **visual** result, not a metric.

## What the open SOTA data actually is (the finding)

Segment `PHercParis4/segments/20230702185753` (our old-baseline segment) in
`s3://vesuvius-challenge-open-data/`:
- **Surface volume:** a multiscale OME-Zarr pyramid, **109 depth layers**, level 0 =
  **50600 × 36400** (uint8), levels 1..5 halving each step. High-resolution (2.4 µm, 78 keV).
- **`ink-detection/`:** a model **prediction** (`…new_canon_autoresearch_recipe…tif`), **not**
  a hand ground-truth label.
- Our **local hand ground-truth label** for this segment exists, but is aligned to the **old**
  flattening (13513 × 17381, 26 layers, aspect 0.78). The SOTA surface is **re-flattened**
  (aspect ≈ 1.39, 109 layers) — the label does **not** align to the new geometry.

**Consequence:** there is no ground-truth ink label aligned to the SOTA surface volume, so a
rigorous `val_f1` on it is not available. We deliberately do **not** report a `val_f1` against a
mismatched label (that would be the exact garbage-number trap our metric discipline avoids).

## What we ran

Extracted a **26-layer depth window** (centered on the surface, layers 41–66 of 109) from a
**4096 × 4096 region** of the level-2 pyramid (12650 × 9100, ≈ old-data scale) via OME-Zarr
partial read (`repro/sota_data/qualitative.py`), then ran the existing detector
(`models/detector/detector_epoch=7.ckpt`, trained on Scroll-2 `Fr47`) on it.
Renders: [`sota_scroll1_input_surface.png`](sota_scroll1_input_surface.png) (input) and
[`sota_scroll1_ink_ours.png`](sota_scroll1_ink_ours.png) (our detector's ink probability).

## Result (honest)

- The **input surface is excellent** — the papyrus fiber crosshatch and cracks are crisply
  resolved at 2.4 µm.
- The **detector's output is texture-driven, not legible ink**: it largely tracks fiber/surface
  structure and cracks (prob range 0.18–0.90, mean ≈ 0.47), with no clear Greek letterforms in
  this region.

**Interpretation.** Our detector is a **Scroll-2 model applied cross-scroll** to Scroll-1, and
this qualitative result matches the quantitative cross-scroll gap we measured earlier (prevalence
-lift ≈ 1.3, near the chance floor). **Better data alone does not make a cross-scroll model read
ink** — it needs retraining on the target distribution. This is consistent with the preprint's
own framing of ink nets as *visibility amplifiers* that must be trained for the data at hand, not
autonomous readers.

**Caveats:** one arbitrary region (may be text-sparse); the SOTA re-flattening + 2.4 µm fiber
detail is a different input distribution than the detector's 8-bit training data; no aligned label.

## The honest path forward (Phase 2, deferred)

A real quantitative rebase requires **retraining the detector on SOTA-quality Scroll-1 data with a
ground-truth label aligned to the SOTA flattening** — i.e., train on the new surface volumes using
the released ink labels/annotations for the SOTA segments (if/where they exist), not the old
labels. That is Sub-project follow-up work, not this evaluate-only slice.
