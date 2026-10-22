# Design and architecture review — the detector's held-out row was selected where it is reported

Date: 2026-10-22. Baseline: `c200a41d` (main after #184).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the detector's evaluation path, and the documents that report it.
- The code: `detector/infer.py`, `measure.py`, `eval.py`, `cli.py`'s `reproduce` and `measure`, and the checkpoint
  `detector/train.py` returns. No earlier review covered `measure.py`. `DESIGN_ARCHITECTURE_REVIEW_2026-10-04_DETECTOR.md`
  covered `infer.py`'s window and uncovered-pixel rules.
- The documents: the working detector's results in `FINDINGS.md`, `reports/detector/REPRODUCTION.md`,
  `REPRODUCE.md` §5 and `docs/RESEARCH_PAPER.md`.

Main has not moved since #184. There are no open pull requests. This round covers the 07:13 UTC firing.

## What changed

- **The same-scroll row was selected on the fragment it is reported on, and no document said so.**
  - FINDINGS' headline table gives the detector's same-scroll row on Fr143: `val_f1` 0.393, AP 0.357, lift 2.07,
    ROC-AUC 0.709. The research paper gives the same table.
  - Its checkpoint, epoch 7 of 12, is the best of the 12 by ROC-AUC on Fr143 itself (REPRODUCTION.md's sweep).
    REPRODUCTION.md, REPRODUCE.md and FINDINGS' Phase 5 state the selection. None says it makes the row optimistic,
    and neither the headline table nor the paper mentions it.
  - `DESIGN_ARCHITECTURE_REVIEW_2026-10-16_SOTA_DISTILLATION.md` added such caveats to the distillation reports, and
    gave each a fixed-rule row. The working detector's row predates them, and kept none.
  - The sweep measures the selection's effect only on ROC-AUC under the Gaussian blend: epoch 7 scored 0.7001, the
    last epoch, a fixed rule, 0.6982. No fixed-rule run measured the other metrics.
  - **Change:** FINDINGS (the table and Phase 5), REPRODUCTION.md and the paper now say so, with the fixed-rule
    figure. Each addition is dated. The cross-scroll column involves no epoch selection on Scroll 1; in both, `val_f1`
    is at its own best threshold, as FINDINGS says.
  - Phase 5's "plateaus at ~0.69–0.71 across epochs 6–11" is now ~0.69–0.70 (Gaussian blend). The sweep it cites runs
    from 0.6915 to 0.7001. 0.709 is epoch 7 under the uniform blend.
- **The one-command `reproduce` does not run the selection REPRODUCTION.md reports.**
  - It scores the checkpoint `train()` returns. `ModelCheckpoint` monitors `train/total_loss`, and with Lightning
    2.6.6 it ranks epochs by their mean training loss.
    - Measured: a three-epoch CPU run on synthetic fragments. The callback's scores were exactly the CSV log's epoch
      means, 0.4446, 0.5859 and 0.6012, and it kept epoch 0.
  - So `reproduce` neither repeats the epoch-7 selection nor need give 0.7090. Its ≥ 0.70 gate is checked on the
    lowest-training-loss epoch. REPRODUCTION.md printed the command under the 0.7090 result, with no note.
  - **Change:**
    - `reproduce` prints the path of the checkpoint it scored.
    - Its docstring says what it scores.
    - REPRODUCTION.md and REPRODUCE.md §5 say it too.
  - The gate and the selection rule are unchanged.
- **A failed fragment's error could break `measure`'s table.**
  - `measure` records a fragment that fails as an `ERROR:` row in `cross_scroll_measurement.md`, with the exception's
    text.
  - A checkpoint that fails to load raises PyTorch's multi-line `load_state_dict` error. Its lines after the first
    did not stay in the row, and a `|` in it split the cell.
  - **Change:** the row's text has its whitespace runs collapsed and its pipes escaped. The JSON keeps the error as
    raised.
- **Tests** (`tests/test_detector_contracts.py`, +2, in the standard suite):
  - A multi-line error with a pipe stays one row, and the JSON keeps it whole.
  - `reproduce` scores the checkpoint training returns, on the configured held-out fragment, and prints its path.
- **Mutants.** Each of these fails a new test:
  - the error cell left raw;
  - its pipes not escaped;
  - its newlines kept;
  - the JSON given the cleaned text;
  - the checkpoint not printed.

## Verified, no change needed

- **`infer.py`.**
  - It divides patches by 255 after `read_volume_mask` clips them at 200, as training's `A.Normalize` does.
  - Its mirror TTA flips back the dimensions it flipped.
  - It refuses a model output that is not finite (batch, 1, h, w) logits, and a fragment with no usable window.
- **`measure.py`** crops the probability and mask to the label's shape. A degenerate target is recorded as a failure,
  and the CLI exits 1 (`test_measure_records_degenerate_target_failure_and_cli_exits_nonzero`). So its strict JSON
  holds only finite rows.
- **`core/frangi_torch.py`.**
  - Its reflect indices are scipy's `reflect`, for any radius.
  - Its closed-form eigenvalues hold when all three are equal.
  - `tests/test_frangi_torch.py` checks it against skimage.
- **`core/inference.py`.**
  - Every region is tiled to its edge.
  - The Hann weights are positive.
  - The blend refuses uncovered pixels in a complete prediction.
- **`core/villa_inference.py`.**
  - The Gaussian window stays positive at the patch's corners, at about e^−16.
  - Villa's TTA is loaded from the pinned file.
- **#184's marker** is read by the action matrix for `ready` only, which the new checkpoint check sets.
- **The standard suite's tests and the clock.**
  - One test reads the date: `test_daily_never_overwrites_existing_same_day_pdf`. A run across midnight would make it
    pass vacuously, not fail.
  - Nine test functions have no assertion. Each checks that its subject runs: five run a script's entry point, two
    run a subprocess with `check=True`, and two call a check that raises on failure.

## Observations for the owner (not changed)

- **The filings carry the uncaveated row.**
  - They are records of what was filed:
    - `docs/PRIZE_FILING_DRAFT_2026-06.md`;
    - `docs/PRIZE_FILING_DRAFT_2026-07.md`;
    - `docs/PRIZE_FILING_2026-07_SUBMIT.md`;
    - `SUBMISSION.md`.
  - `docs/LAB_NOTEBOOK.md` states the selection, as a dated entry.
  - None was changed.
- **What `reproduce` should select is the owner's call.** It could keep the lowest-training-loss epoch, take a fixed
  rule such as the last, or report both. So is whether the ≥ 0.70 gate belongs on that epoch. The last epoch's
  uniform-blend AUC has not been measured; that needs the data and a GPU.
- **The blend was compared on Fr143 too.** Uniform scored 0.709 against Gaussian's 0.700 on epoch 7. The reason
  REPRODUCTION.md gives for it is fidelity to the proven recipe's accumulation.
- **`measure`'s JSON records neither the checkpoint nor the configuration.** Its Markdown names the checkpoint.
- **`measure` and `eval` write fixed names under `reports/detector/`, which are tracked.** A run replaces the
  committed record. `git status` shows it. The 2026-06-30 resenc plan copies the files aside first.

## Verification

VERIFICATION
