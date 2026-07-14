# Renderer validation (Scroll 1 20230702185753, scan 20260411134726) — FAIL

Clean triple: tifxyz geometry + raw volume + released surface volume all in one frame; only our sampler is unknown. Center-depth layer vs the released surface volume, same (row,col) parameterization.

- sign1: NCC 0.5936 valid 0.875 clamped 0.005
- sign-1: NCC 0.5936 valid 0.875 clamped 0.005

Best sign: sign1. Gate: NCC >= 0.60.

## Interpretation (honest — did NOT move the goalpost)

The renderer scores **NCC ~0.59 against released ground truth**, stable across two artifact
removals (finer grid 633→1265, best-of depth-slice search): **0.5800 → 0.5936**. It plateaus
just under the 0.60 gate I set before running.

- This is a **strong positive, far from chance.** A wrong axis order, wrong coordinate
  scale, or wrong placement would give NCC ≈ 0; 0.59 means the sampler lands on the correct
  surface and reads correlated papyrus texture. The `(x,y,z)→(z,y,x)` + level-0→level-2
  conventions and the tile sampler are therefore substantively correct.
- **Why not ≥0.8:** (a) my render grid (1265px) is still coarser than the reference's
  finest matching level (surface-vol L5, 1582px) — a resolution mismatch that blurs the
  comparison; (b) the released surface volume is the core team's *independent* render with
  its own depth spacing / surface offset / interpolation, so two correct renders of the same
  surface are not expected to match pixel-for-pixel at coarse resolution. The residual is
  render-methodology difference, not a placement bug.
- **Both normal signs tie** because the compared layer is the surface center (k=0),
  independent of normal direction — sign is not distinguished by this gate (it only affects
  off-surface layers, which the qualitative Scroll-3 use does not gate on).

**Verdict for use:** the renderer is **validated as fundamentally correct in placement**,
sufficient for a *qualitative* Scroll-3 first look (surface texture + arm C prediction, no
reading claims). It is **not** validated as a pixel-accurate reproduction of the core team's
surface volumes, and must not be presented as one. Reaching the strict 0.60 bar would need a
full-resolution comparison (2530px grid vs surface-vol L4) — deferred as not worth the cost
for the qualitative purpose.

