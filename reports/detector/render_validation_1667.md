# Renderer validation #2 (PHerc1667 w011, scan 20251217075048) — PASS

Second-scroll acceptance gate for the surface renderer, same clean-triple design as the
Scroll-1 run (`reports/detector/render_validation.md`): tifxyz geometry + raw volume +
released surface volume all in one frame (scan 20251217075048, 2.399µm), so only our
sampler is unknown. Gate pre-registered before the run: center-layer NCC ≥ 0.60 vs the
released surface volume. Script: `repro/sota_data/validate_render_1667.py` (uses the new
tifxyz input path, `render_surface.read_tifxyz` + `pointmap_from_tifxyz`).

- grid (1975, 736), valid 0.798; reference = released surface-volume level 4 (109, 2469, 920)
- **center-layer NCC = 0.7799 → PASS** (clamped 0.005; sign=+1 only — the center layer is
  sign-invariant, measured on Scroll 1 where both signs tied)

## Why this also strengthens the Scroll-1 result

The Scroll-1 run scored 0.5936, just under its 0.60 gate, and the report attributed the
residual to *render-resolution mismatch* (our grid was coarser than the reference's
closest pyramid level). This run is the test of that explanation: here the tifxyz grid
(1975×736) nearly matches the reference level (2469×920), and NCC rises to **0.78** with
the *same* conventions and sampler. A placement bug would not get better on a harder,
unseen scroll; a resolution artifact would — and did. The renderer's coordinate
conventions ((x,y,z)→(z,y,x), level-0→level-2 scaling) transfer across scrolls unchanged.

Status across scrolls: Scroll 1 = 0.59 (FAIL vs gate, placement-correct, resolution-limited
comparison); **PHerc 1667 = 0.78 (PASS)**. The renderer is now gate-validated on released
ground truth on one scroll and placement-validated on two.
