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
    the ridge filter's response to the CT, around 1e-3 at production's `ridge_sigma` of 1.0.
  - On the synthetic patch of the 2026-10-19 review, whose ridge maximum is 1.1e-3, the noise is 9 times the
    channel's maximum. The noisy channel correlates 0.02 with the clean one; the noisy CT correlates 0.996 with the
    clean CT.
  - The loop also samples `ridge_sigma` 2.0 and 3.0 (its `features` family). There the ridge channel is larger, and
    the independent review measured correlations of 0.33 and 0.87 after the noise. So the teacher was blind to the
    ridge channel at production's setting, and partly so at the others.
  - Production runs UA-MT (`use_uamt`, consistency weight 0.1). Its resenc_unet has no dropout-like layer, so
    `teacher_is_stochastic` finds it deterministic and it takes one pass: the student sees the view, and the teacher
    sees the view plus this noise. The consistency loss therefore fitted the student to a teacher that could not see
    the ridge channel. Since #145 the Albumentations recipe leaves that channel alone, so in Albumentations cycles
    this was the last place in training where it was buried. In batchgeneratorsv2 cycles villa's intensity
    transforms still bury it (below).
  - The noise is now on channel 0, the CT, only. A CT-only input gets it as before.
  - Why not scale it per channel instead: the independent review recomputed the ridge channel from the noisy CT. It
    correlates 1.000 with the clean ridge channel, and differs from it by at most 6 to 8% of its maximum. So leaving
    the ridge channel unperturbed is what a perturbation of the CT does to it.
- **Decohesion padded with zeros.**
  - `scroll_decohesion` blends into each slice the slice two before it and a five-slice z-blur. For the first two
    slices the shifted copy held zeros, and the blur counted its zero padding. A constant volume came out with its first two slices at 0.71
    and 0.77 of it, and its last two at 0.95 and 0.89 (alpha 0.45). That is an edge the augmentation never meant to
    add.
  - It is off in production, but it is one of the ablation's six conditions. That ablation now records val_f1 (#142),
    so a re-run measures decohesion rather than darkened end slices.
  - Now the shifted copy repeats the first slice at the start, and at both ends the blur averages only the slices
    there are. The interior is unchanged, bit for bit (the independent review compared it with main's).
  - The committed `reports/ablation_2026-05-20_19-38-31.csv` measured decohesion with the darkened ends.
  - A patch shallower than the blur (3 or 4 slices with the default five-slice blur) made `avg_pool3d` raise, on
    main as here. It is now returned unchanged. The loop's 16 slices never reach it.
- **`scripts/train_with_new_augs.py`** swapped `train.apply_scroll_specific_3d_augmentations` for the function
  `train.py` already imports from `scroll_augmentations`, so the swap did nothing. It is removed, and the docstring
  says what the wrapper is for now: the seed and the spawn start method. The ablation harness's docstring no longer
  says the wrapper monkey-patches.
- **Tests** (2 new, both in the standard suite):
  - `tests/test_uamt_compute.py`: the teacher's noise reaches the CT and not the ridge channel. It has std 0.01 and
    is drawn per pass, and a CT-only input still gets it.
  - `tests/test_scroll_specific_augmentations.py`: decohesion leaves a constant volume constant, matches the blend
    slice by slice, the ends included, and returns a patch shallower than its blur unchanged.

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
  - the noise at a tenth or ten times its scale, or drawn once per call;
  - the shifted copy zero-filled, or filled from the last slice, or shifted one slice too far;
  - the blur counting its padding;
  - the old early return for short patches.
- The existing UA-MT, augmentation and ablation-harness tests pass.
- Ruff clean; mypy clean on the changed files, the tests included.
- The standard suite on the first commit (`a93e8e72`): 2672 passed. The failures and errors are the same 42 and 2
  as on main, all environmental. The PR gives the final commit's.
- **Independent review** of the first commit found nothing blocking, and two should-fix findings:
  - the ablation harness's docstring still described the monkey-patch;
  - "the last place in training" held only for Albumentations cycles.

  Its nits, all addressed:
  - the ridge channel's size depends on `ridge_sigma`;
  - the CT noise's scale was not pinned from below;
  - short patches crashed decohesion;
  - the ghost's wording;
  - the 2026-10-19 doc's patch, whose sheets have variance 1, not 2 (corrected there).

  It also found `v3_training/trainer.py` adding noise to every channel of a CT-and-ridge input. That trainer has been
  unused since June (the 2026-10-17 review), so it is left as it is.
