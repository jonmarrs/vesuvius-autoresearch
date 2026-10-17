# Design and architecture review — the registration warp's alignment

Date: 2026-10-17. Baseline: `1b183c3a` (main after #101). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: how the registration places a region of the SOTA surface volume on the new mesh's grid, and how it samples
the correspondence field over that region: `register.warp_via_field`, the two copies of `_region_in_mesh`
(`register_run.py`, `gt_register.py`), their callers (`warp`, `warp_obj`, `gt_prep_fragment`,
`probe_orientation_ncc.py`), and what the reports, FINDINGS and the gate's derivation say about placement. The
previous review verified the misalignment and left the fix to this one
([GT registration review](DESIGN_ARCHITECTURE_REVIEW_2026-10-16_GT_REGISTRATION.md)).

## What changed

- **The region is placed on the mesh by the tifxyz convention, without rounding.**
  - The crop's bounds were rounded to whole mesh cells, and `warp_via_field` stretched the crop over the region with
    `cv2.resize`, which aligns pixel centres.
  - The tifxyz grid is vertex-aligned: vertex r sits at surface coordinate r / scale
    (`villa/lasagna/tifxyz_format.md`, sections 2 and 5.1), and villa's reader maps full-resolution index p to grid
    coordinate p × scale (`Tifxyz.__getitem__`). So the region's row y0 + i is mesh row (y0 + i) · sy, between two
    vertices.
  - On an identity registration in the geometry of segment `20230702185753` (7.91 µm mesh 776 × 559, about 16.3
    level-2 px a cell; region (4000, 2500) + 4096), the old warp placed every row 1.8–13.8 px off (7.8 on average)
    and every column 0.7–10.6 px off (5.6). The new one is within 0.05 px, at this geometry, at the 2.4 µm mesh's 5 px
    a cell, and at an unaligned origin.
  - `register.region_in_mesh` now returns the crop and the fractional row and column of each region pixel in it.
    `warp_via_field(..., coords=...)` samples the field there.
  - Both `_region_in_mesh` copies now call it; there is one implementation.
- **The field is sampled exactly, and only where it exists.**
  - `sample_field` interpolates the field between vertices, separably, in NumPy. An invalid vertex spoils only the
    pixels it has weight on.
  - A region running past the mesh's edge comes back zero there. Before, slicing shortened the crop and the resize
    stretched what was left over the whole region, mis-scaling it.
  - Without `coords`, field vertex j sits on output pixel j × stride, as `correspondence_field` computes it. The
    resize put it half a pixel off.
- **Every registration records the warp that made it.**
  - The `warp` and `warp_obj` stats and the GT prep record carry `warp_alignment`.
  - For a label without it, `validate` prints a warning and `score` heads its report with the warning.
  - Fine-tuning refuses a prep entry without it. Fragment writes refuse to overwrite, so an entry carrying it was
    written by the new warp.
- **Disclosures.**
  - The committed placements (held-out 32.0 px, train-exposed 46.6 px) were measured with the old warp. They are
    unchanged, and marked as to be re-measured, in:
    - both registered-GT reports (with the warning `score` now prints) and their JSON;
    - the offset report and its JSON;
    - the target disclosures in `register_run.py`;
    - FINDINGS' held-out table.
  - The offset report closed the residual offset "as an irreducible floor". Part of it is this error.
  - The gate's derivation (`MAX_PLACEMENT_OFFSET_L2PX`) notes the floor was measured with the old warp. The threshold
    is unchanged.
- **Small fixes.** The `warp` stats called its field "stride-8"; it is stride 1.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The warp misplaced every registered label by several px:** crop rounding and a pixel-centre stretch, 1.8–13.8 px in rows at 16.3 px a cell. It is in every committed GT score and in the measured placement floor. | Fractional, vertex-aligned crop; exact field sampling. Tests: identity registrations at two cell sizes and three origins; the old warp's error, measured. |
| P3 | **A region past the mesh edge was silently mis-scaled.** | Zeroed. Test. |
| P3 | **Old labels could not be told from new ones.** | `warp_alignment` recorded; validate and score warn; fine-tuning refuses. Tests. |
| P4 | Two copies of the crop; the stride-field half pixel; "stride-8". | One crop; fixed. Tests. |

All new and changed test cases fail on main.

## Observations for the owner (not changed)

- **The convention is the spec's, but the 7.91 µm mesh does not index the volume exactly.**
  - The pipeline maps the level-2 volume onto the 7.91 µm mesh in proportion to its extent. The offset report
    showed that grid sits on a different scan's lattice, so this mapping is an approximation of its own.
  - Taking vertex 0 at surface 0 with extent cols / scale is the tifxyz convention, and it is what this change uses.
  - If that mapping were centre-aligned instead, the old warp's error would be the rounding alone: up to 6.1 px in
    rows and 7.0 in columns, 3.0 and 2.9 on average. And this fix would add half a cell, 7.65 px.
  - villa's `upsample_coordinates` (`tifxyz/upsampling.py`) resizes centre-aligned while describing itself as matching
    `QuadSurface::gen`'s `warpAffine`, which is vertex-aligned. Rendering a layer through the 2.4 µm mesh (exactly 5
    level-2 px a cell) and locating it against the released volume to a fraction of a cell would settle which one
    the release follows.
- **Re-measuring needs the meshes.** Re-run `warp_obj` and `validate` on the held-out target, and re-run the
  placement probes. The labels and prep fragments already on disk were made by the old warp. Prep refuses to
  overwrite them, so delete them first.
- **The 48 px threshold** came from a floor that included this error. Whether to tighten it after re-measuring is
  the owner's call.
- **The offset report's rounding estimate** of (+11.7, −12.0) px at the region centre is not reproduced by the model
  here. Its derivation is not committed.
- **The texture side is unchanged.** `row = H - v` reads vt as pixel coordinates with a bottom-left origin; a
  half-pixel convention there is under a label pixel.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), fsspec 2026.9.0 (no s3fs), pytest, Ruff and
mypy.

- Baseline: main `1b183c3a`: 42 failed, 2506 passed, 21 skipped, 1 xfailed, 2 errors. The failures and errors are
  environmental: no scroll data, no CUDA, no villa data files, and no s3fs or tensorstore.
- Branch: _running at this commit; recorded in the next._
- `tests/test_sota_warp_alignment.py`: 10 passed. It cannot be imported on main.
- The registration tests that need s3fs to collect, run with a stand-in: 72 passed (`test_sota_warp_alignment`,
  `test_sota_register`, `test_sota_register_targets`, `test_sota_gt_register`, `test_gt_finetune_prep_superseded`,
  `test_retirement_shared`, `test_sota_registration_gates`). The three changed cases fail on main.
- Cost: a 4096² warp from the 253 × 254 crop takes 1.1 s (0.04 s before) and about 44 MB more peak memory.

New tests (`tests/test_sota_warp_alignment.py`, added to the standard suite):
- `test_an_identity_registration_lands_on_its_own_pixels` (two meshes, three origins);
- `test_a_stride_field_is_read_from_its_first_pixel`;
- `test_an_invalid_vertex_spoils_only_the_pixels_it_weighs_on`;
- `test_a_region_past_the_mesh_edge_is_zeroed_not_extended`;
- `test_the_old_crop_and_stretch_was_several_pixels_off`.

Changed: `test_both_region_croppers_are_the_shared_one` (new, targets file),
`test_a_label_from_the_old_warp_is_flagged` (new, gates file), `test_fine_tuning_rechecks_every_kept_region` (a
pre-fix entry is refused).

Not verified: anything against the meshes, labels or bucket (none here), so no placement was re-measured and no
score re-run.
