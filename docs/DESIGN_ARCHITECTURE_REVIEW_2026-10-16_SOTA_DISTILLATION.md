# Design and architecture review — the SOTA open-data and distillation tooling

Date: 2026-10-16. Baseline: `c927cee7` (main after #93). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `repro/sota_data/`'s path from the open bucket to a detector fragment and a measured student, which the
README and FINDINGS list among the project's tooling. These are `discover.py`, `fetch.py`, `convert.py`,
`qualitative.py`, `fragment.py`, `distill_prep.py`, `distill_run.py`, `xscroll_run.py` and `evaluate.py`, and the
claims FINDINGS, the README and the research paper make from their reports. The surface renderer was reviewed on
2026-10-05. The ground-truth registration (`register*.py`, `gt_register.py`, `gt_finetune.py`) is a later round.

## What changed

- **`fetch.py` fetches what it says, where it says.**
  - It created `out_dir`, then had fsspec copy the whole segment prefix into it recursively. Into an existing
    directory fsspec copies the directory itself, as `out_dir/<segment>/`, so
    `convert_surface_volume(fetch_segment(prefix, out), …)` found no layers.
  - It also copied everything under the prefix. A SOTA segment's includes its surface-volume zarrs: about
    200 GB at level 0.
  - It now fetches `layers/` (its contents, into `out_dir/layers`) and the `*inklabels*` and `*mask*` files, and
    refuses a prefix without `layers/`. A test fetches from an in-memory bucket that also holds a zarr, then
    converts the result.
- **Labels are no longer stretched onto the layers.**
  - `convert.py` accepted a label or mask up to 20% off the layers' size and resized it onto the grid. A label of
    another crop or scale was spread over the volume, misregistered everywhere, while the module's docstring
    promised a loud failure.
  - It now uses the labeled dataset's rule (2 px, `LABEL_SHAPE_TOLERANCE_PX`, which a test keeps equal;
    released segments differ by 0 or 1 px): within it, crop or zero-pad at the origin; beyond it, refuse.
  - Rows or columns padded onto the label are now outside the mask too. Without a mask file they were inside it,
    so they counted as known negatives.
  - `distill_prep` had the same defect for teachers. It scaled each axis separately and accepted up to 20%
    difference between them, then resized: a teacher 9% short in x (the size of the 2026-08-07 registration
    error) passed. A teacher must now be one integer scale of the level (or region) on both axes, within the
    pyramid's rounding (`same_integer_scale`). The committed Scroll-1 teachers are exactly 4× their level-2
    shape.
- **The distillation reports say which rows were selected on the region they are reported on.**
  - Both runners keep every epoch's checkpoint and report the best by val_f1 on the held-out region, which is the
    region they report on.
  - The Phase-2 report's note said AP and ROC-AUC "are threshold-free and unaffected by threshold tuning", and
    FINDINGS and the research paper carried it as "unaffected" by the selection. Being threshold-free spares a
    metric threshold tuning, not epoch selection: the student's row is the best of 12 epochs on that region,
    and its metrics are optimistic.
  - The cross-scroll report had been corrected by hand to call **arm B vs the legacy detector** the robust
    comparison, "which needs no selection asymmetry to hold", while its generator still wrote "diversity is the
    only variable".
    - Both are wrong. Arm B's epoch was chosen on the PHerc-1667 region, and arm A's and the legacy detector's
      were not, so every comparison with arm B there includes a selected row.
    - The selection-free comparison on that region is arm A vs the legacy detector.
    - The arm-C report's "asymmetry-free anchor (arm vs legacy)" has the same flaw.
  - The same-scroll rows run the other way. Arm A is the Phase-2 best epoch, chosen on the Phase-2 Scroll-1
    region that "arm A on Phase-2 held-out Scroll-1" reports. So the ~11% same-scroll cost of diversity is
    overstated.
  - What the runners now do:
    - their notes and caveats say all this, whether or not a provenance file exists;
    - besides the best epoch, they report the **last epoch**, a fixed rule and so selection-free, and record
      every epoch's scores and the selection in the JSON;
    - `epoch_checkpoints` orders checkpoints by the epoch in their name. A Lightning `-v1` name made the old sort
      key raise.
- **The teacher's file is recorded.** `fetch_teacher` takes the first `.tif` by name under a segment's
  `ink-detection/`, but provenance recorded only the teacher's dtype and range.
  - A fetch now writes `<teacher>.tif.source.json`, with the file and the candidates, and the reports name the
    file.
  - A teacher cached before this has no record, and the report says "source not recorded".
