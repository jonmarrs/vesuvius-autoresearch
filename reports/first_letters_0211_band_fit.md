On PHerc. 0211, a crushed scroll nobody has read, the recipe's spiral fit puts its windings on predicted sheets: median excess 0.086 against 0.000 for an unconverged fit, positive on 88% of windings (2026-11-13)

Finding 112. This is the First Letters campaign's first step on a prize-eligible scroll. The question was whether
the PHerc. 343 recipe's spiral fit, run unchanged on one band of PHerc. 0211 (z 10250 to 11750), writes windings
that follow sheets at all, because an ink read of windings that do not is wasted. Host: 4 cores, 31 GB of RAM, one
RTX 4090. Registered before any fit of PHerc. 0211 ran here:
`docs/preregistration/2026-11-13_first_letters_0211_band_fit.md` (commit `4a2a6f8e`). Record:
`reports/first_letters_0211_band_fit.json`. Scripts as run: `repro/first_letters/eligible_band/`.

PHerc. 0211 is prize-eligible. This report and its record carry summary numbers about the fit. The windings, the
distance field and the score of each winding are on this machine only, and nothing here is a render or an ink map.

**Verdict `ON_SHEETS`**, by the registered table: every step exited 0, 120 windings were scored in each fit, the
floor is 0.000, and P1 holds. I registered `PARTLY_ON_SHEETS` as the expected outcome, with low confidence. That
prediction was wrong: the fit did better than I expected.

## The score

For each raw winding, `excess` is the share of its nodes inside a predicted sheet minus the same share for the
nodes moved 6 voxels along the winding's normal. A winding that follows a sheet scores above zero; one that
ignores the sheets scores about zero.

| fit | windings scored | median excess | 10th to 90th percentile | windings with positive excess | median share of nodes inside a sheet |
|---|---|---|---|---|---|
| PHerc. 0211, 300 steps (the floor) | 120 | 0.000 | −0.007 to 0.008 | 50.8% | 0.242 |
| PHerc. 0211, 30,000 steps | 120 | **0.086** | −0.001 to 0.226 | **88.3%** | 0.309 |
| PHerc. 343, 30,000 steps (reference, finding 110) | 120 | 0.140 | 0.025 to 0.240 | 96.7% | 0.356 |

P1 asked for a median of at least 0.07 and at least 80% of windings positive; P2 for 0.03 and 65%. The median is
62% of PHerc. 343's.

**Where in the spiral.** The 120 scored windings in index order, in thirds:

| windings | median excess | positive | at 0.07 or above | median share inside a sheet | median nodes scored |
|---|---|---|---|---|---|
| w010 to w049 (inner) | 0.110 | 80.0% | 24 of 40 | 0.326 | 9,185 |
| w050 to w089 | 0.091 | 97.5% | 26 of 40 | 0.337 | 21,867 |
| w090 to w129 (outer) | 0.061 | 87.5% | 19 of 40 | 0.189 | 30,769 |

69 of the 120 windings score 0.07 or above and 14 score zero or below. The outer third is the weakest: fewer of
its nodes are inside any predicted sheet, and its median is under the P1 line. The four outermost of the
negative windings are next to each other.

## Is the score reading sheets? A profile along the normal

Not registered, and it cannot change the verdict. The registered score compares the nodes with two displaced
copies. This repeats the reading at 25 displacements from −24 to +24 voxels, on every fourth node of every raw
winding, pooled over windings.

| displacement (voxels) | −24 | −14 | −6 | −2 | 0 | +2 | +6 | +14 | +24 |
|---|---|---|---|---|---|---|---|---|---|
| 30,000 steps: share inside a sheet | 0.189 | 0.206 | 0.169 | 0.220 | **0.267** | 0.228 | 0.174 | 0.215 | 0.207 |
| 300 steps | 0.205 | 0.206 | 0.208 | 0.210 | 0.211 | 0.211 | 0.211 | 0.213 | 0.216 |

