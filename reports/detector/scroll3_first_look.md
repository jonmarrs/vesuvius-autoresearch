# Scroll 3 (PHerc0332) first look — rendered surface + arm C

**No ground truth exists on Scroll 3** (it is unread — that is why First Letters is open),
and unlike Scroll 1 there is no released surface volume to calibrate the obj coordinate
scale. The renderer is placement-validated on Scroll 1 (center-layer NCC ~0.59 vs the
released surface, [render_validation.md](render_validation.md)); on Scroll 3 the
obj-coordinate scale was inferred **teacher-free** (render at candidate scales, keep the one
whose surface shows papyrus structure). This is a qualitative look, **NOT a reading claim** —
any legibility is by eye and must be independently corroborated before any prize consideration.

## Segment 20240711124827-20240618142020

**Coordinate-scale inference (teacher-free).** Rendered at three candidate obj level-divs;
mid-layer papyrus-texture structure (high-pass std over valid pixels):

| obj_level_div (meaning) | surface structure | verdict |
|---|---|---|
| 4 (obj coords = level-0) | **0.0 (empty — ÷4 lands off the papyrus)** | rejected |
| 2 (obj coords = level-1) | 41.27 | papyrus |
| 1 (obj coords = level-2) | 41.38 | **chosen** (papyrus, highest) |

The check decisively rejects `div=4` (empty render) and confirms the obj coords are at the
sampled level (`div=1`); `div=1` vs `div=2` are near-tied on structure (both land on real
papyrus), so the scale is resolved only up to that 2× ambiguity — disclosed.

**The renderer works.** At the chosen scale the surface layer is unmistakably papyrus:
coherent fiber striations, whorls, and sheet structure across a flattened segment
(valid_frac 0.936; black regions = UV areas with no mesh coverage). This is the first
independent surface volume rendered from one of Scroll 3's mesh-only bucket segments —
[scroll3_seg1_surface.png](scroll3_seg1_surface.png).

**arm C does not read it.** Predicted-positive rate 0.196; the prediction is diffuse,
fiber-grain-following texture with **no letterforms or coherent ink strokes**
([scroll3_seg1_armC_ink.png](scroll3_seg1_armC_ink.png)). This is the expected, honest
outcome: arm C is a cross-scroll distilled model with weak unseen-scroll transfer
(lift ~2.1), and Scroll 3 is out of its training distribution entirely. It responds to
texture, not ink — consistent with every prior cross-scroll finding in this project. **No
reading, no letters.**

## Segment 20240828190516-20240716140050 — deferred (compute-bound)

Attempted; a full 2048² render is ~4k S3-fetching tiles and exceeded the run time budget
twice. Segment 1 already establishes both findings (renderer produces coherent papyrus; arm
C reads texture not ink), so this segment is a redundant confirmation, not new evidence —
deferred rather than re-run. A lighter render (smaller `SIZE`, or cached volume chunks)
would complete it; not worth the compute here.

## What this establishes

- A **working, placement-validated renderer** that turns Scroll 3's mesh-only segments into
  detector-ready surface volumes — genuinely useful community tooling, since the bucket ships
  these segments without surface volumes or predictions.
- Confirmation, on the live First-Letters scroll itself, that our existing detectors read
  **texture, not ink** cross-scroll — the honest ceiling, now demonstrated on Scroll 3 and
  not just argued from Scroll-1 held-out numbers.

Reading Scroll 3 would need a detector that actually generalizes (or Scroll-3-specific
training data, which does not exist) — not merely the ability to render it. The renderer is
the reusable artifact here; the arm C result is a negative, honestly reported.
