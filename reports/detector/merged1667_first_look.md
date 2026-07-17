# PHerc 1667 merged full-reading segment — first independent render

The scroll that was read in full (announced 2026-06-25) has exactly one segment in the
open bucket carrying the merged reading geometry
(`20260612121456-w011_20260108140509268_merged_v4_flatboi_straightened_v4`, dated
2026-06-12) — and it is **mesh-only**: tifxyz + obj, no surface volume, no predictions.
This is the first independent surface volume rendered from it, produced with the render
CLI's new `--tifxyz` path (one command, `repro/sota_data/render_cli.py`).

Unlike the Scroll-3 first look, the renderer arrives here **gate-validated on this very
scroll**: the sibling segment w011 ships a released surface volume, and the clean-triple
acceptance run scored center-layer **NCC 0.7799 (PASS, pre-registered gate 0.60)** —
[render_validation_1667.md](render_validation_1667.md). No coordinate-scale inference was
needed (tifxyz coords are level-0 voxels by the validated convention).

## Region

The merged grid is (2061 × 30097) at scale 0.05 — ≈20.8 gigapixels of flattened surface
at full resolution, ~1.4 m of papyrus. Rendered region: grid (y0=512, x0=11888, 1024²)
at volume level 2, selected by a validity + z-bounds scan (the straightened mesh overruns
the scan volume's z extent near the scroll ends; the region is fully interior).
valid_frac 1.000, clamped_frac 0.000.

**The surface is unmistakably papyrus** — coherent fiber striations, weave cross-hatch,
and damage lacunae (surface-structure 36.4; empty renders score ~0, Scroll-3 papyrus ~41):
[merged1667_y512_x11888_surface.png](merged1667_y512_x11888_surface.png).

## arm C (honest caption: no reading claim)

arm C — the 3-scroll distilled student, for which PHerc 1667 is the *best* measured
transfer scroll (agreement-with-teacher lift ≈2.1 on sibling w-segments) — predicts
diffuse, tile-grained texture with **no letterforms or coherent ink strokes**
(pred-positive rate 0.194, essentially identical to Scroll 3's 0.196; suppressed on the
damage lacunae): [merged1667_y512_x11888_armC_ink.png](merged1667_y512_x11888_armC_ink.png).
Consistent with every prior cross-scroll finding: current models respond to texture off
their training distribution. **No reading, no letters.** Inference used a transient
all-zero label to satisfy the loader, deleted immediately (no fabricated GT persists).

## Why this matters

- The full reading of PHerc 1667 was produced with the core team's private pipeline; its
  merged geometry ships without a surface volume. This render makes that geometry usable
  by anyone, from the open bucket, with one command — and on this scroll the renderer's
  output is validated against released ground truth (0.78 NCC), not just plausible.
- It is the concrete first step of ScrollGT v0.2 path (b)
  ([scrollgt_v02_groundwork.md](scrollgt_v02_groundwork.md)): aligning the published
  scholar-validated reading onto this geometry would give the benchmark its first
  non-training-scroll targets.
