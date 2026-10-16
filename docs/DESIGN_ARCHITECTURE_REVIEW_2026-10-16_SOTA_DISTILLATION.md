# Design and architecture review — the SOTA open-data and distillation tooling

Date: 2026-10-16. Baseline: `c927cee7` (main after #93). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `repro/sota_data/`'s path from the open bucket to a detector fragment and a measured student, which the
README and FINDINGS list among the project's tooling. These are `discover.py`, `fetch.py`, `convert.py`,
`qualitative.py`, `fragment.py`, `distill_prep.py`, `distill_run.py`, `xscroll_run.py` and `evaluate.py`, and the
claims that FINDINGS, the README, the research paper and the research strategy make from their reports. The surface
renderer was reviewed on 2026-10-05. The ground-truth registration (`register*.py`, `gt_register.py`,
`gt_finetune.py`) is a later round.

## What changed

- **`fetch.py` fetches what it says, where it says.**
  - It created `out_dir`, then had fsspec copy the whole segment prefix into it recursively. Into an existing
    directory fsspec copies the directory itself, as `out_dir/<segment>/`, so
    `convert_surface_volume(fetch_segment(prefix, out), …)` found no layers.
  - It also copied everything under the prefix. A SOTA segment's prefix includes its surface-volume zarrs: about
    200 GB at level 0.
  - It now fetches `layers/` (its contents, into `out_dir/layers`) and the files that `convert.py`'s
    case-sensitive globs read (`*inklabels*`, `*mask*`). It refuses a prefix without `layers/`, and a matching
    name that is a directory: fsspec's non-recursive get would skip one silently, and convert would then use an
    all-valid mask.
- **Labels and teachers are no longer stretched onto the grid.**
  - `convert.py` accepted a label or mask up to 20% off the layers' size and resized it onto the grid. A label of
    another crop or scale was spread over the volume, misregistered everywhere, while the module's docstring
    promised a loud failure.
  - It now uses the labeled dataset's rule (2 px, `LABEL_SHAPE_TOLERANCE_PX`, which a test keeps equal;
    released segments differ by 0 or 1 px): within it, crop or zero-pad at the origin; beyond it, refuse.
  - Rows or columns padded onto the label are now outside the mask too. Without a mask file they were inside it,
    so they counted as known negatives.
  - `distill_prep` had the same defect for teachers. It scaled each axis separately and accepted up to 20%
    difference between them, then resized: a teacher 9% short in x (the size of the 2026-08-07 registration
    error) passed.
  - A teacher must now be one pyramid scale (a power of two, k) of the level, and of the region, on both axes,
    within k px a side (`same_integer_scale`). k is taken from the better-resolved axis.
  - Only the Scroll-1 inputs were confirmed against this: their teachers are exactly 4× their level-2 shapes.
    The other committed teachers pass against their own shape / 4, which assumes they are at level 0; their
    level-2 shapes are not in the repository. A teacher padded beyond the rounding (for instance to a tile
    multiple) is now refused.
- **The distillation reports say which rows were selected on the region they are reported on.**
  - Both runners keep every epoch's checkpoint (`save_top_k=-1`, 12 epochs) and report the best by val_f1 on the
    held-out region, which is also the region they report on. Training validates on it each epoch, but chooses
    nothing by it: the schedule is fixed and the checkpoint monitor is the training loss.
  - **Phase 2.**
    - The report's note said AP and ROC-AUC "are threshold-free and unaffected by threshold tuning", and FINDINGS
      and the research paper carried it as "unaffected" by the selection.
    - Being threshold-free spares a metric threshold tuning, not epoch selection. The student's row is the best
      of 12 epochs on that region (epoch 9), so it is optimistic.
  - **Cross-scroll: three claims were wrong.**
    - The arm-B report had been corrected by hand to call **arm B vs the legacy detector** the robust
      comparison, "which needs no selection asymmetry to hold", while its generator still wrote "diversity is
      the only variable". Arm B's row is the one chosen on the PHerc-1667 region (epoch 7 of 12), so every
      comparison with it there favours B.
    - The arm-C report called arm C's row selected too, and "arm vs legacy" the asymmetry-free anchor. But arm
      C's best epoch was its last (epoch 11 of 0–11), so its row is the fixed-rule one. Comparisons among arm A,
      arm C and the legacy detector are free of epoch selection; arm A was not chosen on 1667.
    - "Scaling saturates (C ≈ B)" compares fixed-rule C with selected B. The only selection bias favours B, so
      neither saturation nor the absence of a gain is established: C shows no measured gain over B's selected
      row.
  - The same-scroll rows run the other way. Arm A is the Phase-2 best epoch, chosen on the Phase-2 Scroll-1
    region that its same-scroll row reports. So diversity's ~11% same-scroll cost is an upper bound.
  - What the runners now do:
    - each arm's caveat is built from its own run (`epoch_caveat`). It says whether the reported epoch was
      selected there or is the last, and that val_f1, precision and recall sit at each row's own best threshold
      on the region;
    - they report the best and the **last** epoch, a fixed rule (`epoch_rows`, one row when they coincide), and
      record every epoch's scores and the selection in the JSON;
    - the arm-C report cites arm A's same-scroll row, which its caveat mentions;
    - `epoch_checkpoints` orders checkpoints by epoch, and refuses Lightning's `-v<k>` names. Those mean a second
      run saved into the same `model_dir`, whose epochs cannot be told from the first's; they also broke the old
      sort key.
