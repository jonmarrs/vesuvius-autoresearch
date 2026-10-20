# Design and architecture review — the UA-MT teacher's noise, and decohesion's edges

Date: 2026-10-20. Baseline: `b37a1bf5` (main after #144).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: two observations the 2026-10-19 ridge-channel review (#145) left unchanged, and a leftover of the ablation
harness. The round also read:
- the owner's #143 and #144 (the neural tracer at its training pitch);
- `scripts/process_supervisor.py`;
- `villa_modules.py` and `model_wrappers.py`, among the least-reviewed modules the loop imports.

They need no change (below).

## What changed

- **UA-MT's teacher noise buried the ridge channel.**
  - `uamt_teacher` added noise of std 0.01 to every channel of the teacher's input. With `use_ridges`, channel 1 is
    the ridge filter's response to the CT, around 1e-3. On the synthetic patch of the 2026-10-19 review (a ridge
    maximum of 1.1e-3), the noise is 9 times the channel's maximum. The noisy channel correlates 0.02 with the
    clean one; the noisy CT correlates 0.996 with the clean CT.
  - Production runs UA-MT (`use_uamt`, consistency weight 0.1). Its resenc_unet has no dropout-like layer, so
    `teacher_is_stochastic` finds it deterministic and it takes one pass: the student sees the view, and the teacher
    sees the view plus this noise. The consistency loss therefore fitted the student to a teacher that could not see
    the ridge channel. Since #145 the augmentations leave that channel alone, so this was the last place in
    training where it was buried.
  - The noise is now on channel 0, the CT, only. A CT-only input gets it as before.
- **Decohesion padded with zeros.**
  - `scroll_decohesion` blends into each slice the slice two before it and a five-slice z-blur. For the first two
    slices the shifted copy held zeros, and the blur counted its zero padding. A constant volume came out with its first two slices at 0.71
    and 0.77 of it, and its last two at 0.95 and 0.89 (alpha 0.45). That is an edge the augmentation never meant to
    add.
  - It is off in production, but it is one of the ablation's six conditions. That ablation now records val_f1 (#142),
    so a re-run measures decohesion rather than darkened end slices.
  - Now, at the patch's ends, the shifted copy repeats the first slice and the blur averages only the slices there
    are. The interior is unchanged.
- **`scripts/train_with_new_augs.py`** swapped `train.apply_scroll_specific_3d_augmentations` for the function
  `train.py` already imports from `scroll_augmentations`, so the swap did nothing. It is removed, and the docstring
  says what the wrapper is for now: the seed.
- **Tests** (2 new, both in the standard suite):
  - `tests/test_uamt_compute.py`: the teacher's noise reaches the CT and not the ridge channel, and a CT-only input
    still gets it;
  - `tests/test_scroll_specific_augmentations.py`: decohesion leaves a constant volume constant, and matches the
    blend slice by slice, the ends included.

  Both fail with main's code.

## Effect on the loop

From the next cycle, UA-MT's teacher sees the ridge channel the student sees. The CT's noise is unchanged in
distribution, so the teacher's single pass perturbs the CT as before. Validation does not involve UA-MT, so the
incumbent stays comparable. Nothing here is measured on a trained model.

## Verified, no change needed

- **The owner's #143 and #144** (finding 92 and the October draft's citations).
  - `resample_cube_pitch.resample` maps output voxel j to source position j·r (`affine_transform` with `diag(r)`),
    and replicates the edges. `resampled_length` covers the source axis and rounds up to an even length.
  - It samples trilinearly at the coarser pitch without averaging over the coarser voxel. At r = 1.21 that is a
    mild difference from a scan acquired at 9.6 µm, and it is part of the preregistered design.
- **`process_supervisor`**:
  - the stop path terminates, then kills after the grace period;
  - a second stop kills at once and waits for the group;
  - an interrupted wait kills before it propagates.

  Each of these is documented, and tested in `tests/test_loop_lifecycle.py`.
- **`villa_modules.load_villa_leaf`**:
  - refuses a file that imports a sibling or `vesuvius`;
  - registers the module before executing it, and holds a per-module lock throughout;
  - drops a failed initialization so the next caller retries.
- **`model_wrappers`** declares which outputs are heads (`task_heads`), so train.py trains no placeholder.

## Observations for the owner (not changed)

- The `aug_mode` confound from #145 stands. batchgeneratorsv2 cycles run villa's intensity transforms on the ridge
  channel.

## Verification

- `pytest tests/test_uamt_compute.py tests/test_scroll_specific_augmentations.py`: all pass. With main's code, the
  two new tests fail.
- **Mutation check.** Each of these is killed:
  - the noise on every channel, or none;
  - the shifted copy zero-filled, or filled from the last slice, or shifted one slice too far;
  - the blur counting its padding.
- The existing UA-MT, augmentation and ablation-harness tests pass.
- Ruff clean; mypy clean on the changed files, the tests included.
- The standard suite: see the PR.
