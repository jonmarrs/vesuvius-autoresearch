# Design and architecture review — the ground-truth registration gates

Date: 2026-10-16. Baseline: `9d9896e9` (main after #97). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the tooling that registers the 2023 hand labels onto the SOTA flattening and scores models against them
(`repro/sota_data/register.py`, `register_run.py`, `gt_register.py`, `gt_finetune.py`, `retirement.py`), its
probes (`scripts/probe_registration_offset.py`, `scripts/probe_placement_field.py`), and the claims the README,
FINDINGS, the research paper and the committed reports make from it. This is the code behind the 2026-08-07
retraction. The review audited it read-only, then verified each finding before fixing it.

## What changed

- **Scoring needs the validation that passed, on what it scores.**
  - `cmd_score` checked only that a `VALIDATED` file existed. `warp` and `warp_obj` rewrote the label and its
    stats without removing it, so a new, never-validated label was scored.
  - A validation that crashed (an unreadable layer, say) also left the last one's marker.
  - Now:
    - warp, warp_obj and validate remove the marker first;
    - a passing validation writes a JSON marker with the sha256 of the registered label, its stats and the
      teacher;
    - `cmd_score` refuses unless the stats record a passing gate and the three files still hash as they did.
  - A marker in the old text format is refused.
- **The gate thresholds cannot be loosened from the command line.**
  - `--min-enrichment` and `--min-periodicity` defaulted to 0, which turned those criteria off, and
    `--max-placement-offset` could be raised: 1000 passed a 150 px displacement.
  - Each target now records the thresholds its committed validation used (residual 12, enrichment 2.0 or
    periodicity 0.6) beside the 48 px placement threshold. These are the defaults; a value may tighten them and a
    looser one is refused.
  - The report states the gate's thresholds and the placement offset.
- **The placement gate fails closed.**
  - `placement_peak` returned (0, 0), a pass, when no shift could be scored: its initial value, with a Dice of −1.
  - A flat landscape tie-breaks to the search corner, and a label displaced beyond the search peaks on its edge.
  - In strict mode, the gates' default, it now raises in these cases. A raise makes `validate` leave no marker,
    and `gt_prep_fragment` drop the region. The two probes pass `strict=False` and report the clamp.
- **Retirement is enforced where scores are made.**
  - Segment `20230702185753` was retired non-scoring on 2026-08-14. Its per-tile placement error reaches ~1.9×
    the 512 µm analysis window. But only the fine-tune prep checked retirement, and that segment is
    `register_run`'s default target.
  - warp, warp_obj, validate and score now refuse a retired segment unless run with `--allow-retired`, and such a
    report says it is indicative only.
- **Fine-tuning re-checks what it trains on.**
  - `cmd_finetune` trained on whatever the prep record's `kept` listed. The 2026-07 record, still committed inside
    `gt_finetune_heldout.json`, keeps all four regions with no placement check.
  - Its displaced labels are still on disk: fragment writes refuse to overwrite.
  - `verified_kept` now admits a region only if its own entry passed and has a verified placement within the
    gate, on a segment that is neither retired nor the held-out one. On the July record it admits none.
- **Disclosures corrected:**
  - The orientation: `warp_obj` selects the vt convention by teacher-enrichment among four. The held-out gate note
    said it was "carried from the slice-5 export-pipeline convention", and the report called the enrichment
    margin "independent corroboration".
  - The held-out report's committed overlay (2026-07-07) predates the 2026-08-07 fix.
  - The orig report now carries the retirement.
  - FINDINGS:
    - the retired segment's rows, the "single clean fact" included, are now indicative only;
    - a stale "the held-out test below shows it does not generalize" is marked.
  - The research paper: the retirement, and the F1 comparison.
  - The README's headline gave the teacher ROC-AUC "0.56–0.70", but 0.56 is the retracted held-out figure; it is
    0.70–0.75.
    - The README's and the paper's "at or just under the teacher" holds on ROC-AUC, which the reports say
      understates the binary teacher. On their fair metric, F1 at 0.5, the teacher leads: 0.572 vs 0.44–0.46.
- **Small fixes.**
  - `probe_registration_offset.py` recorded `--coarse` but never passed it.
  - `gt_finetune`'s accounting of its four regions is corrected: two fail placement, one drops at prep and one
    is retired.
  - A retirement test created `local_data/` directories in the checkout; it now runs in a temporary directory.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P1 | **The README cited the retracted held-out teacher figure** (ROC-AUC 0.56). | 0.70–0.75. |
| P2 | **Scoring ran without the checks:** a stale marker after warp or a crashed validate; thresholds that defaulted off or could be raised. | Hashed markers, cleared first; target thresholds as floors. Tests: stale label refused, crash leaves none, old marker refused, three loosened thresholds refused, floors applied. |
| P2 | **`placement_peak` passed what it could not locate** (no scored window; a boundary peak). | Strict mode raises; probes opt out. Test. |
| P2 | **The retired segment could be validated and scored**, and was the default. | Refused without `--allow-retired`. Test. |
| P2 | **`cmd_finetune` trusted its prep record.** | `verified_kept`. Test: the July record admits none; offset, held-out and retirement refusals. |
| P2 | **Disclosures** described a teacher-selected orientation as carried or independent; a pre-fix overlay was cited as evidence; the retired segment's rows were called clean. | Corrected in code, reports, FINDINGS and the paper. |
| P4 | `--coarse` ignored; region accounting; a test writing into the checkout. | Fixed. |

All 10 new test cases fail on main.

## Verified, not fixed here

- **`warp_via_field` misaligns every registration by several pixels.**
  - It upsamples the mesh-grid field with `cv2.resize`, which aligns pixel centres. The mesh's samples are grid
    points, and the crop bounds are rounded to whole mesh cells.
  - The new mesh's grid is 776 × 559 cells, about 16.3 level-2 px a cell (`registration_offset_2026-08-07.md`).
    On a synthetic identity registration in the held-out crop's geometry (y0 = 4000, 4096 px), every output
    pixel samples 3 to 14 px off, 8.4 on average. At 4 px a cell the error is 1.5 px, at 1 px a cell none.
  - So part of the measured placement "floor" (32 px held-out, 46.6 px orig) is this artifact, not the cross-scan
    method. Its exact share needs the meshes.
  - The fix changes the shared warp (vertex-aligned, fractional crop), and the committed placements would then
    need re-measuring on the data. It is the next round's.

## Observations for the owner (not changed)

- **Possible label leakage through the teacher.**
  - villa's 2023 recipe trains on all three hand-labelled segments
    (`repro/villa_preserved/ink_detection/train_timesformer_og.py`).
  - If the released canon predictions came from a model trained on these labels, the teacher row scores a model
    on its own training labels. Every student distilled from it then inherits that signal, the held-out
    students' included.
  - Not established either way here: nothing in the repository says which model made the release.
- **The scoring mask is all-valid.** Pixels where the field was invalid, or the label was out of range, are
  zeroed and scored as negatives. Far nearest-vertex matches are not masked, and the 2023 `_mask.png` is
  ignored. Size of the effect unmeasured.
- **The placement gate can still pass a spurious peak inside its window.** On synthetic text labels displaced
  by about 450 px, 3 of 40 found a peak within 48 px, according to the audit. A requirement that the peak's Dice
  clearly beat chance would close it. That is a new gate criterion, so the owner's call.
- **The per-tile placement figures are clamped.**
  - `probe_placement_field` searches ±102 px, and the orig segment's worst tile sits on that clamp: its true
    error is at least 139 px (≈1.34 mm, 2.6× the window), not the "~102 px / ~0.96 mm / 1.9×" of
    `retirement.py` and the report.
  - One tile is degenerate (Dice 0 at zero and at the peak) and is counted in the mean.
  - The retirement stands; its numbers are lower bounds.
- **Arm A's epoch was chosen on the held-out GT region** (by agreement with the teacher). Its row is the only one
  above the teacher on ROC-AUC (0.772 vs 0.753), and "mildly" optimistic is unmeasured. Arms B and C were not
  selected there.
  - Every row's val_f1, precision and recall sit at that row's best threshold on the GT region.
- **Provenance.**
  - The reports record no checkpoint, teacher, mesh or label hashes, no commit and no `placement_peak`
    parameters.
  - `registration_offset_2026-08-07.json` was overwritten by the post-fix run, so it no longer backs that
    report's first table.
  - `registered_gt_heldout_stats.json` (2026-07-07, "the teacher reads this segment poorly") carries no
    superseded marker.
- **Duplication.**
  - `_region_in_mesh` exists in `register_run` (reading a module global) and in `gt_register` (taking `seg`),
    both hardcoding level 2 as `/4`.
  - There are three OBJ parsers; two assume v and vt pair by position.
  - The mesh caches and downloads are separate and non-atomic.
  - The second-copy `LEVEL0_SHAPE` regression tests are grep-based: an annotated or literal-call variant passes
    them.
- **The offset report is internally inconsistent in places**: "blame not yet assigned" beside its resolution,
  and four values for the corrected teacher ROC.
- **The dated records** (the lab notebook, the prize filings, the superpowers specs) keep their wording.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), fsspec 2026.9.0 (no s3fs), pytest, Ruff and
mypy.

