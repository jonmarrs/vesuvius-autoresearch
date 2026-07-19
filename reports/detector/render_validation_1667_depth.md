# Renderer depth validation (PHerc1667 w011) — full-stack agreement with the released volume

The center-layer gate (NCC 0.78, PASS) is sign-invariant by construction, so it could
not validate the depth direction or spacing of the 26-layer stacks the renderer emits.
This probe does: a 512² w011 region rendered at sign=+1, every layer NCC'd against every
released surface-volume depth slice (26×109 matrix). Script:
`repro/sota_data/validate_render_1667_depth.py`.

- **All 26 layers well-matched: NCC 0.84–0.89** (per-layer maxima; higher than the
  center-layer gate score — this interior crop is cleaner than the full segment).
- **Best-match mapping k→d is perfectly monotonic (rank corr 1.000), slope exactly
  4.00** released slices per rendered layer — the value correct level-2 depth scaling
  predicts (our step = 4 level-0 voxels; the released stack's 109 slices are
  level-0-spaced). Depth *scale* confirmed, not just direction.
- **Verdict: sign=+1 matches the released convention** (the CLI default). Our stack
  spans released slices 2–102 of 109 — well-centered on the sheet.

Renderer validation status is therefore upgraded from "placement-correct + center-layer
gate PASS" to **full-3D-stack validated on PHerc 1667**: lateral placement (0.78 gate),
depth direction, and depth spacing all measured against released ground truth.
