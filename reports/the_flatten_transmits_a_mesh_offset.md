# The flatten transmits a mesh offset: T = 0.94, both ways

**2026-09-23.** The result of `docs/preregistration/2026-09-22_does_the_flatten_transmit_a_mesh_offset.md`,
decided by `scripts/analyse_flatten_transmission.py` (written before either flatten ran). Data:
`reports/flatten_transmission.json`. Two deterministic flatten-only arms (render stubbed) of `rad0`'s
ten `w120–w129` meshes displaced by exactly −4 / +4 vx, against `flatten_det_a` (the same meshes
undisplaced). Lineage was checked by bytes at staging (`z.tif` identical, `x.tif` displaced), the
determinism shim activated in both arms, and all three share one tree.

## The result

| mesh offset | along the outward normal | perfect transmission | **T** | in-plane |
|---|---:|---:|---:|---:|
| −4 vx | −3.370 | −3.579 | **0.942** | 6.46 |
| +4 vx | +3.378 | +3.579 | **0.944** | 6.23 |

**Verdict: TRANSMITS.** A radial offset in the fitted meshes reaches the flattened surface the render
reads, at 94% in both directions. The prediction (T ≈ 1, band 0.8–1.1) is **met**. As registered, that
was close to certain by construction: the flattener optimises only a 2D map (`map_flatten_ms`), so
this confirms the code reading rather than discovering anything.

* **The 6% shortfall is symmetric** (0.942 vs 0.944). A curvature bias from the measurement would push
  both arms the same way (towards the concave side) and show as an asymmetry. So the shortfall is
  small and real, but its mechanism is **not investigated**.
* **The displaced inputs were also re-laid out**, by ~6.3–6.5 vx in-plane. This is the same behaviour as
  `reports/the_flatten_moves_the_grid_not_the_surface.md`: a different input gets a different layout
  on (nearly) its own surface.

## What it connects

* **The loop-reachability question is moot for gaming.** The offset sweep found **no free lever**
  (`reports/no_free_offset_lever.md`), so there was nothing to reach.
* **But it links fit error to the objective.** A radial bias in the fitted meshes lands at ~0.94× on
  the rendered surface. The sweep put the fitted surface at the best of seven positions, costing
  2–3% of `total_fg_pixels` per vx outward and more inward, at a resolution of ~±2.5%. **A fit
  change that shifts the surface radially by about 1 vx should cost a few percent of ink for that
  reason alone.** That is an inference joining two measurements, not a measurement of any fit.
* **It says nothing about ink directly.** Nothing here was rendered.

## Limits

One region, one magnitude (4 vx), one reference flatten, deterministic mode only.