- **Documents corrected:**
  - FINDINGS: the Phase-2 "unaffected"; the cross-scroll framing; "diversity was the only variable"; the
    same-scroll cost; arm C's "bought back".
  - The research paper's Phase-2 caveat and its cross-scroll "selection-asymmetry-free anchor" and "controlled
    diversity result".
  - The README's diversity headline.
  - The three committed reports' caveats, each marked as corrected. Their numbers are unchanged.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The selection caveats understated or misplaced the bias.** Phase 2: "unaffected". Cross-scroll: "arm B vs legacy needs no selection asymmetry", "diversity the only variable", and the generator would have restored the last over the hand-corrected report. | Caveats, generators, FINDINGS, paper, README and reports corrected; a selection-free last-epoch row and per-epoch scores from now on. Tests: both generated reports. |
| P2 | **Labels and teachers were stretched onto the grid** when up to 20% off (`convert.py`), or up to 20% apart between axes (`distill_prep`). | 2 px crop/pad (convert); one integer scale (prep). Tests: padded, refused, per-axis teacher refused, pyramid rounding accepted. |
| P3 | **`fetch.py` nested the segment one directory down, and fetched the whole prefix.** | Layers, labels and mask only, into `out_dir`. Test: in-memory bucket with a zarr, then convert. |
| P3 | **Rows padded onto a label counted as negatives** when there was no mask file. | Outside the mask. Test. |
| P3 | **The teacher's file was not recorded.** | Recorded at fetch; in provenance and the report line. Test. |
| P4 | A Lightning `-v1` checkpoint name broke the measure step's sort. | `epoch_checkpoints`. Test. |

## Review of the PR, and what it changed

The independent review of the first head (`e8b6c5d6`) confirmed the fetch semantics, against fsspec's own `_get`
as s3fs uses it. It also confirmed convert's fit (the loader's), "best of 12 epochs" (`epochs` 12, `save_top_k=-1`),
the 65-slice → 19–44 window, and that the new report keys break no reader.

