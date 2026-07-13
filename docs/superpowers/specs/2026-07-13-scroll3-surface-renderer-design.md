# Scroll 3 surface-volume renderer

**Date:** 2026-07-13
**Status:** approved design, pre-implementation
**Strategy context:** the B-swing's first artifact (Q3 plan) + future community tooling.
PHerc0332 (Scroll 3, a live $60k First Letters/Title target) ships two segments in the
open bucket that are **mesh-only** — no surface volumes, no predictions — so nobody
without a private renderer can run ink detection on them. We build the renderer from
components our stack already has, validate it against ground truth on Scroll 1, then
produce the first independent surface volumes + window-compliant detector inference on
Scroll 3.

## Inputs (all verified present, anonymous S3)

- `PHerc0332/segments/{seg}/mesh/intermediate/{seg}_original.obj` — the surface mesh:
  3D vertices `v` (scan coordinates) paired with flattened texture coords `vt` (the UV
  layout). **This is the geometry source.** Segments: `20240711124827-20240618142020`,
  `20240828190516-20240716140050`. NOTE (verified 2026-07-13): the sibling
  `tifxyz_normalized/` directory is an EMPTY 2×2 `-1` placeholder on both segments — it
  cannot be used; the point map is rebuilt from the obj (see unit 1). `flattened.obj`
  also exists but is not needed (`original.obj`'s `vt` already carries the flattening).
- `PHerc0332/volumes/20251211183505-2.399um-0.2m-78keV-masked.zarr` — 6-level pyramid,
  L0 shape (33592, 15761, 15761) uint8, 128³ chunks. **Sample level 2** (L0/4 ≈ 9.6µm
  effective — matches the detector's input scale, which consumes level-2 of the 2.4µm
  SOTA surface volumes).
- Validation reference: Scroll 1 segment `20230702185753` — its
  `tifxyz`/`original.obj` mesh (cached locally), the `PHercParis4` volume zarr, and the
  **released** SOTA surface volume for the same segment (ground truth to compare our
  render against).

## v1 scope (user-approved defaults)

- One 4096² level-2 region per Scroll-3 segment (central or content-rich by mask), plus
  one Scroll-1 validation region. NOT full segments (that is a later scale-up).
- Lives at `repro/sota_data/render_surface.py`, internal-first. Public/standalone
  release only after the validation gate passes.
- Bandwidth budget: a few GB total (tile-wise fetches at L2); storage under
  `local_data/rendered/` (gitignored via `local_data/`).

## Architecture (5 units)

1. **Point-map builder (obj → grid)** — parse `original.obj` with the existing
   `repro/sota_data/gt_register.parse_obj_vt` → `v[N,3]` (3D) and `vt[N,2]` (flattened
   UV). Build a regular render grid over the `vt` bounding box at a chosen output
   resolution (target ≈ 4096² for the region; grid step = vt-range / size), and
   interpolate the three coordinate channels with
   `scipy.interpolate.LinearNDInterpolator(vt, v)` evaluated on the grid → an
   `(H, W, 3)` point map, plus a validity mask (True where the interpolant is inside the
   mesh convex hull; NaN outside). This is the drop-in replacement for the (empty)
   tifxyz grid — everything downstream treats it identically. **Assert** the resulting
   point-cloud bounds fit inside the volume shape at level 2 (loud failure = coordinate-
   scale bug caught here, not in output). Build the interpolator once per segment; it is
   reused for both the region grid and any sub-tiling.
2. **Normals** — tangents via `np.gradient` on the x/y/z channel maps;
   `n = normalize(du × dv)`; propagate NaN where the grid is invalid. Normal SIGN is
   not assumed — it is fixed empirically by the validation harness (a sign flip
   reverses layer order).
3. **Sampler** — iterate 512² surface tiles; per tile build 26×512×512 sample
   coordinates `p + k·n` for k ∈ {−13..12} (unit steps in level-2 voxels); compute the
   tile's 3D bbox (+1 margin); fetch that subvolume from the L2 zarr (one ranged read,
   chunk-aligned); trilinear-sample with `scipy.ndimage.map_coordinates(order=1)`.
   Memory bound: bbox of an oblique 512² tile stays small at L2. Out-of-bounds samples
   are clamped and counted; > 1% clamped in a tile ⇒ loud warning in provenance.
