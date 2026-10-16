# Design and architecture review — the SOTA open-data and distillation tooling

Date: 2026-10-16. Baseline: `c927cee7` (main after #93). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `repro/sota_data/`'s path from the open bucket to a detector fragment and a measured student, which the
README and FINDINGS list among the project's tooling. These are `discover.py`, `fetch.py`, `convert.py`,
`qualitative.py`, `fragment.py`, `distill_prep.py`, `distill_run.py`, `xscroll_run.py` and `evaluate.py`, and the
claims FINDINGS and the research paper make from their reports. The surface renderer was reviewed on 2026-10-05.
The ground-truth registration (`register*.py`, `gt_register.py`, `gt_finetune.py`) is a later round.

## What changed

- **`fetch.py` puts the segment where its return value says.**
  - It created `out_dir`, then had fsspec copy the segment directory into it recursively. Into an existing
    directory, fsspec copies the directory itself, as `out_dir/<segment>/`.
  - So `convert_surface_volume(fetch_segment(prefix, out), …)` found no layers.
  - A trailing `/` copies the contents instead. A test fetches from an in-memory bucket and converts the result.
- **`convert.py` no longer stretches a label onto the layers.**
  - It accepted a label or mask up to 20% off the layers' size and resized it onto the grid.
  - A label of another crop or scale was thus spread over the volume, misregistered everywhere, while the
    module's docstring promised a loud failure on a shape mismatch.
  - It now uses the labeled dataset's rule (`LABEL_SHAPE_TOLERANCE_PX`, 2 px; released segments differ by 0 or
    1 px): within it, crop or zero-pad at the origin; beyond it, refuse.
