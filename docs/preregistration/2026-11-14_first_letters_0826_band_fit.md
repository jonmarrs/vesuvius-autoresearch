# Pre-registration: does the recipe's spiral fit put windings on sheets of PHerc. 0826, a second unread scroll?

**Written 2026-11-14, before any fit of PHerc. 0826 has run here.** Finding 114.

PHerc. 0826 is on the prize-eligible list. Everything this step makes from it (distance field, fit, windings,
scores per winding) stays on this machine under `spiral_out/first_letters/pherc0826_band`. The report will carry
summary numbers about the fit and no mesh, render or ink map.

## The question

Finding 112 asked this of PHerc. 0211 and the answer was `ON_SHEETS`: a median excess of 0.086 against 0.000 for
an unconverged fit. That is one scroll, and I had predicted worse. This repeats the measurement, unchanged, on
the next scroll the strategy names, so that the campaign's second scroll has a fit before its ink read is
planned. It does not wait for finding 113's reading of PHerc. 0211, which is with the reader.

## Reachability, checked before this was written

- **Inputs are public.** The spiral tracks are on disk (12 GB, tracked range z 4500 to 16920, fetched
  2026-11-14). The catalog lists the 9.362 µm CT, the m7 surface prediction, lasagna volumes and a scroll axis
  for PHerc. 0826. `setup/fetch_volumes.sh` has not run for this scroll; it is step 1.
- **The winding direction is published.** The catalog's two orientation flags for volume `20250821151701`
  (`metadata.json`, read again 2026-11-14) give anticlockwise by villa's rule, the same as PHerc. 0211.
- **The score and its floor are finding 112's**, with the same code (`band_fit_quality.py`,
  `band_fit_verdict.py`).
- **Another contributor has attempted PHerc. 0826 end to end** (winners page). I have not compared.
- **Not checked:** whether villa's default of 130 windings at 16 voxels suits this scroll.

## The band

z 10250 to 11750, the slices `env.sh` has carried as its default since before PHerc. 0826's tracks were
fetched, and the same slices as PHerc. 0211's band. They lie inside the tracked range.

## Procedure

Scripts in `repro/first_letters/eligible_band/`, with `FL_SCROLL=PHerc0826`. Each step once, in its own unit, one
at a time, the training loop stopped.

1. `setup/fetch_volumes.sh`, `setup/make_dataset.sh`, `run_sdt.sh` (CPU).
2. `run_fit.sh smoke 300`, then `run_quality.sh smoke`: the floor.
3. `run_fit.sh full`: 30,000 steps, the PHerc. 343 recipe's overrides, villa `0fb38c45` with the recipe's
   one-line patch, seed 1.
4. `run_quality.sh full`, then `band_fit_verdict.py`.
5. `run_spacing.sh full`: the description below.

## Predictions, fixed now

The lines are finding 112's.

- **P1, the windings follow sheets.** A median excess of at least 0.07 and at least 80% of windings with
  positive excess.
- **P2, some do.** A median excess of at least 0.03 and at least 65% of windings with positive excess.
- **What I expect: P1 holds** (`ON_SHEETS`), with low confidence. PHerc. 0211 cleared the line by 0.016, and I
  have one scroll to go on.

## Decision rule

| outcome | verdict |
|---|---|
| a step exits non-zero, or fewer than 60 windings are scored | `DOES_NOT_RUN` |
| the smoke fit's median excess is above 0.03 | `INSTRUMENT_FAILS` |
| P1 holds | `ON_SHEETS` |
| P1 fails and P2 holds | `PARTLY_ON_SHEETS` |
| P2 fails | `NOT_ON_SHEETS` |

What each does to the campaign:

- `ON_SHEETS` or `PARTLY_ON_SHEETS`: PHerc. 0826's band is ready for an ink read, which is registered
  separately once finding 113 has shown whether its protocol works. `PARTLY` restricts it to windings with
  excess of at least 0.07.
- `NOT_ON_SHEETS`: no ink read of this fit. The report says what differs from PHerc. 0211 and PHerc. 343, and
  the next step is one named change to the fit, registered separately.
- `DOES_NOT_RUN`: the failure is diagnosed to its cause before anything is changed.

## A description that is not part of the verdict

`band_fit_spacing.py` measures, on the full fit, the spacing between consecutive raw windings and the spacing
between predicted sheets (where the share of nodes inside a sheet rises again as the nodes are moved along the
normal). On PHerc. 343 the two were about equal (12 to 13 voxels). On PHerc. 0211, measured by hand after finding
112, the windings were 9.5 voxels apart and the sheets about 14: more windings than sheets, so some windings
must share a sheet or sit between two. I expect the ratio on PHerc. 0826 to be under 0.85 as well, with low
confidence. Whatever it is, it is reported; it changes no verdict here. It decides how the ink read chooses
windings.

## What the result cannot do

- **It does not show the windings are the right sheets.** The distance field comes from the surface prediction
  the fit was given, and the fit's loss has a term on it. A winding can sit on predicted sheets and switch
  sheets along its length.
- It says nothing about ink.
- A pass is about this band, this seed and these defaults.

## Limits

One scroll, one band, one fit, one seed, villa's default winding count. The thresholds are half and about a
fifth of one reference value from PHerc. 343.

## Cost

On PHerc. 0211 the distance field took 13 minutes, the 300-step fit 4 minutes and the full fit 3 h 19 min at
7.7 GB of host memory and 10.3 GB of GPU memory. I expect about the same. No training of any model. No upload.