4. **Writer** — emit a detector-format fragment following the layers/mask conventions
   of `repro/sota_data/qualitative.write_fragment` (`layers/17.tif..42.tif`, 26 uint8
   slices; `{frag_id}_mask.png` from grid validity) but implemented directly — NOT by
   calling `write_fragment`, because that helper also writes a zero-filled
   `_inklabels.png`, which on Scroll 3 would masquerade as a label. **No ink-label
   file is written — none exists; nothing may fabricate one.** Plus
   `{frag_id}_render_provenance.json` (segment, region, pyramid level, normal sign,
   spacing, bounds/clamp stats, input URIs).
5. **Validation harness (acceptance gate)** — render a 4096² region of Scroll-1
   `20230702185753` from its **`original.obj`** (the same one `parse_obj_vt` already
   consumes for registration) + the `PHercParis4` volume, using the identical
   obj→point-map→sample path, and compare depth-center slices against the **released**
   SOTA surface volume for the same region:
   - normalize scale/offset, compute NCC per depth slice;
   - test BOTH normal signs; the sign with higher center-slice NCC wins and is recorded;
   - **PASS gate: center-slice NCC ≥ 0.8** (papyrus texture must visibly match, not
     merely correlate). Below gate ⇒ renderer is wrong; do not proceed to Scroll 3.

## Operational sequence

1. Unit tests green (see Testing).
2. Validation harness on Scroll 1 → PASS required.
3. Render one region per Scroll-3 segment (region chosen from the grid-validity mask —
   maximize valid fraction, prefer center).
4. Arm C inference (`models/detector_xscroll_c/detector_epoch=11.ckpt`) over the two
   rendered fragments via the existing detector pipeline.
5. Qualitative report `reports/detector/scroll3_first_look.md`: input surface + ink
   prediction PNGs, honestly captioned — **no ground truth exists on Scroll 3**; the
   deliverable is texture-vs-letterform qualitative assessment plus the renderer
   itself. No reading claims without legible letterforms, and any letterform claim
   must state the cross-scroll context (arm C unseen-scroll lift ≈ 2.1, weak).

## Error handling

- Grid invalid points → mask, never silent zero-fill.
- Bounds/scale mismatch → assertion at load with both bounding boxes printed.
- S3 read failures → per-tile retry ×2 then hard fail (no partial fragments without a
  provenance note listing missing tiles).
- Every output carries provenance JSON; renders are reproducible from it.

## Testing

- **Unit:** point-map builder on a synthetic obj (a known tilted quad with vt = its
  projection → interpolated grid reproduces the analytic plane; points outside the hull
  are NaN-masked); normals on a synthetic tilted plane (analytic normal, both winding
  orders); sampler against a dense in-memory volume with a known analytic field
  (max abs error bound); writer round-trip (fragment readable by
  `detector.data.read_image_mask` path conventions, and NO `_inklabels.png` is written);
  bounds-assertion fires on a deliberately mis-scaled point map.
- **Integration (the gate):** Scroll-1 NCC harness as above.
- **Operational:** Scroll-3 renders complete with < 1% clamped samples; arm C runs
  end-to-end; report committed.

## Risks

- **obj coordinate scale / units unknown** until read (are `v` in level-0 voxels? a
  fixed offset?) — mitigated by the load-time bounds assertion and the Scroll-1 gate
  (both fail loudly, not silently). The Scroll-1 gate is the real safety net: the same
  obj→point-map path must reproduce a released surface volume before Scroll 3 is trusted.
- **Interpolation cost / holes** — `LinearNDInterpolator` builds a Delaunay triangulation
  over ~10⁵–10⁶ vt points; feasible once per segment. Regions of the flattened UV with no
  mesh coverage interpolate to NaN → masked (a finding about surface completeness, not a
  bug). If Delaunay memory/time is prohibitive on the full mesh, restrict vt/v to the
  region's UV bbox (+margin) before building the interpolator.
- **Depth spacing mismatch** (our unit-voxel steps vs the core team's render spacing)
  — detected by the validation NCC being high at center but degrading off-center;
  provenance records spacing; v1 accepts center-slice validation.
- **Scroll 3 surfaces may be poorly flattened/damaged** — that is a finding, not a
  failure; report it honestly.

## Out of scope (v1)

- Full-segment renders; GPU-accelerated sampling; standalone/public packaging;
  Scroll 2 (no segments exist in the bucket); any ink-label fabrication.