- **The distillation reports say how the student was chosen.**
  - Both runners pick the student's epoch by val_f1 on the held-out region they then report it on.
  - The Phase-2 report's note said AP and ROC-AUC "are threshold-free and unaffected by threshold tuning". True,
    but FINDINGS and the research paper carried it as "unaffected" by the selection. Being threshold-free spares
    a metric threshold tuning, not epoch selection: the student's row is the best of 12 epochs on that region,
    optimistic in every column.
  - The note now says so, and it is printed whether or not the provenance file exists (it was printed only
    beside it). The report's JSON records the selection.
  - The cross-scroll report had been corrected by hand ("an advantage arms A and the legacy baseline do not
    get"), but its generator still wrote "training-scroll diversity is the only variable". A re-run of
    `measure` would have restored the claim; the generator now writes the corrected caveat, with its numbers.
- **The teacher's source is recorded.** `fetch_teacher` takes the first `.tif`, by name, under a segment's
  `ink-detection/`. The provenance recorded the teacher's dtype and range but not which released file it was. A
  fetch now writes `<teacher>.tif.source.json` (the file and the candidates), and the reports name it.
  - A teacher cached before this records none, and says so (`source: null`).
  - Both runners now build provenance through one function, and the report line through another.
- **Documents corrected:**
  - FINDINGS' Phase-2 "AP/ROC-AUC … unaffected", and its cross-scroll "diversity was the only variable";
  - the research paper's Phase-2 caveat;
  - the committed Phase-2 report's note, marked as corrected. Its numbers are unchanged.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The selection caveat understated the bias, and FINDINGS and the paper carried it as "unaffected".** Every reported student number is the best of N epochs on the region it is reported on. | Note, JSON record, FINDINGS, paper and report corrected. Test: the report says it, without a provenance file. |
| P2 | **The cross-scroll generator would restore "diversity is the only variable"** over the hand-corrected report. | It writes the corrected caveat. Test: the generated report. |
| P2 | **`convert.py` resized a label up to 20% off onto the layers.** | 2 px, crop/pad, else refuse. Tests: a 1 px short label is padded and stays registered; a 10% short label or mask is refused. |
| P3 | **`fetch.py` nested the segment one directory down**, so the fetch-then-convert path failed. | Trailing `/`. Test: fetch from an in-memory bucket, then convert. |
| P3 | **The teacher's file was not recorded.** | Recorded at fetch; in provenance and the report line. Test. |

All eight new test cases fail on main.

## Reviewed and sound

- **`fragment.write_fragment_artifact`** stages layers, mask, label and metadata in a hidden directory beside the
  destination, publishes with one rename, refuses an existing id (including a broken symlink) and validates every
  layer before writing. `to_uint8` refuses non-finite pixels, unsupported dtypes and floats outside [0, 1] or
  [0, 255].
- **`distill_prep`.** The teacher crop scales the box per axis, and an anisotropic teacher (more than 20%
  different scale per axis: an axis swap or a wrong crop) is refused. An empty region is refused with the likely
  cause. The label is the binarized teacher, and every report labels its metrics agreement-with-teacher.
- **Train/held-out disjointness.** The Phase-2 training segments (`20230702185753`, `20231005123336`) and the
  held-out one (`20231210121321`) are distinct, as are the cross-scroll arms' training fragments and the
  PHerc-1667 region.
- **Zarr choice.** `extract_region` prefers the 2.4 µm volume explicitly, because sorting picks a 1.129 µm scan
  on segments that ship both.

## Observations for the owner (not changed)

- **The student's epoch is chosen on the test region.** The reports now say so. Choosing it on a separate region
  of the held-out segment, or on a training-segment region, would remove the bias, but needs a GPU re-run, and
  changes the experiment. The cross-scroll report's asymmetry-free comparison (arm vs the legacy detector) stands
  either way. The size of the bias has not been measured.
- **`convert.py` and the zarr extraction name the window 17–42 whatever its source depth.** They take the middle
  26 slices (for a 65-slice segment, source 19–44), while the detector's training fragments were read at source
  17–42. Nothing records the source indices. The distilled students train and are measured on the same
  convention, so their numbers are consistent. The legacy detector, on SOTA data, reads a window two slices higher
  than it was trained on: one more difference beside the re-flattening.
- **`evaluate.py`** writes `reports/detector/sota_scroll1_measurement.*` for whatever segment it is given, under a
  hard-coded baseline row for `20230702185753`. Nothing committed came from it.
- **The dated records repeat the old wording**: the lab notebook (2026-07-03) and the July prize filings. They are
  records of what was said then, and are left as they are.
- **`s3fs` is declared but not installed here**, so `test_sota_gt_register` (in the standard suite) and
  `test_sota_xscroll` fail to collect in this environment. The new tests use a stand-in.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), fsspec 2026.9.0 (no s3fs), pytest, Ruff and
mypy.

- Baseline: main `c927cee7`, 42 failed, 2478 passed, 21 skipped, 1 xfailed, 2 errors (the run of `3c90dc4f`, whose
  tree is the same but for its review doc's result lines). The failures and errors are environmental.
- Branch: _running at this commit; recorded in the next._
- `tests/test_sota_convert.py`: 11 passed; `tests/test_sota_distill_prep.py`: 11 passed. The 8 new test cases
  fail on main.
- The README- and FINDINGS-reading tests: 40 passed.
- Ruff check on the changed files: clean. Three of the four changed modules were not Ruff-formatted on main; the
  edits follow their style rather than reformatting them.

New tests:
- `tests/test_sota_convert.py`: `test_a_label_within_two_px_is_padded_onto_the_grid_not_stretched`,
  `test_a_label_or_mask_of_another_crop_or_scale_is_refused` (label, mask),
  `test_fetch_puts_the_segment_where_convert_reads_it`;
- `tests/test_sota_distill_prep.py`: `test_the_selection_note_names_epoch_selection`,
  `test_a_fetched_teacher_records_its_bucket_file`,
  `test_the_distillation_report_states_how_the_student_was_selected`,
  `test_the_cross_scroll_report_keeps_its_corrected_caveat`.

Not verified: anything against the real bucket (no network use, no s3fs), and the GPU runs.
