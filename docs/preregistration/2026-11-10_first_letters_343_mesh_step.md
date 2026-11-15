# Pre-registration: do windings fitted on this machine trace the published PHerc. 343 sheets and carry the same ink?

**Written 2026-11-12, before any winding fitted here has been compared with the published windings or with
their ink.** The file keeps the date the study was designed (2026-11-10), which the scripts already cite.
Finding 110.

PHerc. 343 is already awarded. Nothing here concerns a scroll that is still eligible for a prize.

## The question

The [kill test](../../reports/first_letters_343_reproduction.md) rebuilt the published PHerc. 343 image
**from the published windings**. It did not run the half of the recipe that makes windings: the distance
field, the spiral fit, the snap onto the surface prediction and the flattening. That half is the larger
unknown on a machine with 4 cores, 31 GB of RAM and one 24 GB card, and the fit is stochastic, so the
published windings cannot be reproduced bit for bit.

If the answer is yes, the campaign in [the strategy](../RESEARCH_STRATEGY.md) can run a band of an unread
scroll here and a null on it means something. If the chain does not run here, or its windings do not lie on
the published sheets or do not show the published ink, the strategy's rank-1 stop rule applies and the
campaign stops until that is understood.

## Reachability, checked before this was written

- **All inputs are public and on disk**: the tracks, the m7 surface prediction (level 1 for the distance
  field), the lasagna normals and the CT, for the band only. The recipe's scroll axis is read from its clone.
- **Step 1 has run**: villa's `make_surf_sdt.py` built the band's distance field in 53 s (3,019 bricks,
  5.9 GiB). It is an input, not a result; nothing was compared with it except the instrument check below.
