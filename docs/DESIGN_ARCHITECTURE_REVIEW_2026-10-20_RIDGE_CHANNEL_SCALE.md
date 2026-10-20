# Design and architecture review — the ridge channel's scale, and the pitch run's status

Date: 2026-10-20. Baseline: `8f2a38f1` (main after #147).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the owner's #147 (finding 92's exploratory funnel);
- the ridge channel's scale at the model's input, which the last three rounds (#145, #146) left as the remaining
  reason the incumbent cannot use it;
- finding 92's run status against its registration.

## Observation for the owner: the model cannot see the ridge channel at its scale (not changed)

The 2026-10-13 review found the incumbent "barely uses the channel": ridges computed over a different depth block
moved its ink by at most 0.1%. #145 and #146 removed the training-time corruptions of that channel. This review asks whether the channel could matter even
clean. Measured on the 2026-10-19 synthetic patch (16 × 64 × 64, CT std 0.116) with the tracked `best_model.pt`
(resenc_unet, `ridge_sigma` 1.0, base_feat 64):

| `ridge_sigma` | ridge maximum | ridge std | stem variance from the ridge / from the CT |
|---|---:|---:|---:|
| 1.0 (production) | 1.1e-3 | 2.2e-4 | 4.5e-7 |
| 2.0 | 1.7e-2 | 3.4e-3 | 1.1e-4 |
| 3.0 | 8.4e-2 | 1.7e-2 | 2.8e-3 |

- **The incumbent's first convolution weighs the two channels alike.** Its stem kernels have an L2 norm of 3.69 on the
  CT and 3.66 on the ridge channel, as if training never pushed the ridge weights. The ridge channel enters at 1/500
  of the CT's spread, so it contributes 4.5e-7 of the stem's response at production's `ridge_sigma`.
- **The incumbent's ink output:**
  - Zeroing the ridge channel moves the ink probability by at most 2.4e-4, on a range of 0.06–0.17.
  - Rescaling the channel to the CT's spread moves it by up to 0.035 (correlation 0.93 with the original). So the
    weights respond to the channel when it has the CT's magnitude; at its own they never see it.
- **So `use_ridges` adds an input the network cannot see** at production's setting. The ridge filter
  (`fibers.detection.detect_ridges`) normalizes the CT it reads, but its output stays near 1e-3: the background term
  divides the Hessian norm by gamma 1.5.
- **The loop's `ridge_sigma` axis (1.0, 2.0, 3.0) changes this scale 80-fold.** What that axis measures is therefore
  the channel's visibility as much as the filter's scale.

**What a change would take, for the owner to decide.**
- Scale the ridge channel to the CT's spread, in the one place that builds it (`vesuvius_loader.ridge_channel`), so
  that training, validation and inference all see the same input. The scale could be fixed per `ridge_sigma`, or the
  patch's own.
- Record the scale in the config and the checkpoint, so that existing checkpoints keep reading the channel as they
  were trained.
- A warm start from the incumbent would then see a ridge input about 500 times larger through stem weights fitted to
  a near-zero one. It may want those weights scaled down, or a controlled pair of cycles to judge it.

None of this is done here: it changes the model's input, which is an experiment-design decision.

## What changed

- **Finding 92's status followed failed runs, not the row minimums.**
  - The registration: a run that fails is reported as failed, not scored; fewer than 9 in-sample, 6 Scroll-3 or 17
    total rows leave P1, P2 or P3 unevaluated, and the status INCOMPLETE.
  - `main()` set INCOMPLETE after any failed run. With 20 rows every prediction is evaluated, and the status
    still read INCOMPLETE. Finding 91's verdict sets it from the predictions.
  - `run_status` now gives IDENTITY_FAILED for a `run.json` that differs from the entrant, INCOMPLETE when a
    prediction is unevaluated, and OK otherwise. Failed runs are listed in `failed_runs` either way.
  - The committed run had no failure, so its status, OK, is unchanged.
- **Test** (`tests/test_neural_tracer_pitch_analysis.py`): one failed run is OK; five Scroll-3 rows are INCOMPLETE; an
  identity problem is IDENTITY_FAILED.

## Verified, no change needed

- **The owner's #147** (`scripts/neural_tracer_pitch_funnel.py`, the report's exploratory section).
  - It converts grid voxels to physical length by r = 9.6 / 7.91: a pitch-run grid voxel is r times longer.
  - The trace grid's 0.57 and 0.56 are 106³/128³ and 211³/256³.
  - Against the committed JSON: traces and seed dots fall on all 21 cubes. Scroll 3's median dot ratio is 0.42, the
    lowest of the three groups. The physical length kept correlates 0.959 with the coverage ratio. Grid voxels per
    trace are 66 against 66.
  - Its 7 tests pass.

## Verification

- `pytest tests/test_neural_tracer_pitch_analysis.py tests/test_neural_tracer_pitch_report.py
  tests/test_neural_tracer_pitch_funnel.py tests/test_filing_2026_10_numbers.py`: all pass, 4 skipped for want of the
  sibling checkouts.
- Ruff and mypy clean on the changed files, the test included.
- The measurements above: a script in the session's scratchpad, from `best_model.pt` at `8f2a38f1`, the loader's
  `ridge_channel`, and `build_resenc_unet` loading the checkpoint strictly.
- The standard suite: see the PR.
