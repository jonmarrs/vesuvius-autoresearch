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
  - Take an identity registration in the geometry of segment `20230702185753`: the 7.91 µm mesh is 776 × 559,
    about 16.3 level-2 px a cell, and the region is (4000, 2500) + 4096. The old warp shifted content down and right
    on average:
    - rows 1.8–13.8 px, 7.8 on average;
    - columns 0–18.3 px, 5.6 on average; away from the edges, where `cv2.resize` clamps, 0.7–10.6 px;
    - in 2D, 1.8–22.9 px, 10.1 on average.

    These figures supersede the previous review's "3 to 14 px, 8.4 on average".
  - The new warp is within 0.05 px, at this geometry, at the 2.4 µm mesh's 5 px a cell, and at an unaligned origin.
  - `register.region_in_mesh` now returns the crop and the fractional row and column of each region pixel in it.
    `warp_via_field(..., coords=...)` samples the field there.
  - Both `_region_in_mesh` copies now call it; there is one implementation.
- **The field is sampled exactly, and only where it exists.**
  - `sample_field` interpolates the field between vertices, separably, in NumPy. An invalid vertex spoils only the
    pixels it has weight on.
  - A region running past the mesh's edge comes back zero there. Before, slicing shortened the crop and the resize
    stretched what was left over the whole region, mis-scaling it.
  - `coords` is now required by `warp_via_field`, `sample_field` and `register_label_to_region`. A caller that
    drops it fails instead of silently falling back to stretching the field.
    - `stride_coords` gives a stride-k field's coordinates: vertex j on pixel j × k.
    - `cv2.resize` had put that vertex (k − 1) / 2 px off, 0.5 px at the test's stride 2 and 3.5 at the default
      stride 8.
- **Every registration records the warp that made it.**
  - The `warp` and `warp_obj` stats and the GT prep record carry `warp_alignment`.
  - For a label without it, `validate` prints a warning and `score` heads its report with the warning.
  - Fine-tuning refuses a prep entry without it. Fragment writes refuse to overwrite, so an entry carrying it was
    written by the new warp.
  - The two placement probes read ScrollGT's exported labels, which carry no such record, and now print that
    caveat.
- **Disclosures: the published placements were measured through the shift, and it moved them.**
  - The shift moves the label's agreement peak by about (−8, −6) px. On the identity registration above, the old
    warp's peak is (−8, −6); the new one's is (0, 0). Re-warping should therefore move each committed peak by about
    (+8, +6): rows between −0.5 and +15.8 px, and the same for columns.
  - **The held-out target**, (31, −8) = 32.0 px, most likely goes to about (39, −2) = 39 px, and at worst 47.5 px, just
    under the 48 px gate. Its "floor" is likely larger than published, not smaller.
  - **The train-exposed target**, (−18, −43) = 46.6 px, goes to about (−10, −37) = 38 px.
  - **Gate verdicts:**
    - `20231005123336` (57.5 px) can only grow, because its dy (+56) is positive.
    - `20230702185753` y7000_x4000 (53.3 px) may pass, but it is on the retired segment.
    - So no verdict in the GT-exhaustion report or `gt_finetune.py` changes.
  - Marked, with figures unchanged and the expected direction stated:
    - both registered-GT reports and their JSON (with the warning `score` now prints);
    - the offset report (its top note, and its "there isn't one" convention bug);
    - the GT-exhaustion report;
    - the target disclosures in `register_run.py`;
    - the gate's derivation (`MAX_PLACEMENT_OFFSET_L2PX`);
    - the `gt_finetune.py` docstring;
    - FINDINGS' held-out table;
    - `tools/placement_check/README.md`.
  - All of this assumes the vertex convention, which is unverified against the release render (see below). The
    notes say so.
- **Small fixes.** The `warp` stats called its field "stride-8"; it is stride 1.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The warp shifted every registered label several px**: crop rounding and a pixel-centre stretch, 1.8–13.8 px in rows and up to 18.3 in columns at 16.3 px a cell. It is in every committed GT score and in the placement floor the 48 px gate was derived from. | Fractional, vertex-aligned crop; exact field sampling; `coords` required. Tests: identity registrations at two cell sizes and three origins; end to end through `warp_obj` and `gt_prep_fragment`; the old warp's error, measured. |
| P2 | **Its effect on the published placements was unstated**, and it runs against the flagship. | Direction and expected values disclosed wherever the placements are cited. |
| P3 | **A region past the mesh edge was silently mis-scaled.** | Zeroed. Test. |
| P3 | **Old labels could not be told from new ones.** | `warp_alignment` recorded; validate and score warn; fine-tuning refuses; the probes caveat ScrollGT. Tests, including the score report. |
| P4 | Two copies of the crop; the stride-field offset; "stride-8". | One crop; fixed. Tests. |

## Observations for the owner (not changed)

