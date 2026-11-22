# Pre-registration: does the recipe's spiral fit put windings on sheets of PHerc. 0211, a crushed scroll nobody has read?

**Written 2026-11-13, before any fit of PHerc. 0211 has run here.** Finding 112.

PHerc. 0211 is on the prize-eligible list. Everything this step makes from it (distance field, fit, windings,
scores per winding) stays on this machine under `spiral_out/first_letters/pherc0211_band`. The report will carry
summary numbers about the fit and no mesh, render or ink map.

## The question

Findings 110 and 111 were controls on scrolls with known answers. This is the campaign's first step on an unread
scroll. PHerc. 343, where the recipe was built, is close to round; PHerc. 0211 is crushed flat in most of its
length. Before any ink model is run, the question is narrower: do the windings the fit writes follow sheets at
all? If they do not, an ink read of them means nothing, and the hours it costs are not spent.

## Reachability, checked before this was written

- **Inputs are public.** For PHerc. 0211 the bucket holds the 9.362 µm CT (19416 × 7948 × 7948), the m7 surface
  prediction, lasagna normal and gradient volumes and a scroll axis; packed spiral tracks cover z 4500 to 17500.
  `repro/first_letters/eligible_band/setup/` fetches the band's share.
- **The winding direction is published for this scroll and not for PHerc. 0125.** The fit must be told whether
  the spiral turns clockwise or anticlockwise going outward. villa derives it from two orientation flags in the
  open-data catalog (`metadata.json`, read 2026-11-13). PHerc. 343's flags give CW, which is what its recipe
  uses. PHerc. 0211's and 0826's give ACW. PHerc. 0125's z direction is null there, so its direction is unknown.
  That is why this step is on PHerc. 0211 and not on PHerc. 0125, which the strategy named first.
- **A short fit cannot tell the direction.** On PHerc. 343, 1,000-step fits declared CW and ACW had track
  losses of 440.6 and 438.8 at step 800, the last one printed. So the direction cannot be found by trial at that length.
- **The score exists and separates a converged fit from an unconverged one.** `band_fit_quality.py` reads the
  distance field of the surface prediction at each raw winding's nodes and at the same nodes moved 6 voxels
  along the winding's normal. `excess` is the share of nodes inside the predicted sheet minus that share for
  the moved nodes. On PHerc. 343:

  | fit | median excess over 120 windings | 10th to 90th percentile | windings with positive excess |
  |---|---|---|---|
  | 30,000 steps (finding 110, windings confirmed against the published ones) | 0.140 | 0.025 to 0.240 | 96.7% |
  | 1,000 steps, CW | −0.001 | −0.032 to 0.036 | 49.2% |
  | 1,000 steps, ACW | 0.000 | −0.031 to 0.022 | 47.5% |

- **Not checked:** whether villa's default of 130 windings at 16 voxels a winding suits PHerc. 0211. The recipe
  used the defaults on PHerc. 343 and this step uses them unchanged.

## The band

z 10250 to 11750: the middle 1,500 slices of the tracked range, fixed in `env.sh` before the tracks were read.
Track length per 1,500 slices was checked on PHerc. 0125 only, where it is flat along the axis to about ±10%.

## Procedure

Scripts in `repro/first_letters/eligible_band/`, with `FL_SCROLL=PHerc0211`. Each step once, in its own unit, one
at a time, the training loop stopped.

1. `setup/fetch_tracks.sh`, `setup/fetch_volumes.sh`, `setup/make_dataset.sh`, `run_sdt.sh` (CPU).
2. `run_fit.sh smoke 300`, on an otherwise idle host: it builds the packed pools, shows memory and time, and
   its windings are the floor.
3. `run_quality.sh smoke`.
4. `run_fit.sh full`: 30,000 steps, the PHerc. 343 recipe's overrides, villa `0fb38c45` with the recipe's
   one-line patch, seed 1.
5. `run_quality.sh full`.

## The floor

The smoke fit's windings, scored the same way. An unconverged fit scored 0.00 on PHerc. 343. If the smoke fit's
median excess on PHerc. 0211 is above 0.03, the score is reading something other than convergence there and
the verdict is `INSTRUMENT_FAILS` whatever the full fit scores.

## Predictions, fixed now

- **P1, the windings follow sheets.** Over the full fit's scored windings, a median excess of at least 0.07
  (half of PHerc. 343's) and at least 80% of windings with positive excess.
- **P2, some do.** A median excess of at least 0.03 and at least 65% of windings with positive excess.
- **What I expect: P2 holds and P1 fails** (`PARTLY_ON_SHEETS`), with low confidence. The scroll is crushed, the
  sheets in the slice I looked at run nearly parallel for thousands of voxels, and the winding count is a guess.
  I would not be surprised by `NOT_ON_SHEETS`.

## Decision rule

| outcome | verdict |
|---|---|
| a step exits non-zero, or fewer than 60 windings are scored | `DOES_NOT_RUN` |
| the smoke fit's median excess is above 0.03 | `INSTRUMENT_FAILS` |
| P1 holds | `ON_SHEETS` |
| P1 fails and P2 holds | `PARTLY_ON_SHEETS` |
| P2 fails | `NOT_ON_SHEETS` |

What each does to the campaign:

- `ON_SHEETS`: the next step reads a subsample of this band's windings as a detection test (finding 111's
  terms), after the stacked-winding check.
- `PARTLY_ON_SHEETS`: the same, restricted to windings with excess of at least 0.07, and the report says which
  part of the scroll they are in.
- `NOT_ON_SHEETS`: no ink read of this fit. The report says what differs from PHerc. 343 (loss terms, winding
  count, where the excess is worst), and the next step is one named change to the fit, registered separately.
- `DOES_NOT_RUN`: the failure is diagnosed to its cause before anything is changed.

## What the result cannot do

- **It does not show the windings are the right sheets.** The distance field comes from the surface prediction
  the fit was given, and the fit's own loss has a term on it late in the schedule. A winding can sit on a
  predicted sheet and still switch sheets along its length, or two windings can sit on one sheet. On PHerc. 343
  the score went with windings that were confirmed against published ones; that is one scroll.
- It says nothing about ink.
- A pass is about this band, this seed and these defaults.

## Limits

One scroll, one band, one fit, one seed, villa's default winding count. The thresholds are half and about a
fifth of one reference value from one other scroll.

## Cost

On PHerc. 343 the distance field took 21 minutes, a 300-step fit 14 minutes with pool
building, and the full fit 3 h 09 min at 10.8 GB of host memory and 12.7 GB of GPU memory. PHerc. 0211's band
has a larger cross-section, so I expect more of each and will record them. No training of any model. No upload.
