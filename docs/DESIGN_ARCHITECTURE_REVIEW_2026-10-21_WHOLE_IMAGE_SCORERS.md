# Design and architecture review — the whole-image scorers and the empty-label route

Date: 2026-10-21. Baseline: `26b5d570` (main after #174).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the two scorers that pass villa's `centerline_dice` a whole label rather than the loop's ink-containing
patches.
- **`repro/gp_winner/prize_gate_eval.py`** scores a prediction PNG through a threshold sweep. `FINDINGS.md` cites it
  for the GP-winner models' topology.
- **`scripts/evaluate_villa_metrics.py`** reports villa's metrics on two volumes.

#174 recorded that villa's `centerline_dice` gives a slice with no ground-truth skeleton the whole slice as its
tolerance region: any prediction there scores about 2. `METHOD.md` said these scorers were still exposed to that.

Main has not moved since #174. The owner's open PR #170 changes only the octant-crop files, none of which this round
touches. This round covers the 13:16, 14:14 and 15:16 UTC firings.

## What changed

- **`prize_gate_eval.py` scored a label with no ink as about 2, and called it topology-optimal.**
  - `_label_bbox` falls back to the full frame when the label has no ink inside the mask. The label passed to villa
    is then all zero.
  - Every threshold whose prediction inside the mask was not empty scored about 2, and the sweep reported the
    largest as the scorecard's centerline_dice.
  - **Change:**
    - `sweep_topology` raises `InkFreeLabel`, a `ValueError`, when the label it would give villa has no ink. That is
      the label inside the mask, cropped to its bounding box and converted to uint8. Ink lying only outside the mask
      is refused too.
    - `main` catches only that exception. It exits with the label's path and the reason, writing no scorecard.
      Any other error, from villa's metrics or elsewhere, keeps its own message and traceback.
- **`evaluate_villa_metrics.py` reported villa's whole-volume number with nothing to show the inflation.**
  - It scores whole volumes, as villa does.
  - **Change:**
    - its numbers are unchanged;
    - it now counts the slices that have a prediction and no ground truth, which villa counts as matching;
    - it records the count as `centerline_slices_predicted_without_ground_truth`, and warns when there are any;
    - only a 3-D volume is counted, since villa skeletonizes by slice along the first axis.
- **`METHOD.md`** says what each scorer now does about the empty-label route.
- **Tests**, one file each:
  - `tests/test_prize_gate_eval.py` (+3):
    - a label with no ink, with ink only outside the mask, or with ink lost in the conversion to uint8 is refused;
    - `main` exits with the label's path and the reason, and writes nothing;
    - `main` lets an error inside the metric through.
  - `tests/test_evaluate_villa_metrics.py` (+1): two predicted slices with no ground truth are counted and warned
    about. The predictions lie in the ground truth's column, so only slices along the first axis count them, and a
    third slice below the threshold is not counted. It uses the file's stub metrics, in a subprocess as the other
    tests there.

  Each of these mutants fails them:
  - in `prize_gate_eval.py`:
    - the refusal dropped;
    - the mask ignored in it;
    - the check made before the conversion to uint8;
    - the label's path dropped from the exit;
    - `main` catching every `ValueError`, or writing a scorecard before it exits;
  - in `evaluate_villa_metrics.py`:
    - every empty ground-truth slice counted, whether predicted or not;
    - the count made along the second axis, or the last;
    - the count made on the arrays before the threshold.

## Verified, no change needed

- **The crop to the common size** of prediction, label and mask in `prize_gate_eval.py` is deliberate: the winner's
  inference pads its output. Its test covers it.
- **pixel-AUC of 0.5 for a one-class label** follows `scripts/pixel_auc.py`'s convention, which is by design and
  tested. With an ink-free label refused, an all-ink one is the only case left.
- **The GP-winner figures in `FINDINGS.md`** (centerline_dice 0.121 and 0.101) are on labels with ink, so the refusal
  does not touch them.

## Observations for the owner (not changed)

- **Neither test file is in the standard suite.** Neither scorer is one of the loop's entry points, so
  `test_validation_suite_covers_the_loop` does not require them. They run under `pytest tests/`.
- **`evaluate_villa_metrics.py` crops a shape mismatch to the common size**, with a warning. A prediction of another
  volume, or another resolution, is then scored on the overlap. Whether to refuse is the owner's call.

## Verification

- `pytest tests/test_prize_gate_eval.py tests/test_evaluate_villa_metrics.py`: 10 passed.
- Ruff 0.9.10 is clean on the changed files.
  - `prize_gate_eval.py` was not ruff-formatted, so only the edited lines changed: its one difference from ruff
    format, a blank line after the docstring, is as it was.
  - The other changed files were formatted, and still are.
- `test_audit_doc_references` reports nothing new for `METHOD.md`.
- **The standard suite** on the first commit (`b2922ae8`) ran as on main: 2704 passed, with the same 42 failures and
  2 errors, all environmental. The count is unchanged because neither test file is in it. The smoke test gave 9 of 11
  passed and 2 skipped, as on main.
- **Independent review** of the first commit, in a worktree without villa. It found nothing blocking.
  - It confirmed:
    - the refusal is on the arrays the loader has already cropped, before the bounding box;
    - nothing else calls `sweep_topology`, and nothing reads the results JSON but the tests;
    - the count uses the binarized arrays villa is given, along villa's slicing axis;
    - the scorecards behind `FINDINGS.md`'s 0.121 and 0.101 have a pixel-AUC near 0.9, so their labels have ink
      inside the mask;
    - the padding is bottom and right (`repro/gp_winner/infer_resenc.py`), so the top-left crop is right;
    - the pixel-AUC convention.
  - Its should-fix finding: the new count test did not pin the slicing axis, since counting along the last axis also
    gave 2.
  - Its nits:
    - the test did not pin the threshold either;
    - `main` caught every `ValueError`;
    - the label's path in the exit was untested;
    - the refusal checked the label before its conversion to uint8, which can lose ink for a caller passing wider
      integers;
    - "every threshold's prediction scored about 2" overstated, since an empty prediction scores 0;
    - the test's docstring said the count measures how much of the score is inflated, where it says only whether;
    - `METHOD.md` did not say the count is made for 3-D volumes only;
    - the new key is wider than the results printout's 30-character column.

  All are addressed above except the last, which only misaligns the printout; it is left as is.