- **The teacher's file is recorded.** `fetch_teacher` takes the first `.tif` by name under a segment's
  `ink-detection/`, but provenance recorded only the teacher's dtype and range.
  - A fetch now writes `<teacher>.tif.source.json`, with the file and the candidates, and the reports name the
    file.
  - A teacher cached before this has no record, and the report says "source not recorded".
- **Documents corrected** (each marked as corrected; numbers unchanged):
  - FINDINGS: the Phase-2 "unaffected"; the cross-scroll framing; "diversity was the only variable"; the
    same-scroll cost; "scaling saturates", including the section heading.
  - The research paper: its Phase-2 caveat, and the cross-scroll "anchor", "controlled diversity result" and
    "saturates".
  - The README's Phase-2 and diversity headlines.
  - The research strategy's cross-scroll line.
  - The caveats of the three committed reports.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **The selection caveats understated or misplaced the bias.** Phase 2: "unaffected". Cross-scroll: "arm B vs legacy needs no selection asymmetry"; "diversity the only variable", which the generator would have restored; arm C's last-epoch row called selected; "scaling saturates" resting on B's selected row. | Caveats built per run, a last-epoch row and per-epoch scores from now on; FINDINGS, README, paper, strategy and reports corrected. Tests: the Phase-2, arm-B and arm-C generated reports. |
| P2 | **Labels and teachers were stretched onto the grid** when up to 20% off (`convert.py`), or up to 20% apart between axes (`distill_prep`). | 2 px crop/pad (convert); one pyramid scale (prep). Tests: padded, refused, per-axis teacher refused, pyramid rounding and thin shapes accepted, 3× refused. |
| P3 | **`fetch.py` nested the segment one directory down, and fetched the whole prefix.** | Layers, labels and mask only, into `out_dir`; a directory match refused. Tests: in-memory bucket with a zarr and a non-matching name, then convert; a `masks/` directory. |
| P3 | **Rows padded onto a label counted as negatives** when there was no mask file. | Outside the mask. Test. |
| P3 | **The teacher's file was not recorded.** | Recorded at fetch; in provenance and the report line. Test. |
| P4 | A Lightning `-v1` checkpoint name broke the measure step's sort; two runs in one `model_dir` were mixed. | `epoch_checkpoints` refuses them. Test. |

## Review of the PR, and what it changed

**First review**, of `e8b6c5d6`. It confirmed:
- the fetch semantics, against fsspec's own `_get` as s3fs uses it;
- that convert's fit is the loader's;
- "best of 12 epochs";
- the 65-slice → 19–44 window;
- that the new report keys break no reader.

| Finding | Outcome |
| --- | --- |
| P2: "arm B vs the legacy baseline needs no selection asymmetry" — copied from the hand-corrected report into the generator, a test, FINDINGS and this doc — is false: arm B is the selected row. | Corrected. |
| P3: same-scroll rows have the reverse asymmetry; README's "1.22 → 2.12" and the paper's "controlled diversity result" left. | Corrected. |
| P3: `distill_prep` stretched teachers 20% apart per axis; this doc called it sound. | Pyramid scale; tested. |
| P4: fetch copied the whole prefix; padded label rows were negatives without a mask; the tolerance constant was duplicated; fixture hygiene; "every column" included the label's positive_rate; a silent null source; the `-v1` sort; the s3fs note; the depth claim; "disjoint" means distinct IDs; formatting. | Corrected. |

**Second review**, of `db90d2b6`. It confirmed:
- every number against the committed JSONs;
- that arm A's Scroll-1 row is the Phase-2 selected row;
- the NaN handling;
- that `same_integer_scale` accepts all ten committed teacher shapes against shape / 4 (level 0 assumed outside
  Scroll 1), and their edge-clipped crops;
- the fetch copy and the mask zeroing.

