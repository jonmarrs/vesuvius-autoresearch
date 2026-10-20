# Design and architecture review — the ridge channel's scale, and the pitch run's status

Date: 2026-10-20. Baseline: `8f2a38f1` (main after #147).
Reviewer: Claude (Anthropic), at the owner's request.

Scope:
- the owner's #147 (finding 92's exploratory funnel);
- the ridge channel's scale at the model's input, after #145 and #146 removed the Albumentations recipe's and UA-MT's
  corruptions of it;
- finding 92's run status against its registration.

## Observation for the owner: at production's setting the model cannot see the ridge channel (not changed)

The 2026-10-13 review found the previous incumbent "barely uses the channel": ridges computed over a different depth
block moved its ink by at most 0.1%. This review asks why, with the tracked `best_model.pt` (resenc_unet,
`ridge_sigma` 1.0, base_feat 64, trained before #145). The figures are from one synthetic patch: the 2026-10-19
review's 16 × 64 × 64, with CT std 0.117, and ridges from `vesuvius_loader.ridge_channel`. Production computes them
over 24 slices and crops.

**`ridge_sigma` is a gain, not a scale.**
- `fibers.detection.hessian` smooths with a fixed `gauss_sigma` of 2 and multiplies the Hessian by `sigma**2`. The
  ridge measure's planar and blob terms are ratios, which that factor leaves alone.
- So the channel at `ridge_sigma` σ is σ⁴ times the channel at 1.0. On the patch the gains are 15.9 and 78.8 (σ⁴ = 16
  and 81), with a correlation of 1.0000.
- The loop's `ridge_sigma` axis (1.0, 2.0, 3.0) therefore turns the channel's gain, and nothing else.

**What the stem sees.** The stem's convolution is followed by InstanceNorm, which removes each filter's mean. So the
quantity that matters is each filter's variance from the ridge channel over its variance from the CT, both centred.

| `ridge_sigma` | ridge maximum | ridge std | median share over the 64 filters | largest share |
|---|---:|---:|---:|---:|
| 1.0 (production) | 1.1e-3 | 2.2e-4 | 1.7e-6 | 3.5e-5 |
| 2.0 | 1.7e-2 | 3.4e-3 | 4.4e-4 | 8.8e-3 |
| 3.0 | 8.4e-2 | 1.7e-2 | 1.1e-2 | 0.22 |

- At 1.0 the ridge channel is invisible to the stem: its median share, in amplitude, is about 1e-3. At 3.0 one filter
  takes a fifth of its variance from it.
- The stem's kernels have nearly equal norms on the two channels (3.69 and 3.66). Both moved alike from their
  initialisation, so the norms say nothing about use. The zeroing test below does.

**The incumbent's ink output** (range 0.06–0.17 on the patch):
- zeroing the ridge channel moves it by at most 2.4e-4 (3.2e-4 with another noise seed, independent review);
- rescaling the channel to the CT's std moves it by up to 0.035 (correlation 0.93). The weights respond to ridge-shaped
  input of the CT's size.

The heads take the input beside the backbone's output, so they see the ridge channel directly. Zeroing it moves the
fiber head's probability by up to about 4e-3 (independent review). None of the heads feeds ink.

**Why the channel is so small.** The ridge measure's background term is 1 − exp(−S²/2γ²), about S²/(2γ²) for small S,
where S is the Hessian norm. The Hessian is taken of a smoothed, min-max-normalised patch, so S is small (at most 0.08
on this patch). It then enters squared, giving 1.4e-3. Gamma, 1.5, accounts for only a factor of 2.25.

**How general this is.** There is no real CT in the repository. On a sharper, papyrus-like patch (2-slice sheets every
8 slices, contrast 0.4, noise 0.05), the independent review found the CT's std 115, 7.4 and 1.7 times the ridge's at
1.0, 2.0 and 3.0. It also found that zeroing the ridge channel moved ink by at most 5.3e-3 on every probe. The
conclusion holds at production's 1.0; at 3.0 the channel is near the CT's scale.

**What a change would take, for the owner to decide.**
- Scale the ridge channel to a CT-like spread in the one place that builds it (`vesuvius_loader.ridge_channel`), so
  that training, validation and inference all see the same input.
- Record the scale in the config and the checkpoint, so existing checkpoints keep their input.
- The `ridge_sigma` axis would then do nothing, since it is only a gain. It would be retired, or made a real scale
  (`gauss_sigma`).
- A warm start from the incumbent would see the ridge input magnified through stem weights that never used it. A
  controlled pair of cycles would judge the change.
- The fiber head's target is the Frangi vesselness of the CT. A visible, Hessian-based input could become a shortcut
  for that head.

None of this is done here: it changes the model's input, which is an experiment-design decision.

## What changed

- **Finding 92's status followed failed runs, not the row minimums.**
  - The registration: a failed run is reported as failed, not scored. Fewer than 9 in-sample, 6 Scroll-3 or 17 total
    rows leave P1, P2 or P3 unevaluated, and the status INCOMPLETE.
  - `main()` set INCOMPLETE after any failed run. With 20 rows every prediction is evaluated, and it still read
    INCOMPLETE. Finding 91's verdict takes the status from its predictions.
  - The logic after the scoring loop is now `outcome(identity, rows, native, comp)`, which `main()` calls. It returns
    IDENTITY_FAILED (and no verdict) for a `run.json` that differs from the entrant. Otherwise it returns INCOMPLETE
    when a prediction is unevaluated, and OK when none is. Failed runs are still listed in `failed_runs`.
  - The 2026-10-20 pitch-verdict review left this as an observation for the owner. It is the registration's own table,
    the same kind of divergence #148 corrected, so it is corrected here.
  - The committed run had no failure, so its status, OK, is unchanged. The analysis code now differs further from the
    copy frozen with that run, which `reports/neural_tracer_pitch.md` says was fixed in the registration. The chain
    script would refuse to resume that work directory, which is harmless since the run is complete.
- **Test** (`tests/test_neural_tracer_pitch_analysis.py`), through `outcome`:
  - one failed run (a row of None) is OK;
  - five Scroll-3 rows are INCOMPLETE;
  - an identity problem gives IDENTITY_FAILED with no verdict.

  It kills the parent's rule (INCOMPLETE after any failure), a verdict computed despite an identity problem, and a
  status taken from no predictions.

## Verified, no change needed

- **The owner's #147** (`scripts/neural_tracer_pitch_funnel.py`, the report's exploratory section).
  - It converts grid voxels to physical length by r = 9.6 / 7.91: a pitch-run grid voxel is r times longer.
  - The trace grid's 0.57 and 0.56 are 106³/128³ and 211³/256³.
  - Against the committed JSON:
    - traces and seed dots fall on all 21 cubes;
    - Scroll 3's median dot ratio is 0.42, the lowest of the three groups;
    - the physical length kept correlates 0.959 with the coverage ratio;
    - grid voxels per trace are 66 against 66.
  - Its 7 tests pass.

