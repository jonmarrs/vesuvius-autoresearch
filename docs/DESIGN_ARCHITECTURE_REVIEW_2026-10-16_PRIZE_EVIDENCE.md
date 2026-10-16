# Design and architecture review — the prize-evidence chain

Date: 2026-10-16. Baseline: `37fb8937` (main after #88). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the scripts that turn a ranked candidate into submission evidence, and the validator that judges it.
- The chain: `run_villa_prize_evidence_chain.py`, with `run_ranked_inference.build_predict_command`.
- The validator: `validate_prize_artifact.py`.
- Reports: `summarize_villa_evidence_preflight.py`, `build_villa_prize_action_matrix.py`,
  `build_villa_review_manifest.py`, and the handoff that runs them all (`run_post_sprint_villa_handoff.py`).
- `generate_submission_package.py`, `promote_to_review.py`, `make_alignment_evidence.py`, and
  `prize_readiness.tsv`.

None of these has had a design review before. The earlier inference reviews covered the writer of the metadata they
read (`predict.py`).

## What changed

- **The validator requires what `predict.py` records, and what a reader can check.**
  - **A complete prediction.** `prediction_complete` must be `true`. It was checked only when present, so a record
    without it passed.
  - **A `sigmoid(ink)` ink map.** `inference_recipe.ink_probability` must equal `INK_PROBABILITY`, the constant the
    ranker already uses. QC-gated maps from before 2026-10-13 (whose uint8 exports were blank) and maps without a
    recorded recipe passed, though the ranker refused them.
  - **A scale bar that fits.** A declared 1 cm bar must fit the region: `width_px × voxel_size_um ≥ 10 mm`. The
    declaration was taken on trust, and the shared test fixture declared one on a 64 px region (0.51 mm).
- **The chain leaves no evidence from an earlier run.** Before anything that can fail, it removes its earlier
  `evidence_metadata.json`, `manifest.json`, `neural_tracing.json` and `validation_report.json`, and resets its
  report to FAIL. It used to reset the report only after selecting the candidate and building its command, either
  of which can raise.
  - Before, a rerun that failed after `predict.py` had overwritten the region's arrays left the old
    `evidence_metadata.json` in place. The review manifest's `validate_command` re-validates that file, and could pass
    it against the new arrays.
- **`--neural-tracing` runs the launcher.**
  - The chain looked for `scripts/launch_neural_tracing.py`. That file moved to `scripts/inference/` on 2026-06-02, so
    the option silently did nothing.
  - A launcher that exits non-zero now yields no plan, even if it wrote a marker.
- **The predict command passes the candidate's voxel size** (`--voxel_size_um` from `voxel_um`).
  - `predict.py` prefers a voxel size the checkpoint records. `train.py`'s checkpoints record none, so every export
    was scaled at the 7.91 µm default whatever the scan.
  - The chain then compared that with the candidate's `voxel_um`. A queue built with `--voxel-um` other than 7.91
    always failed.
- **Smaller fixes:**
  - `make_alignment_evidence.py` scanned for its densest crop over the image height on both axes, so it never searched
    the right of a wide image. It now refuses a crop larger than the image.
  - `promote_to_review.py` read `visualization_path`, which no predictor writes, so it never copied a preview. Its
    `.replace("_meta", "")` turned every chain `evidence_metadata.json` into one directory, `evidencedata`. It now
    reads `output_image_path` and names a chain candidate after its directory.
  - Stale names:
    - the action matrix's launcher paths;
    - the loop's proofreader hint, which named Fr47 and `predictions/pred_10_…`; the benchmark reads Fr143 and writes
      to `reports/`;
    - `launch_vc3d.py`'s "load both ink and fiber";
    - `docs/VILLA_PRIZE_READINESS.md`'s root-level `predict.py` and its "always writes fiber";
    - `docs/SUBMISSION_EVIDENCE.md`'s "uses the checkpoint's voxel size".

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P3 | **The validator passed evidence the pipeline knows is not evidence.** It checked completeness only when recorded, never the ink recipe, and took a declared 1 cm bar on trust. Run on the committed `reports/scroll23_evidence/candidate_000` prediction, it now names all three: no completeness, no recipe (a pre-2026-10-13 QC-gated map), and a 1 cm bar declared on a 0.51 mm region. That record's tracked `PRIZE_READINESS_REPORT.json` still says PASS (2026-05-29). | The three gates. Tests: absent, false and string completeness; four non-`sigmoid(ink)` recipes; a 64 px region. Six of the eight cases fail on main; the other two, already caught there, guard them. The shared fixture and the three PASS tests in `test_prize_readiness.py` now describe a 1600 × 64 px region (12.7 mm, wide enough for `predict.py` to declare the bar) with a recorded recipe and completeness. |
| P3 | **A failed rerun left the previous evidence to be re-validated**, and a rerun refused before predicting (a candidate the table no longer has, a row the command builder refuses) left the previous PASS report too. | The chain removes them first. Tests: after a failed `--execute` rerun none of the four files remains; after a rerun refused for a bad `voxel_um` or an empty table the report is FAIL and no evidence remains. Fail on main. |
| P4 | **`--neural-tracing` was a silent no-op**, and would have trusted a marker from a failed launch. | The launcher's path, and its exit code. Tests: with exit 0 the marker is the plan; with exit 1 there is none. Both fail on main. |
| P4 | **Every export was scaled at 7.91 µm**, whatever the candidate's voxel size. | `--voxel_size_um` from the candidate; a non-numeric, zero, negative or NaN `voxel_um` is refused. Test fails on main. |
| P4 | `make_alignment_evidence.py` never searched the right of a wide image; `promote_to_review.py` lost its previews and merged chain candidates. | Fixed. Tests fail on main. |

## Review of the PR, and what it changed

The independent review of the PR's first head (`68469b03`) found nothing blocking. It confirmed:
- every writer that can produce passing evidence (`predict.py`, `ensemble_predict.py`, and the chain's copy of
  their metadata) records `prediction_complete` and the `sigmoid(ink)` recipe;
- the only other `validate()` callers are the submission package, which always fails, and the lasagna pipeline,
  which reads chain output;
- `width_px` is the region's width in source pixels in every writer, the dimension the bar is drawn along;
- nothing reads the files the chain now removes, except after a chain run;
- the launcher accepts the chain's flags, exits 1 only without `trace_service.py`, and records "not ready" with exit 0;
- each new test fails with its fix reverted.

| Finding | Outcome |
| --- | --- |
| The reset still came after `select_candidate` and `build_predict_command`, either of which can raise. A rerun with a row the builder now refuses (`voxel_um = "bad"`), or with fewer ranked rows than the index (the handoff runs 0–11), kept the earlier PASS and its evidence. | The removals and the FAIL report come first. Tested both ways; fails on the first head. |
| `promote_to_review.py` still merged the lasagna worklist's candidates, whose chain directories are all `<rank>_<stem>/evidence`. | A chain candidate is named by its directory and parent. Tested on both layouts; fails on the first head. |
| A stale `validation_report.json` (written by the review manifest's validate command) survived a failed rerun; removing `neural_tracing.json` first was untested. | Removed with the others; both tested. |
| The shared fixture declared its bar at 1280 px, which `predict.py` would not (it needs 1581 px). | 1600 px. |
| `docs/VILLA_PRIZE_READINESS.md`'s checklist; the doc's `prize_gate_report` (it is `evaluate_prize_gates`); "first FAIL ends the handoff" holds in preflight too; the submission package's new wrong-reason failure; the validator's new package import; `review_villa_pin.py`'s legacy record. | Corrected or recorded below. |
| `build_lasagna_fiber_worklist.py` builds every eligible row's command, so one non-numeric `voxel_um` now stops the step; a boolean `True` voxel would be read as 1.0. | Stays as is. It is the builder's existing strictness: every tracked row is "7.91", a TSV cannot hold a boolean, and the chain's voxel check refuses 1.0 against the export. |


- **As wired, no queued candidate can pass, and the reports say they are ready.**
  - `build_scroll23_search_queue.py` sets each region to one patch, 64 × 64 px. At 7.91 µm that is 0.51 mm wide, so it
    cannot carry the 1 cm bar the validator requires. `predict.py` declares one from 1581 px wide.
  - No caller supplies overlap masks, and `predict.py` does not write their paths:
    - `run_post_sprint_villa_handoff.py` and the review manifest's commands pass no `--train-mask`/`--predict-mask`;
    - the masks must come from the model's training history, which only the owner can attest.
  - Preflight checks neither the bar nor the masks. So `summarize_villa_evidence_preflight.py` marks candidates
    `ready_for_gpu`, and the action matrix marks them `ready_now`.
  - Prize evidence needs a region at least 1 cm wide predicted with the 64 px window, plus masks. Choosing those
    regions and supplying the masks are the owner's decisions.
- **The handoff stops at the first candidate that fails.**
  - `run_steps` runs each command with `check=True`. The chain exits 1 on FAIL, in preflight as after a GPU run,
    and raises when the ranked table has fewer rows than `--evidence-limit` (12).
  - So in either mode the first FAIL ends the handoff, and the summary, matrix and manifest are not rebuilt.
  - In that mode the chain is not given `--preflight-report`, so the summary would read the older preflight reports.
  - The summary never reads `PRIZE_READINESS_REPORT.json`, so a GPU run's result does not reach the matrix or the
    manifest.
- **Preflight is more lenient than the command builder.** Its `_as_int`/`_as_float` default or truncate a bad value
  (`z = "1.5"` becomes 1, `patch_size = "bad"` becomes 64), where `build_predict_command` refuses it. A row can pass
  preflight and then fail the chain.
- **The overlap gate does not relate the masks to the region.** It checks their shape against each other, not
  against `width_px`/`height_px`. Masks passed on the command line bypass the metadata's `overlap_evidence_mode`, so
  the dry-run package's illustrative 1000 × 1000 masks, which `docs/VILLA_PRIZE_READINESS.md` suggests for a trial
  run, satisfy it.
- **The committed `reports/scroll23_evidence/candidate_000` record says PASS.**
  - The validator fails it, as above. Its masks, `evidence_metadata.json`, and its zarrs' `.zgroup` are not in the
    checkout.
  - Re-validating it, or removing the report, is a change to a project record, so it is left to the owner.
- **`generate_submission_package.py` always fails, by design**, and has three loose ends:
  - its default `--prediction-image predictions/pred_10_20_30.png` cannot match `predict.py`'s names;
  - it draws its bar at `10000 / voxel` image pixels on whatever figure it is given, so on `predict.py`'s three-panel
    figure the bar is not 1 cm;
  - it records its 64 px ML window as `window_width_px`, which the validator reads as the region's width, so it now
    also fails on the scale bar, though its 2000 px placeholder image does carry a 1250 px bar (at its default 8.0 µm).
- **`review_villa_pin.py`'s checks validate `predictions/pred_10_1000_1000_64x64_meta.json`**, a tracked legacy
  record that always fails (unknown scroll, no masks; a test keeps it failing). The command checks that the validator
  runs, not that any evidence passes.
- **The validator now needs the project package** (for `INK_PROBABILITY`), as the ranker already did. Every caller
  runs it under `uv` or the project's `.venv`; run with a bare system `python3` it would fail to import.
- **`promote_to_review.py` and `make_alignment_evidence.py` have no callers.** Also, `promote_to_review.py` promotes
  without checking a readiness report, and prints a `launch_crackle_viewer.py --project` flag that the viewer does not
  read.
- **Paths resolve against two bases.** The summary and the opportunity plan's `--out` are relative to the working
  directory; the matrix, the manifest and the plan's `--audit` to the checkout. Run from elsewhere, the matrix and
  manifest read the checkout's copies.
- **`prize_readiness.tsv`.**
  - The README calls it a per-cycle check, but `train.py` writes a row only on promotion.
  - Its `window_mm` uses 8.0 µm (`train.py`, `evaluate_prize_gates`) where the evidence path uses 7.91. The window
    decision is the same: both accept up to 64 px.
  - Its `submittable` column reflects the training gates, not evidence.
- **`zarr>=2.18.3` has no upper bound** in `pyproject.toml`. `save_vc3d_zarr` relies on zarr v2's file layout
  (`.zgroup`, `.zarray`), which the validator checks. `uv.lock` pins 2.18.3.
- **Stale strings left in dated records:** `docs/PROGRESS_PRIZE_SUBMISSION_2026-05.md` and the launchers' generated
  runner docstrings name the old launcher paths.

## Reviewed and sound

- **Every subprocess command matches its target's options.** Checked for:
  - the handoff's steps;
  - the manifest's chain and validator commands;
  - the chain's `predict.py` and neural-tracing commands.
- **The VC3D check matches `save_vc3d_zarr`.** It checks:
  - a v2 group and the meta dimensions;
  - voxel size;
  - a `|u1` (1, H, W) array;
  - z/y/x micrometre axes and scale;
  - the x/y/z → z/y/x translation.
- **The chain keeps provenance.** It:
  - never invents masks;
  - keeps the prediction's metadata byte-identical;
  - resets the report to FAIL first;
  - refuses artifacts a run did not refresh;
  - checks source, position, size, patch, image and voxel against the candidate.
- **The window rule is one rule everywhere** (64 px or 0.5 mm): `train.py`, the validator, preflight and the queue.
- **`production_predict.py` cannot become evidence.** It writes no image and uses a `prod_pred_` prefix.
- **A model without a fiber head** writes no fiber export, and the validator then skips the fiber check (#88).

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy.

- Baseline: the validation run of `1837cc1c` (#88), whose tree is `37fb8937`'s but for its review doc's result
  lines. It was 42 failed, 2224 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are environmental:
  no scroll data, no CUDA, no villa data files.
- Branch, PR first head (`68469b03`): 42 failed, 2238 passed, 15 skipped, 1 xfailed, 2 errors. The failures and
  errors are the same set as the baseline; the 14 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11
  passed, 2 skipped (no training data).
- After the PR review's fixes (`e4032512`): 42 failed, 2240 passed, 15 skipped, 1 xfailed, 2 errors. Same set; the
  2 extra passes are the refused-rerun cases. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped. The related modules
  with the handoff, manifest and worklist tests: 318 passed.
- `test_submission_contracts`, `test_prize_readiness`, `test_candidate_preprocessing_contracts`,
  `test_volume_inference_contracts`, `test_villa_prize_action_matrix`, `test_summarize_villa_evidence_preflight` and
  `test_execute_lasagna_pipeline_resume`: 307 passed.
- The modules of the scripts that import the validator's helpers, with the handoff and the manifest: 14 failed,
  222 passed, the same 14 failures as on main (tifxyz and villa modules absent here).
- The validator runs as a script from outside the checkout.
- Ruff (check and format) and mypy on the changed scripts: clean.

New tests in `tests/test_submission_contracts.py` (each fails on main, except the two guard cases):
- `test_evidence_must_record_a_complete_prediction` (absent, false, "true");
- `test_evidence_must_be_a_sigmoid_ink_map` (none, empty, QC-gated, a bare string);
- `test_a_declared_scale_bar_must_fit_the_region`;
- `test_failed_execution_leaves_no_evidence_to_revalidate`;
- `test_a_rerun_refused_before_predicting_leaves_no_previous_pass` (a bad voxel, an empty table; from the PR review);
- `test_neural_tracing_runs_the_launcher_and_trusts_only_a_successful_marker` (exit 0, exit 1);
- `test_ranked_command_passes_the_candidates_voxel_size`;
- `test_alignment_evidence_scans_the_whole_width`;
- `test_review_promotion_names_and_previews_chain_evidence`.

Not verified here: the handoff or the chain on the GPU host.
