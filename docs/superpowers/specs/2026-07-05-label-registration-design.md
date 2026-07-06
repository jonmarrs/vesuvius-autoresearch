# Ground-Truth Label Registration onto the SOTA Flattening — Design

**Status:** Approved design (brainstorming). Fifth slice of the SOTA-rebase pivot, following the
scaling-saturation result (`2026-07-03-scaled-multiscroll-distillation-design.md`).

## Context & motivation

Every SOTA-data result so far is **agreement-with-teacher** — no ground-truth ink labels aligned
to the re-flattened SOTA surfaces exist in the open bucket, and our old hand labels live on the
old 2023 flattening (different geometry). Two things now hang on closing that gap:

1. **Validation:** the July filing's one soft spot is that the distillation story has no
   independent ground-truth number.
2. **Diagnosis:** the measured cross-scroll saturation (lift ≈ 2.1 on unseen PHerc 1667) cannot
   be attributed — agreement-with-teacher can't distinguish a *teacher ceiling* (student
   extracted all transferable teacher signal) from a *domain ceiling*.

**Key discovery (verified in the bucket):** the segment's `mesh/` directory ships **tifxyz
coordinate meshes for the same segment on multiple volumes**, including
`20230702185753-on-20230205180739-7.91um.tifxyz` (the **old 2023 scan** our hand labels align
to) and `20230702185753-on-20260411134726-2.4um.tifxyz` (the **exact SOTA volume** we distill
on), plus an `intermediate/` directory. TIFXYZ maps flattened pixels → 3D scan coordinates, so
both ends of a principled geometric bridge between old and new flattenings are published.

## Target & scope

**One segment** — Scroll-1 `20230702185753` (old hand label 13568×17408, ink fraction 0.073,
verified on disk; SOTA surface 50600×36400 @2.4µm, level-2 12650×9100) — **one region**
(the existing prepped 4096² level-2 region at (4000,2500) where all our SOTA measurements
already live). No training.

## Approach (staged, honesty-gated)

**Stage 1 — mesh-bridge feasibility probe (cheap, decides the method).** Fetch and parse both
tifxyz meshes (+ list `intermediate/`). Determine: format (per-pixel x,y,z planes?), UV grid
shapes, and whether the two meshes' 3D frames are relatable (same canonical frame, a published
scan-to-scan transform in `intermediate/`, or shared UV parameterization). Outcome A: exact
per-pixel correspondence is computable → use it. Outcome B: frames unrelatable with released
data → fall back to Stage-2b.

**Stage 2a — mesh-based warp (preferred):** for each pixel of the target SOTA region, use the
new-volume tifxyz to get its 3D point, map into the old scan frame (identity if canonical /
via the published transform), invert the old tifxyz (nearest-neighbor lookup over the old UV
grid, KD-tree) to find the old-flattening pixel, and sample the old hand label. Produces a
registered label + a per-pixel correspondence-distance map (residual of the nearest-neighbor
match) as the registration-quality signal.

**Stage 2b — feature-based fallback:** ORB/SIFT matching between the old mid-layer surface
image and the SOTA region (both are fiber-textured), RANSAC affine/similarity, warp the label.
Global transform only; usable if inlier support is strong.

**Stage 3 — alignment validation gate (mandatory, before ANY scoring):** overlay renders
(registered label over the SOTA surface and over the teacher prediction) + quantitative checks
(Stage 2a: correspondence-residual stats; Stage 2b: RANSAC inlier count/ratio + NCC of warped
old surface vs new surface). **If the gate fails, we report the negative and STOP — no metrics
against a misaligned label** (the standing discipline; this failure mode invalidated an
experiment once already).

**Stage 4 — ground-truth scoring (the payoff):** with a validated registered label, score on
the region under A's metric contract, each row explicitly framed **"vs registered ground truth
(registration method + residual stated)"**:
- the **canon teacher itself** (first ground-truth calibration of the teacher),
- the distilled students (Phase-2 arm A, arm B, arm C),
- the legacy detector.
Report `reports/detector/registered_gt_validation.{md,json}` + renders. This calibrates what
"agreement-with-teacher 0.66" means in ground-truth terms and anchors the whole distillation
arc.

## Non-goals

- No training; one segment, one region (spot-check, not a labels-at-scale pipeline).
- No PHerc-1667 ground truth (its published readings are a follow-up — this slice proves the
  method where we own the labels).
- No claim that registration is exact — the residual/inlier stats are part of every reported
  number's framing.

## Components

All in `repro/sota_data/` + `tests/`:
1. `register.py` — tifxyz reader, correspondence builder (Stage 2a), feature-fallback (2b),
   label warper, residual/quality stats. Pure-geometry parts unit-tested with synthetic
   meshes/labels (round-trip: a known warp applied to a synthetic label is recovered).
2. `register_run.py` (operational) — subcommands `probe` (Stage 1), `warp` (2a/2b), `validate`
   (Stage 3 renders + stats), `score` (Stage 4; loud guard: refuses to run unless a
   validation-passed marker exists).
3. Loud guards throughout (missing meshes, unparseable formats, residuals over threshold).
   Concrete gate thresholds (e.g., max acceptable median correspondence residual, minimum
   RANSAC inlier ratio) are set during the Stage-1 probe from the observed data scales and
   recorded in the validation report — not invented in advance of seeing the mesh formats.

## Success criteria

1. Stage-1 probe answers the method question either way (a finding in itself — documents what
   the released meshes enable).
2. A registered label that passes the validation gate, OR an honest documented negative.
3. If validated: the ground-truth scoring table (teacher + 3 students + legacy) committed with
   registration-quality caveats inline.

## Global constraints

Isolation (`repro/sota_data/` + `tests/` + `reports/detector/` + git-ignored `local_data/`);
anonymous S3; no detector-code changes; no AI-authorship markers; loop paused only for GPU
inference in Stage 4 (registration itself is CPU).

## Follow-ups (out of scope)

- Registering PHerc-1667's published readings → diagnosing the transfer plateau directly.
- Labels-at-scale: registered old labels as *training* data on SOTA surfaces (ground-truth
  fine-tuning of the distilled student).
- July filing refresh with the ground-truth validation row (deadline 2026-07-31).
