# Design and architecture review — what a training step spends on UA-MT

Date: 2026-10-14. Baseline: `51688255` (main after #61). Villa pin unchanged.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the training step's semi-supervised work in `scripts/training/train.py`:
- the second augmented view and its forward pass, used for the DINO-lite projection consistency;
- the UA-MT teacher's stochastic passes;

and what they cost inside the loop's fixed time budget. The 2026-10-12 training-step review aligned the
student and teacher views, and found the uncertainty weighting to be a no-op without dropout. It left whether
UA-MT should require dropout as a research decision. This review is about the compute.

## What changed

- **The second view is built only under UA-MT.** The view (`x_aug2`) and its forward pass (`p2`) feed only the
  projection consistency, which is computed only when `use_uamt` is on.
- **The UA-MT teacher makes one pass when the model has no dropout, four when it does.**
  - `has_dropout` looks for a dropout layer or attention dropout with p > 0.
  - `uamt_teacher` returns the mean probability and its variance; with one pass the variance is zero, where
    `torch.var` of one sample would be NaN.
  - The step prints the pass count when UA-MT is on.

The training objective is unchanged. With UA-MT off nothing used the removed work. With UA-MT on, the removed
passes differed only by the 0.01 input noise (below).

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **Cycles with UA-MT off spent about a fifth of every step on work they discarded.** Every step built a second augmented view and ran a full forward pass on it (`p2 = model(x_aug2, return_proj=True)`), but the only consumer, the projection consistency, is computed under `use_uamt`. Measured on a small `resenc_unet` (CPU, batch 4, 16×64×64), a step took 1.39 s with the pass and 1.10 s without, 21% less. The loop's budget is wall-clock, so a `use_uamt: false` candidate trained on about a fifth fewer batches than its cost suggests, which biased every UA-MT on/off comparison toward UA-MT. The logs have 17 `use_uamt_False` cycles. | The view and the pass run only under UA-MT. |
| P2 | **The UA-MT teacher ran four passes that a model without dropout makes identical.** The passes are meant to differ by dropout, so their variance estimates uncertainty. The production `resenc_unet` has no dropout layers, so they differ only by the 0.01 input noise. On a `resenc_unet` (base 16, random input) the per-pixel variance averaged 4.1e-6 (at most 3.1e-5), and `exp(-variance)` was at least 0.99997. Three of the four passes changed nothing but the step time. With UA-MT on, as in production, the measured step went from about 4.0 s to 3.2 s, 20% less: about a quarter more batches per cycle. | One pass when `has_dropout` is false, four otherwise. Tests: dropout and attention dropout are detected, and p = 0 is not. One pass gives a zero variance, not NaN, and the teacher is returned to eval mode. Dropout makes the passes differ. Without dropout, one pass moves the teacher's target by no more than two single passes already differ by. |

## Observations for the owner (not changed)

- **More batches per cycle changes what a cycle measures.** Production cycles have UA-MT on, so each will now
  train on about a quarter more batches in the same budget. The incumbent was trained at the old rate. A
  candidate's gain may partly reflect the extra batches rather than its tweak, much as when the LR schedule moved
  to the time budget (2026-10-12).
- **Whether UA-MT should require dropout** remains the research decision the 2026-10-12 review left open. With
  dropout (for example `gated_unet` at `dropout > 0`), four passes and the uncertainty weighting run as before.
- **The DINO-lite projection** is still nearly degenerate: `Linear(1, 128)` on the pooled ink logit, then
  `LayerNorm`, as noted on 2026-10-12.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #61's head, whose tree is `51688255`'s.

- Baseline: 42 failed, 2089 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch: 42 failed, 2093 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the 4 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files: clean.

New tests in `tests/test_uamt_compute.py`, now in `scripts/run_validation_tests.py`:
- dropout is detected where it acts;
- one teacher pass gives a zero variance, not NaN;
- dropout makes the passes differ;
- without dropout one pass matches four within the injected noise.

Not verified here: a training cycle on the GPU host, where the proportions may differ from the CPU measurement.