- Baseline: main `9d9896e9`, the tree of `9832c4d6` but for documents and a docstring: 42 failed, 2494 passed, 21
  skipped, 1 xfailed, 2 errors. The failures and errors are environmental: no scroll data, no CUDA, no villa data
  files, and no s3fs or tensorstore.
- Branch: _running at this commit; recorded in the next._
- `tests/test_sota_registration_gates.py`: 10 passed; all fail on main.
- The registration tests that need s3fs to collect, run with a stand-in: 58 passed (`test_sota_register`,
  `test_sota_register_targets`, `test_sota_gt_register`, `test_gt_finetune_prep_superseded`,
  `test_retirement_shared`, and the new file).
- The README- and FINDINGS-reading tests: 40 passed. Ruff check on the changed files: clean.

New tests (`tests/test_sota_registration_gates.py`, added to the standard suite):
- `test_placement_without_any_scored_window_is_not_zero`;
- `test_a_passing_validation_vouches_for_exactly_what_it_saw`;
- `test_a_failed_or_crashed_validation_leaves_no_marker`;
- `test_an_old_text_marker_is_not_trusted`;
- `test_thresholds_cannot_be_loosened_from_the_command_line` (three thresholds);
- `test_the_targets_thresholds_apply_by_default`;
- `test_a_retired_segment_is_not_validated_or_scored`;
- `test_fine_tuning_rechecks_every_kept_region`.

Not verified: anything against the meshes, labels or bucket (none here), and the GPU scoring runs.