- **The fit starts.** A 300-step smoke fit (arm `smoke`) loads every input and trains. Its windings are
  never compared with the published ones; the selection, P1 and comparison scripts refuse that arm. Two
  earlier attempts failed before training: an import error, and a kill by systemd-oomd for memory pressure
  while the distance field was loading. Two things differed in the killed attempt. villa `0fb38c45`
  rejected the published packed track store and crossing cache, because it identifies the track file by
  its modification time in nanoseconds and an HTTP download keeps whole seconds, so the fit unpickled the
  9 GiB track file in Python; `setup/fetch_tracks.sh` now restores the recorded time, and villa main already
  validates by content digest (villa #2041). And it was the first fit on the band, which packs the distance
  field into a 5.9 GiB file before loading it. Three 20-step diagnostic fits on 2026-11-12, with the track
  store accepted and a watchdog below systemd-oomd's limit, separated the second: packing that file while
  another process held 11 GiB drove memory pressure to 34% and rising within 25 seconds (stopped by the
  watchdog); the same load with the file already packed peaked at 1.7%; packing it on an idle host peaked
  at 1.6% (the user session's 10-second "full" pressure, the figure systemd-oomd acts on at 50%). The packed file is on disk now and the repacked copy was byte-identical. The unpickling path
  with the file already packed was not tested. The diagnostic fits' windings were deleted unread.
- **The instruments read what they should.**
  - Distance of a surface to itself: published w047 to w047, median 0.00 voxels, 98.8% of nodes within 2.
  - Ink transfer of the published segment onto itself: r = 1.0 over all 123,154 letter-box cells, every model.
  - The renderer's `--flip-normals` gives exactly the plain render reversed in depth (0 differing voxels in a
    1024² crop), so a winding whose normals point the other way can be rendered to match.
  - The distance field at the published nodes: median 2 working voxels from the sheet, 61% and 63% of nodes
    within 2; the same nodes displaced 6 voxels along the normal, 41% and 42%.

## The floor: what the wrong answer scores, measured here

- **Wrong sheet (P1).** Published w047 to published w048, along the normal: median 12.82 voxels, 13.1% of
  nodes within 2 voxels. The reverse: median 13.03, 13.0%. A fitted winding that lies on the neighbouring
  sheet scores about this.
- **Ink out of place (P3).** On the published maps transferred onto themselves, sliding one copy 64 render
  pixels gives r up to 0.193, and the published blind side against the reading side gives r = 0.180. These
  two controls are measured again on our maps in the run; the thresholds below are written against the run's
  own values.

One fit, one seed: there is no interval on any of these and none is claimed.

## Arms

| arm | work dir under `R/work` | what it is | compared with the published windings |
|---|---|---|---|
| `recipe` | `fit_recipe`, `gate_recipe` | the recipe's fit: 30,000 steps, its overrides, villa's default seed | yes |
| `reduced` | `fit_reduced`, `gate_reduced` | the same with fewer steps, only under the rule below | yes, verdict suffixed |
| `smoke` | `fit_smoke`, `gate_smoke` | 300 steps, to learn time, memory and layout | never |

`R` is `spiral_out/first_letters/pherc343_mesh` under the workspace root. One villa commit (`0fb38c45`, with
the recipe's one-line `fit_spiral_shell_optional.patch`), one renderer image (`vc-render:sampler-75c79ac5f`),
the four checkpoints of the kill test. Attempts that died before training are kept beside the arm with an
`_attemptN_` name and are not arms.

**Reduced-fit rule.** The `recipe` arm is the registered one. If its projected wall time from the smoke
fit's steady step rate exceeds 24 hours, or it is killed twice for memory, the `reduced` arm runs instead
with the largest multiple of 5,000 steps that projects under 24 hours. Below 5,000 steps the verdict is
`DOES_NOT_RUN`. Only one of the two arms is ever compared.

## Procedure

1. `run_fit.sh ARM`.
2. `run_select.sh ARM`: for each published winding, the raw fitted winding with the smallest median distance
   among those covering at least half of its nodes. Geometry only; no ink is looked at.
3. `run_snap.sh ARM` (the recipe's `snap_meshes.py`, after fetching every level-0 surface chunk it can
   sample) and `run_flatten.sh ARM W` (villa's lasagna flattening) for each chosen winding.
4. `run_p1.sh ARM`: P1 and P2 on the final windings.
5. `run_render.sh ARM W` (66 layers, flipped only if step 4's normals say so) and `run_ink.sh ARM W` (four
   models, depth +1, both sides).
6. `run_compare.sh ARM`: carries our ink into the published segment's frame and applies the table below.

The measurements and the table are `mesh_step_analysis.py` and `transfer_maps.py`, committed with this
document and tested in `tests/test_first_letters_343_mesh_step.py`.

## Predictions, fixed now

- **P1, same sheets.** For each of published w047 and w048, the chosen final winding has at least 50% of the
  published nodes within 2 voxels along the normal, and a median distance of at most 3 voxels. Reasoning:
  both come from the same tracks, the same surface prediction and the same snap, so they should land on the
  same sheet; the wrong sheet scores 13% and 12.8.
- **P2, neighbours.** The two chosen windings are consecutive, in the published order. Reported, not part of
  the verdict: the fit numbers windings from its own start, so the indices may differ from 047 and 048.
- **P3, same ink.** Over the published letter boxes, our ensemble (mean of the four models' z-scores at
  depth +1 on the reading side, broad background removed) correlates with the published one at r ≥ 0.50, and
  at least twice each of the two controls measured on our maps: slid by 64 pixels, and the published blind
  side. It is evaluable only if at least half of the letter-box cells received ink from our windings within
  4 voxels. Reasoning: the kill test showed depth +1 alone carries the strokes; a surface a few voxels off
  moves the sampled depth, so r well below 1 is expected. No magnitude beyond the threshold is predicted.
- **No prediction** for wall time or memory beyond the reduced-fit rule. They are recorded for every step.

## Decision rule

| outcome | verdict |
|---|---|
| any step of the chain exits non-zero or never ran | `DOES_NOT_RUN`, with the failed steps; P1 to P3 are not read |
| P1 holds for both windings and P3 holds | `REPRODUCED` |
| P1 holds for both, P3 does not hold or is not evaluable | `SAME_SHEETS_NO_LETTERS` |
| P1 fails for either, P3 holds | `LETTERS_OFF_THE_PUBLISHED_WINDINGS` |
| neither | `NOT_REPRODUCED` |

With the `reduced` arm every verdict carries `_WITH_REDUCED_FIT`. If no fitted winding covers half of
either published winding, P1 fails and there is no ink to carry: `NOT_REPRODUCED`.

`SAME_SHEETS_NO_LETTERS` is the row where the instrument may be at fault rather than the windings: check the
depth and side conventions before reading it as a property of the surface.

## What the result cannot do

- `REPRODUCED` says the chain runs here and lands on a known positive. It says nothing about whether an
  unread scroll has readable ink, and nothing about a scroll without a good surface prediction.
- One fit with one seed cannot say how often the fit lands on the same sheets.
- The ink comparison is against the kill test's maps at depth +1, not against the published 31-depth image.
- Any failure is a statement about this host and this pinned villa commit, not about the recipe.

## Limits

One scroll, one band (z 9500 to 11000), one pair of windings, one seed, one machine. The published windings
were chosen by their author after seeing ink; ours are chosen by distance to his.

## Cost

Serial; the GPU steps need the training loop stopped. The smoke fit (300 steps, 2026-11-12) took 13 min
36 s: about 6 minutes of preparation before the first step, then about 2.1 steps a second, with 11.5 GB on
the card, 10.3 GB of host memory at peak and memory pressure at most 9%. That projects the 30,000-step fit
at about 4 hours, so the `recipe` arm runs. The kill test measured the render at
about 8 minutes and depth-+1 ink at about 17 minutes for the joined segment. No training. No upload.