## Observations for the owner (not changed, pre-existing)

- `neural_tracer_pitch_analysis.main()` exits 0 for every status; finding 91's exits 1 unless OK.
- `reports/neural_tracer_pitch.json` holds a `sources` entry that `main()` does not write, and the report test reads
  it. A re-run of `main()` would therefore fail that test until the entry was added again.

## Verification

- **The measurements.**
  - The stem shares are per filter: the variance over voxels of `conv3d(ridge only)` over that of `conv3d(CT only)`,
    with the stem's own weights. They are taken before InstanceNorm, which does not change a ratio of centred
    variances.
  - The ink effects are from `build_resenc_unet(2, 64, True)` loading `best_model.pt` strictly, on the patch.
  - The independent review reproduced every figure, and corrected the first commit's shares, which had included each
    channel's offset.
- `pytest tests/test_neural_tracer_pitch_analysis.py tests/test_neural_tracer_pitch_report.py
  tests/test_neural_tracer_pitch_funnel.py tests/test_filing_2026_10_numbers.py`: all pass, 4 skipped for want of the
  sibling checkouts.
- Ruff and mypy clean on the changed files, the test included.
- The standard suite does not import the pitch analysis. On the first commit (`5c48c58f`) it ran as on main: 2672
  passed, with the same 42 failures and 2 errors, all environmental.
- **Independent review** of the first commit found nothing blocking. Its should-fix findings:
  - the test did not reach `main()`'s wiring;
  - the stem-weight inference was wrong;
  - the variance shares included the channels' offsets;
  - `ridge_sigma` is a gain, not a filter scale;
  - the account of the channel's smallness was misleading;
  - the figures came from one patch.

  All are corrected above, with its nits.