The converged fit's profile has one peak at zero displacement, a trough 4 to 6 voxels to either side and a
second, lower rise at 12 to 16 voxels, which is where the neighbouring sheets would be. The unconverged fit's
profile is flat to within 0.011. So the excess is a peak centred on the windings and not a slope across them. It
is still a reading of the same surface prediction the fit was given, and the first limit below stands.

## What the fit did

| | PHerc. 0211 band | PHerc. 343 band (finding 110) |
|---|---|---|
| tracks in the band | 1,454,417 | 2,277,921 |
| loss at step 0, 200, 1,000 | 6,593, 1,541, 381 | 4,142, 964, 326 |
| total loss at step 29,800 | 241.6 | 234.6 |
| track term | 134.5 | 148.6 |
| distance-field term (on from between steps 10,000 and 15,000) | 49.7 | 48.4 |
| distortion term (`sym_dirichlet`) | 35.5 | 18.5 |

The track and distance-field terms ended where they did on PHerc. 343. The distortion term ended at about twice
PHerc. 343's: the fitted spiral is bent further from its starting shape, as a crushed scroll requires.

villa warned once, as it did on PHerc. 343: `shell_outer_winding_idx 130 requires
model_gap_expander_num_windings >= 133, got model_gap_expander_num_windings 130`. The shell losses are set to
zero by the recipe's overrides, and the run was left as registered.

## What it cost

| step | wall time | host memory (peak resident) | GPU peak |
|---|---|---|---|
| distance field (CPU) | 13 min 11 s | 0.8 GB | none |
| fit, 300 steps, with pool building | 3 min 57 s | 7.9 GB | 9.4 GB |
| fit, 30,000 steps | 3 h 18 min 41 s | 7.7 GB | 10.3 GB |

On PHerc. 343 the same steps took 21 minutes, 14 minutes and 3 h 09 min, at 10.8 GB of host memory and 12.7 GB
of GPU memory. I expected more of each on PHerc. 0211 because its cross-section is larger; the fit took 5% longer
and less memory, and the band holds fewer tracks (1.45 million against 2.28 million). Memory pressure during the full fit peaked at 1.7% over ten seconds, far from the 50% at which
the host's out-of-memory daemon kills a job. The training loop was stopped throughout.

## What this does to the campaign

By the registered consequence: **the next step reads a subsample of this band's windings as a detection test, in
finding 111's terms, after a check for stacked windings.** That step is registered separately as finding 113
before anything is rendered. What finding 111 fixed for it: both sides are swept over depth, a blank result is
weak evidence of no ink, and strokes are not letters until something sharper than the four released models says
so. Its renders and ink maps stay on this machine.

The direction of the spiral came from the open-data catalog (`metadata.json`): villa derives it from two
orientation flags, which give anticlockwise for PHerc. 0211. PHerc. 0125, which the strategy named first, has no
z direction there, so its direction is unknown and it was set aside. A 1,000-step fit cannot find the direction
by trial: on PHerc. 343 the track term at step 800 was 440.6 declared clockwise and 438.8 declared anticlockwise.

## What this does not show

1. **That the windings are the right sheets.** The distance field comes from the surface prediction the fit was
   given, and the fit's own loss has a term on it. A winding can sit on predicted sheets and still switch sheets
   along its length, and two windings can sit on one sheet. On PHerc. 343 the score went with windings confirmed
   against published ones; that is one scroll, and a round one.
2. That the surface prediction is right on this scroll. Nobody has published a checked segment of PHerc. 0211.
3. Anything about ink.
4. That villa's default of 130 windings at 16 voxels suits this scroll. The outer third's weaker score may be
   that default, or the scroll; this run cannot tell which.
5. Anything beyond this band, this seed and these defaults. Each fit ran once.
6. That this is the first fit of PHerc. 0211. The winners page lists a spiral fit of it by another contributor;
   I have not compared this fit with that one.
7. A calibrated meaning for 0.07. The line was half of one reference value from one other scroll.
