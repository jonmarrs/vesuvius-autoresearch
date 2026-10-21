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
  - Every threshold's prediction scored about 2, and the sweep reported the largest as the scorecard's
    centerline_dice.
  - **Change:** `sweep_topology` refuses a label with no ink inside the mask, and `main` exits with the label's path
    and the reason, writing no scorecard. Ink lying only outside the mask is refused too.
- **`evaluate_villa_metrics.py` reported villa's whole-volume number with nothing to show the inflation.**
  - It scores whole volumes, as villa does.
  - **Change:**
    - its numbers are unchanged;
    - it now counts the slices that have a prediction and no ground truth, which villa counts as matching;
    - it records the count as `centerline_slices_predicted_without_ground_truth`, and warns when there are any;
    - only a 3-D volume is counted, since villa skeletonizes by slice along the first axis.
- **`METHOD.md`** says what each scorer now does about the empty-label route.
- **Tests**, one file each:
  - `tests/test_prize_gate_eval.py` (+2): a label with no ink, or with ink only outside the mask, is refused; `main`
    exits with the reason and writes nothing;
  - `tests/test_evaluate_villa_metrics.py` (+1): two predicted slices with no ground truth are counted and warned
    about. It uses the file's stub metrics, in a subprocess as the other tests there.

  Each of these mutants fails them:
  - the refusal dropped;
  - the mask ignored in it;
  - every empty ground-truth slice counted, whether predicted or not.

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

- `pytest tests/test_prize_gate_eval.py tests/test_evaluate_villa_metrics.py`: 9 passed.
- Ruff 0.9.10 is clean on the changed files.
  - `prize_gate_eval.py` was not ruff-formatted, so only the edited lines changed: its one difference from ruff
    format, a blank line after the docstring, is as it was.
  - The other changed files were formatted, and still are.
- `test_audit_doc_references` reports nothing new for `METHOD.md`.
- PLACEHOLDER: standard suite and smoke.
- PLACEHOLDER: independent review.