- **The convention is the spec's, but it is not verified against the release.**
  - The pipeline maps the level-2 volume onto the 7.91 µm mesh in proportion to its extent. The offset report
    showed that grid sits on a different scan's lattice, so this mapping is an approximation of its own.
  - Taking vertex 0 at surface 0 with extent cols / scale is the tifxyz convention, and it is what this change uses.
  - If that mapping were centre-aligned instead, the old warp's error would be the rounding alone: up to 6.1 px in
    rows away from the edges, 3.0 on average, and 2.9 in columns. This fix would then add (s − 1) / 2 = 7.65 px:
    half a cell, 8.15 px, less half a pixel.
  - villa's `upsample_coordinates` (`tifxyz/upsampling.py`) resizes centre-aligned while describing itself as matching
    `QuadSurface::gen`. That C++ source is not in the pinned checkout.
  - The check that would settle it: render a layer through the 2.4 µm mesh (exactly 5 level-2 px a cell) and locate it
    against the released volume to a fraction of a cell. It is worth doing before re-scoring.
- **Re-measuring needs the meshes and ScrollGT.**
  - Re-run `warp_obj` and `validate` on the held-out target. The labels and prep fragments already on disk were made
    by the old warp, and prep refuses to overwrite them, so delete them first.
  - The placement probes and `make_alignment_evidence.py` read ScrollGT's exported `gt_ink.png`. Nothing here writes
    that file, so re-export it from the re-warped registration before re-running them. The same holds for the
    ink-ablation reports that use ScrollGT's registered GT.
- **The 48 px threshold** came from a floor measured through this shift. Re-warped, the held-out target is expected
  near 39 px, and at worst 47.5. Revisiting the threshold after re-measuring is the owner's call.
- **Records left as written:**
  - `labeled_segment_availability.json`, which the availability probe builds from the committed JSON placements;
  - `PRIZE_CORRECTION_2026-08_DRAFT.md`, a dated filing.
- **The offset report's rounding estimate** of (+11.7, −12.0) px at the region centre is not reproduced here under
  either convention. Its derivation is not committed.
- **The texture side is unchanged.** `row = H - v` reads vt as pixel coordinates with a bottom-left origin; a
  half-pixel convention there is under a label pixel.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), fsspec 2026.9.0 (no s3fs), pytest, Ruff and
mypy.

- Baseline: main `1b183c3a`: 42 failed, 2506 passed, 21 skipped, 1 xfailed, 2 errors. The failures and errors are
  environmental: no scroll data, no CUDA, no villa data files, and no s3fs or tensorstore.
- Branch: see the PR. The suite's result is recorded there for the final commit.
- The registration tests that need s3fs to collect, run with a stand-in: 76 passed (`test_sota_warp_alignment`,
  `test_sota_register`, `test_sota_register_targets`, `test_sota_gt_register`, `test_gt_finetune_prep_superseded`,
  `test_retirement_shared`, `test_sota_registration_gates`).
- On main:
  - `test_sota_warp_alignment` cannot be imported (no `region_in_mesh`).
  - The new and changed cases in the gates file fail, some at the import of `WARP_ALIGNMENT`.
  - The changed `test_region_in_mesh_tracks_the_segments_own_shape` passes.
- Mutations, each caught by at least one test:
  - the half-cell (centre) convention;
  - a rounded crop start;
  - dropping `warp_alignment` from the `warp_obj` stats or the prep record;
  - dropping the score banner.
- Cost: a 4096² warp from the 253 × 254 crop takes 1.2–1.6 s, against 0.25–0.27 s for main's. Peak traced memory
  is 64 MiB higher, 416 against 352.

New tests:
- `tests/test_sota_warp_alignment.py`, added to the standard suite:
  - `test_an_identity_registration_lands_on_its_own_pixels` (two meshes, three origins);
  - `test_a_stride_field_is_read_from_its_first_pixel` (strides 2 and 8, a size not a multiple of 8);
  - `test_an_invalid_vertex_spoils_only_the_pixels_it_weighs_on`;
  - `test_a_region_past_the_mesh_edge_is_zeroed_not_extended`;
  - `test_the_old_crop_and_stretch_was_several_pixels_off`.
- `tests/test_sota_registration_gates.py`:
  - `test_warp_obj_gives_an_identity_scene_back_unmoved`;
  - `test_gt_prep_gives_an_identity_scene_back_unmoved`;
  - `test_a_score_of_an_old_warp_label_says_so`;
  - `test_a_label_from_the_old_warp_is_flagged`;
  - `test_both_region_croppers_are_the_shared_one`.

Changed: `test_fine_tuning_rechecks_every_kept_region` now checks that a pre-fix entry is refused. The stride-field
roundtrip in `test_sota_register` and the GT register test now pass `coords`.

Not verified: anything against the meshes, labels, ScrollGT or bucket (none here), so no placement was re-measured
and no score re-run.