| Finding | Outcome |
| --- | --- |
| P2: "arm B vs the legacy baseline needs no selection asymmetry" — copied from the hand-corrected report into the generator, a test, FINDINGS and this doc — is false: arm B is the selected row. | Corrected everywhere it appeared, with the arm-C "anchor", FINDINGS' and the paper's framing, and the reports. A selection-free last-epoch row added. |
| P3: the same-scroll rows have the reverse asymmetry (arm A selected on the Phase-2 region), so the ~11% cost is overstated. | Said in the generator, the reports and FINDINGS. |
| P3: README's "1.22 → 2.12" and the paper's "controlled diversity result" were left. | Corrected. |
| P3: `distill_prep` stretches teachers 20% apart per axis, the defect removed from convert; this doc called it sound. | One integer scale; tested. |
| P4: `fetch` copies the whole prefix (a segment's zarrs); padded label rows count as negatives without a mask; the duplicated tolerance constant; the fixture leaves its module bound on the package; "every column" includes the label's positive_rate; a null source is silent in the report; the `-v1` sort crash; the s3fs note omits `test_sota_register_targets`; the depth claim below; "disjoint" means distinct IDs; `test_sota_distill_prep.py` left unformatted. | All corrected. |
| P4: an old cached teacher never gets a source record; the zarr `extract_region` picks is not recorded; stale checkpoints in a reused `model_dir` count towards "best of N"; labels are not checked for a 0/1 encoding; the committed JSONs have no selection record. | Left; noted below. |

## Reviewed and sound

- **`fragment.write_fragment_artifact`** stages layers, mask, label and metadata in a hidden directory beside the
  destination and publishes with one rename. It refuses an existing id, including a broken symlink, and validates
  every layer before writing. `to_uint8` refuses non-finite pixels, unsupported dtypes and floats outside [0, 1]
  or [0, 255].
- **`distill_prep`, otherwise.** An empty region is refused with its likely cause. The label is the binarized
  teacher, and every report labels its metrics agreement-with-teacher.
- **Train and held-out segment IDs are distinct** in Phase 2 and in every cross-scroll arm. Whether segments of
  one scroll share papyrus was not checked.
- **Zarr choice.** `extract_region` prefers the 2.4 µm volume explicitly, because a `1.129um…` name sorts first
  on segments that ship both (checked by name, not against the bucket).

## Observations for the owner (not changed)

- **The bias's size has not been measured.**
  - The committed numbers are the selected rows.
  - A re-run of `measure` (GPU, the trained checkpoints) now prints the last-epoch rows and every epoch's scores.
  - Choosing the epoch on a separate region would remove the bias, but changes the experiment.
- **Depth windows.**
  - `convert.py` (tiff layers) names the middle 26 slices 17–42, whatever their source depth; for a 65-slice
    segment that is source 19–44. The detector's training fragments were read at source 17–42.
  - The zarr path takes the middle 26 of the level-2 volume, whose depth is not downsampled: 41–66 of 109
    slices, about 62 µm at 2.4 µm a slice. The legacy detector's training fragments' slice spacing was not
    checked here; the review's "about 3× deeper" used `um_per_px`, the lateral pixel size.
  - Nothing records the source indices. The students train and are measured on the same convention, so their
    numbers are consistent with each other.
- **Provenance still missing:**
  - which zarr `extract_region` read;
  - the source of teachers cached before this change (an ETag or size match against the bucket listing could
    recover it);
  - the selection, in the committed JSONs.
- **`model_dir` reuse.** Stale checkpoints from an earlier run in the same `model_dir` are counted, and can be
  chosen.
- **`convert.py` does not check the label's encoding.** A 0/1 label becomes all-negative after the detector's
  `/255`.
- **`evaluate.py`** writes `reports/detector/sota_scroll1_measurement.*` for whatever segment it is given, under a
  hard-coded baseline row for `20230702185753`. Nothing committed came from it.
- **The dated records repeat the old wording**: the lab notebook (2026-07-03) and the July prize filings. They are
  records of what was said then, and are left as they are.
- **`s3fs` is declared but not installed here.**
  - `test_sota_gt_register`, in the standard suite, fails to collect in this environment: one of the baseline's
    2 errors, `test_zarr_loading` (tensorstore) being the other.
  - So do `test_sota_xscroll` and `test_sota_register_targets`, which are outside the suite.
  - The new tests use a stand-in and remove it afterwards.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), fsspec 2026.9.0 (no s3fs), pytest, Ruff and
mypy.

- Baseline: main `c927cee7`, 42 failed, 2478 passed, 21 skipped, 1 xfailed, 2 errors (the run of `3c90dc4f`, whose
  tree is the same but for its review doc's result lines). The failures and errors are environmental.
- Branch, PR first head (`e8b6c5d6`): 42 failed, 2486 passed, 21 skipped, 1 xfailed, 2 errors. Same set; the 8
  extra passes are its new test cases. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped (no training data).
- Branch, after the PR review's fixes: _running at this commit; recorded in the next._
- `tests/test_sota_convert.py`: 13 passed; `tests/test_sota_distill_prep.py`: 14 passed. Every new case fails on
  main; those added after the review fail on the first head too.
- The README- and FINDINGS-reading tests: 40 passed.
- Ruff check on the changed files: clean.
  - Three of the five changed modules were not Ruff-formatted on main, and the edits follow their style rather
    than reformatting them.
  - `tests/test_sota_distill_prep.py` is formatted.

New tests:
- `tests/test_sota_convert.py`:
  - `test_a_label_within_two_px_is_padded_onto_the_grid_not_stretched`;
  - `test_rows_padded_onto_the_label_are_outside_the_mask`;
  - `test_the_tolerance_is_the_labeled_datasets`;
  - `test_a_label_or_mask_of_another_crop_or_scale_is_refused` (label, mask);
  - `test_fetch_puts_the_segment_where_convert_reads_it`.
- `tests/test_sota_distill_prep.py`:
  - `test_a_teacher_at_another_scale_per_axis_is_refused`;
  - `test_a_pyramid_levels_rounding_is_accepted`;
  - `test_the_selection_note_names_epoch_selection`;
  - `test_a_fetched_teacher_records_its_bucket_file`;
  - `test_the_distillation_report_states_how_the_student_was_selected`;
  - `test_checkpoints_are_ordered_by_epoch_whatever_lightning_appends`;
  - `test_the_cross_scroll_report_says_which_rows_were_selected_on_it`.

Not verified: anything against the real bucket (no network use, no s3fs), and the GPU runs.
