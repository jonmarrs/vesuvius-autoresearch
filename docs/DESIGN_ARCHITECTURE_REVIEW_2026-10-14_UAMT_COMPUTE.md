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
- **The UA-MT teacher makes one pass when it is deterministic, four when it is not.**
  - `teacher_is_stochastic` runs four train-mode passes on the first unlabeled batch and compares them, so
    dropout, stochastic depth and functional dropout all count. Four, because a per-sample mask can repeat between
    two passes (1 in 16 for stochastic depth at batch 4; 1 in 4,096 over four).
  - `uamt_teacher` returns the mean probability and its variance; with one pass the variance is zero, where
    `torch.var` of one sample would be NaN. It restores the teacher's mode afterwards.
  - The pass count is printed and recorded in `run_result.json` (`uamt_teacher_passes`).

The training objective is unchanged. With UA-MT off, nothing used the removed pass except BatchNorm running
statistics (below). With UA-MT on, the removed passes differed only by the 0.01 input noise.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | **Cycles with UA-MT off spent about a fifth of every step on work they discarded.** Every step built a second augmented view and ran a full forward pass on it (`p2 = model(x_aug2, return_proj=True)`), but the only consumer, the projection consistency, is computed under `use_uamt`. Measured on a small `resenc_unet` (CPU, batch 4, 16×64×64), a step took 1.39 s with the pass and 1.10 s without, 21% less. The loop's budget is wall-clock, so such a cycle trained on about a fifth fewer batches than it could have. The UA-MT arm wasted a similar share on its teacher passes (next row), so the on/off comparison was not tilted; both arms were slower. The logs have 17 `use_uamt_False` cycles. | The view and the pass run only under UA-MT, in one gated block. |
| P2 | **The UA-MT teacher ran four passes that a model without dropout makes identical.** The passes are meant to differ by dropout, so their variance estimates uncertainty. The production `resenc_unet` has no dropout-like layers, so they differ only by the 0.01 input noise. On the production checkpoint (`best_model.pt`, random input), two train-mode passes are identical, the per-pixel variance is at most 2.1e-7, and `exp(-variance)` is 1.000000. One pass is within 6.8e-4 of the four-pass mean. Three of the four passes changed nothing but the step time. With UA-MT on, as in production, the measured step went from about 4.0 s to 3.2 s, 20% less: about a quarter more batches per cycle. | One pass when the teacher is deterministic, four otherwise. Tests: dropout and a timm-style stochastic depth make a teacher stochastic; p = 0, BatchNorm and `resenc_unet` do not. One pass gives a zero variance, not NaN. The teacher's mode is restored. Dropout makes the passes differ. Without dropout, one pass moves the target by no more than two single passes already differ by. |

## Review of the PR, and what it changed

| Finding | Outcome |
| --- | --- |
| The doc said the wasted view biased UA-MT on/off comparisons, but both arms wasted about a fifth of each step. | Corrected: both arms were slower; the comparison was not tilted. |
| `has_dropout` missed stochastic depth (DropPath) and functional dropout, so such a teacher would have fallen to one pass. | Replaced by `teacher_is_stochastic`, which compares train-mode passes on the first unlabeled batch. Nondeterministic kernels also count as stochastic, which keeps four passes. Its first version compared two passes; its test failed in one full run because a per-sample mask repeated (1 in 16 at batch 4), which would also have misread a stochastic-depth teacher in production. It now compares four. |
| `uamt_teacher` left the module in eval mode rather than restoring its mode. | Fixed and tested both ways. |
| The NaN check on the teacher variance could no longer fire and cost a GPU sync per step. | Removed. |
| The second view's gate was spread over a sentinel and three checks. | One block under `use_uamt and p1 is not None` builds the view, runs the pass and holds `p2`. |
| The pass count went only to stdout. | Recorded as `uamt_teacher_passes` in `run_result.json`. |
| The pass count was printed even when no unlabeled batch ever arrives. | Now decided and printed at the first unlabeled batch. |
| With UA-MT off, the removed pass still updated BatchNorm running statistics in BatchNorm models (`gated_unet`, the TimeSformer). | Recorded below. `resenc_unet` uses InstanceNorm without running statistics. |
| The equivalence test uses random weights. | The production checkpoint was measured too (above). |
| Cycles now train on more batches than the incumbent did, and nothing marks the change. | `uamt_teacher_passes` marks post-change cycles. The training-rate point is recorded below. |
| The DINO-lite consistency compares two differently augmented views; for spatial projections that compares misaligned pixels. | Recorded below: it predates this PR, and `resenc_unet`'s projection is globally pooled. |
| `augmentation_fallbacks` counts calls, of which there are now 1 per step without UA-MT and 3 with it. | Recorded below. |

## Observations for the owner (not changed)

- **More batches per cycle changes what a cycle measures.** Production cycles have UA-MT on, so each will now
  train on about a quarter more batches in the same budget. The incumbent was trained at the old rate. A
  candidate's gain may partly reflect the extra batches rather than its tweak, much as when the LR schedule moved
  to the time budget (2026-10-12).
- **Whether UA-MT should require dropout** remains the research decision the 2026-10-12 review left open. With
  dropout (for example `gated_unet` at `dropout > 0`), four passes and the uncertainty weighting run as before.
- **The DINO-lite projection** is still nearly degenerate: `Linear(1, 128)` on the pooled ink logit, then
  `LayerNorm`, as noted on 2026-10-12. For models whose projection is spatial (the TimeSformer's token grid,
  MedNeXt's map), the consistency compares two differently flipped and rotated views pixel by pixel, the
  misalignment the 2026-10-12 review fixed for UA-MT's student and teacher.
- **BatchNorm models without UA-MT** now update their running statistics once per step instead of twice (the
  removed pass ran in train mode). `resenc_unet` uses InstanceNorm without running statistics.
- **`augmentation_fallbacks`** counts augmentation calls: one per step without UA-MT (two before), three with it.

## Verification

Environment: CPython 3.10 venv with PyTorch 2.14.1 (no GPU visible), pytest, Ruff and mypy. The baseline is the
validation run of #61's head, whose tree is `51688255`'s.

- Baseline: 42 failed, 2089 passed, 15 skipped, 1 xfailed, 2 errors (environmental: no scroll data, no CUDA,
  no villa data files).
- Branch, after the PR review's fixes: 42 failed, 2093 passed, 15 skipped, 1 xfailed, 2 errors. The failures and errors are the same set as
  the baseline; the 4 extra passes are the new tests. `scripts/smoke_test.py`: 9 of 11 passed, 2 skipped.
- Ruff (check and format) on the changed files: clean.

New tests in `tests/test_uamt_compute.py`, now in `scripts/run_validation_tests.py`:
- a teacher is stochastic when its passes differ (dropout, stochastic depth), and not for p = 0, BatchNorm or
  `resenc_unet`;
- one teacher pass gives a zero variance, not NaN, and the teacher's mode is restored;
- dropout makes the passes differ;
- without dropout one pass matches four within the injected noise.

Not verified here: a training cycle on the GPU host, where the proportions may differ from the CPU measurement.