| Finding | Outcome |
| --- | --- |
| P2: arm C's best epoch is its last (11 of 0–11), so "B and C are optimistic" is false for C, and "scaling saturates" rests on B's selected row. | Corrected in FINDINGS (heading too), README, paper, strategy and the arm-C report. The generators build each arm's caveat from its own run, with one row when best is last. |
| P3: `-v<k>` duplicates gave a stale "last" and an inflated "best of N". | Refused. |
| P4: "selection-free" was absolute (every row's val_f1 is at its own best threshold); the arm-C caveat named an arm-A row it lacked; k was taken from the height alone, and 3× accepted; a matched directory was silently skipped, and fetch matched names case-insensitively, convert case-sensitively; untested "source not recorded", best ≠ last, `cmd_measure_c`; a dead import; FINDINGS line length; the README's Phase-2 numbers and the strategy doc uncaveated; "overstated" → "at most"; a typo. | All corrected. |

**Third check**, of `9832c4d6`. It simulated all three generators with best ≠ last and best = last (arm C against
the committed prior and two generated ones) and confirmed:
- the texts and JSON in each case;
- every number and epoch count;
- "at most ~11%";
- that training chooses nothing by the validation region;
- the fetch listing types for s3fs and the memory filesystem;
- `same_integer_scale` on 20,000 random pyramid crops.

| Finding | Outcome |
| --- | --- |
| P2: the paper's "the one comparison there with no row selected" ignores arm C's fixed-rule row. | Corrected. |
| P3: "no further gain" (README, paper, strategy, FINDINGS heading and item 3) rests on B's selected row as "saturates" did. | "No measured gain over B's selected row; a gain over a fixed-rule B is not excluded"; FINDINGS' heading says scaling's effect is unresolved. |
| P3: the paper's own-scroll range 0.587–0.631 left out PHerc 0139 (0.258). | All three named. |
| P4: this doc's test-count exception was wrong (all 16 new cases fail on main) and its teacher-shape claims disagreed; "favours B"; the arm-B report's absolute "selection-free"; `measure_epochs`' docstring for best = last. | Corrected. |
| P4: a tie between the last epoch and an earlier best keeps the earlier as "selected" (conservative); the arm-C JSON does not mark the cited B row as selected. | Left. |

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

- **The selection bias has not been measured.**
  - The committed Phase-2 and arm-B rows are selected; arm C's is its last epoch.
  - A re-run of `measure` (GPU, the trained checkpoints) now prints every epoch's scores and a last-epoch row,
    which would size the bias.
  - Choosing the epoch on a separate region would remove it, but changes the experiment.
- **Depth windows.**
  - `convert.py` (tiff layers) names the middle 26 slices 17–42, whatever their source depth; for a 65-slice
    segment that is source 19–44. The detector's training fragments were read at source 17–42.
  - The zarr path takes the middle 26 of the level-2 volume, whose depth is not downsampled: 41–66 of 109
    slices, about 62 µm at 2.4 µm a slice. The legacy detector's training fragments' slice spacing was not
    checked here.
  - Nothing records the source indices. The students train and are measured on the same convention, so their
    numbers are consistent with each other.
- **Provenance still missing:**
  - which zarr `extract_region` read;
  - the source of teachers cached before this change (an ETag or size match against the bucket listing could
    recover it);
  - the selection, in the committed JSONs.
- **`convert.py` does not check the label's encoding.** A 0/1 label becomes all-negative after the detector's
  `/255`.
- **`evaluate.py`** writes `reports/detector/sota_scroll1_measurement.*` for whatever segment it is given, under a
  hard-coded baseline row for `20230702185753`. Nothing committed came from it.
- **The dated records repeat the old wording**: the lab notebook (2026-07-03), the July prize filings and the
  superpowers plans and specs. They are records of what was said then, and are left as they are.
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
- Branch, first head (`e8b6c5d6`): 42 failed, 2486 passed, 21 skipped, 1 xfailed, 2 errors. Same set; the 8 extra
  passes are its new test cases. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped (no training data).
- Branch, second head (`db90d2b6`): 42 failed, 2491 passed, 21 skipped, 1 xfailed, 2 errors. Same set.
  `scripts/smoke_test.py`: 9 of 11, 2 skipped.
- Branch, after the second review's fixes (`9832c4d6`): 42 failed, 2494 passed, 21 skipped, 1 xfailed, 2 errors.
  Same set. `scripts/smoke_test.py`: 9 of 11, 2 skipped.
- The third check's fixes change documents, two committed reports' wording and one docstring, no behaviour. After
  them: the two SOTA test files and the README- and FINDINGS-reading tests, 70 passed.
- `tests/test_sota_convert.py`: 14 passed; `tests/test_sota_distill_prep.py`: 16 passed.
  - Every new case fails on main (16 of the two files' 30).
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
  - `test_fetch_puts_the_segment_where_convert_reads_it`;
  - `test_fetch_refuses_a_mask_that_is_a_directory`.
- `tests/test_sota_distill_prep.py`:
  - `test_a_teacher_at_another_scale_per_axis_is_refused`;
  - `test_a_pyramid_levels_rounding_is_accepted`;
  - `test_the_selection_note_names_epoch_selection`;
  - `test_a_fetched_teacher_records_its_bucket_file`;
  - `test_the_distillation_report_states_how_the_student_was_selected`;
  - `test_checkpoints_are_in_epoch_order_and_one_run_only`;
  - `test_a_best_epoch_that_is_the_last_is_reported_as_the_fixed_rule_row`;
  - `test_the_cross_scroll_report_says_which_rows_were_selected_on_it`;
  - `test_the_arm_c_report_calls_a_last_best_epoch_a_fixed_rule`.

Not verified: anything against the real bucket (no network use, no s3fs), and the GPU runs.
